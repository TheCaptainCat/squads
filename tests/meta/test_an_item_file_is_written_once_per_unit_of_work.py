"""The write-once rule and the instrument that enforces it.

Within a committed unit of work an item file is written at most once, and before the index
commit. ``tests/_write_guard.py`` observes the write funnel for every test; this module pins
what the observation covers (synthetic units, one known positive per write seam).
"""

from collections.abc import Awaitable, Callable
from typing import Any

import pytest

import _write_guard
from _helpers import create_item
from squads import _aio
from squads._index._resolver import item_file

pytestmark = pytest.mark.anyio

type Op = tuple[str, ...]


async def _run(svc: Any, ops: list[Op], *, fail: bool) -> None:
    """Apply *ops* inside one transaction: ``(funnel, name)`` writes or ``("rename", a, b)``."""
    folder = svc.paths.squad_dir / "tasks"
    folder.mkdir(exist_ok=True)
    async with svc.store.transaction():
        for op in ops:
            if op[0] == "atomic":
                await _aio.atomic_write_text(folder / op[1], "x")
            elif op[0] == "plain":
                await _aio.write_text(folder / op[1], "x")
            elif op[0] == "rename":
                await _aio.path_rename(folder / op[1], folder / op[2])
            elif op[0] == "exempt":
                hidden = svc.paths.squad_dir / ".overrides"
                hidden.mkdir(exist_ok=True)
                await _aio.atomic_write_text(hidden / op[1], "x")
        if fail:
            raise RuntimeError("injected")


UNITS: list[tuple[str, list[Op], str | None]] = [
    ("one write", [("atomic", "a.md")], None),
    ("one write, plain funnel", [("plain", "a.md")], None),
    ("two writes to one path", [("atomic", "a.md"), ("atomic", "a.md")], "a.md written 2 times"),
    (
        "two plain writes to one path",
        [("plain", "a.md"), ("plain", "a.md")],
        "a.md written 2 times",
    ),
    (
        "two writes to one path, mixed funnels",
        [("atomic", "a.md"), ("plain", "a.md")],
        "a.md written 2 times",
    ),
    ("two writes to two paths", [("atomic", "a.md"), ("atomic", "b.md")], None),
    (
        "a write before a rename and one after",
        [("atomic", "a.md"), ("rename", "a.md", "c.md"), ("atomic", "c.md")],
        "c.md written 2 times",
    ),
    ("a rename alone", [("atomic", "a.md"), ("rename", "a.md", "c.md")], None),
    ("an exempt path twice", [("exempt", "x.md"), ("exempt", "x.md")], None),
]


@pytest.mark.parametrize(("name", "ops", "expected"), UNITS, ids=[u[0] for u in UNITS])
async def test_a_committed_unit_is_checked_for_a_second_write(
    svc, write_ledger, name, ops, expected
):
    await _run(svc, ops, fail=False)

    violations = write_ledger.take_violations()
    if expected is None:
        assert violations == []
    else:
        assert len(violations) == 1
        assert expected in violations[0]
        assert violations[0].startswith("_run:")


@pytest.mark.parametrize(("name", "ops", "expected"), UNITS, ids=[u[0] for u in UNITS])
async def test_a_unit_that_raises_is_not_checked(svc, write_ledger, name, ops, expected):
    with pytest.raises(RuntimeError, match="injected"):
        await _run(svc, ops, fail=True)

    assert write_ledger.take_violations() == []


async def test_two_consecutive_units_may_each_write_the_same_path(svc, write_ledger):
    await _run(svc, [("atomic", "a.md")], fail=False)
    await _run(svc, [("atomic", "a.md")], fail=False)

    assert write_ledger.take_violations() == []


async def test_an_item_file_written_after_the_index_commit_is_reported(svc, write_ledger):
    folder = svc.paths.squad_dir / "tasks"
    folder.mkdir(exist_ok=True)
    unit = _write_guard.Unit("late")
    unit.index_written = True
    write_ledger.stacks.setdefault(_write_guard.squad_key(svc.paths.squad_dir), []).append(unit)
    try:
        await _aio.atomic_write_text(folder / "a.md", "x")
    finally:
        write_ledger.stacks[_write_guard.squad_key(svc.paths.squad_dir)].remove(unit)
    unit.committed = True
    write_ledger.finish(unit)

    assert write_ledger.take_violations() == ["late: a.md written after the index commit"]


async def test_the_index_and_regenerable_output_are_not_item_files(svc, write_ledger, tmp_path):
    async with svc.store.transaction():
        await _aio.atomic_write_text(tmp_path / "CLAUDE.md", "x")
        await _aio.atomic_write_text(tmp_path / "CLAUDE.md", "x")

    assert write_ledger.take_violations() == []
    assert not _write_guard.is_item_file(svc.paths.index_path)
    assert not _write_guard.is_item_file(tmp_path / "CLAUDE.md")
    assert not _write_guard.is_item_file(svc.paths.squad_dir / ".overrides" / "x.md")
    assert _write_guard.is_item_file(svc.paths.squad_dir / "tasks" / "x.md")


async def test_the_repair_rebuild_is_watched_while_it_runs(svc, write_ledger, monkeypatch):
    real_overwrite = svc.store.overwrite

    async def overwrite_then_write(db):
        await real_overwrite(db)
        await _aio.atomic_write_text(svc.paths.squad_dir / "tasks" / "late.md", "x")

    monkeypatch.setattr(svc.store, "overwrite", overwrite_then_write)
    await svc.repair()

    assert write_ledger.take_violations() == [
        "_rebuild_index_from_disk: late.md written after the index commit"
    ]


# ----------------------------------------------------------------- known positives
async def _create(svc: Any) -> Any:
    return (await create_item(svc, "task", "seam")).item


async def _body(svc: Any) -> Any:
    item = await _create(svc)
    await svc.set_body(item.id, "text")
    return item


async def _status(svc: Any) -> Any:
    item = await _create(svc)
    await svc.set_status(item.id, "Ready")
    return item


async def _comment(svc: Any) -> Any:
    item = await _create(svc)
    await svc.comment(item.id, ["hi"], as_slug="manager")
    return item


async def _update(svc: Any) -> Any:
    item = await _create(svc)
    await svc.update(item.id, description="d")
    return item


async def _ref(svc: Any) -> Any:
    item = await _create(svc)
    other = await _create(svc)
    await svc.add_ref(item.id, other.id, kind="blocks")
    return item


async def _subentity(svc: Any) -> Any:
    item = await _create(svc)
    await svc.add_block(item.id, "subtask", "step")
    return item


SEAMS: dict[str, Callable[[Any], Awaitable[Any]]] = {
    "a create": _create,
    "a section edit": _body,
    "a status change (frontmatter write)": _status,
    "a comment": _comment,
    "a metadata update": _update,
    "a ref add": _ref,
    "a sub-entity add": _subentity,
}


@pytest.mark.parametrize("seam", list(SEAMS))
async def test_every_item_file_write_seam_is_observed(svc, write_ledger, seam):
    item = await SEAMS[seam](svc)

    path = item_file(svc.paths, item).resolve()
    assert write_ledger.seen[path] >= 1
