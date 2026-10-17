"""``Service.retype()`` composes the retyped file in memory and writes it once, before the index
commit, whatever the item's shape. A fault at the rename, at the write or at the index commit
leaves the file recoverable and the squad repairable.
"""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from _helpers import create_item
from squads import _aio
from squads._context import bind_context, get_context
from squads._index._resolver import item_file
from squads._itemfile import read_frontmatter
from squads._sections import get_section, remove_section
from squads._services import _service as service

pytestmark = pytest.mark.anyio

#: (source type, target type, status is reset). Containers: task and feature host sub-entities;
#: bug, decision and epic do not.
PAIRS = [
    pytest.param("task", "bug", True, id="container-to-none-reset"),
    pytest.param("bug", "task", True, id="none-to-container-reset"),
    pytest.param("task", "feature", False, id="both-with-container-carried"),
    pytest.param("task", "epic", False, id="container-to-none-carried"),
    pytest.param("bug", "decision", True, id="both-without-container-reset"),
]


async def _build(
    svc: Any, source: str, *, own_id_in_body: bool, edges: bool, discussion: bool
) -> Any:
    """The item to retype, with the incoming edges and body the row calls for."""
    item = (await create_item(svc, source, "Subject")).item
    if own_id_in_body:
        await svc.set_body(item.id, f"{item.id} is this item")
    if edges:
        other = (await create_item(svc, "review", "Referrer")).item
        await svc.add_ref(other.id, item.id, kind="blocks")
        await svc.set_body(other.id, f"mentions {item.id}")
    if not discussion:
        path = item_file(svc.paths, item)
        path.write_text(remove_section(path.read_text(encoding="utf-8"), "discussion"))
    return item


def _last_unit(ledger: Any, method: str) -> Any:
    return next(u for u in reversed(ledger.finished) if u.method == method)


@pytest.mark.parametrize(("source", "target", "reset"), PAIRS)
@pytest.mark.parametrize("own_id_in_body", [False, True], ids=["no-own-id", "own-id"])
@pytest.mark.parametrize("discussion", [True, False], ids=["discussion", "no-discussion"])
@pytest.mark.parametrize("edges", [False, True], ids=["no-edges", "edges"])
async def test_a_retype_writes_each_file_it_changes_once(
    svc, write_ledger, source, target, reset, own_id_in_body, discussion, edges
):
    item = await _build(
        svc, source, own_id_in_body=own_id_in_body, edges=edges, discussion=discussion
    )
    old_id = item.id

    res = await svc.retype(item.id, target)

    unit = _last_unit(write_ledger, "retype")
    new_path = svc.paths.abspath(res.item.path).resolve()
    assert unit.counts[new_path] == 1
    assert set(unit.counts.values()) == {1}
    assert len(unit.counts) == 1 + (1 if edges else 0)
    assert res.status_reset is reset
    fm = read_frontmatter(new_path)
    assert fm["type"] == target
    assert fm["id"] == res.item.id
    text = new_path.read_text(encoding="utf-8")
    assert (f"retyped {old_id} → {res.item.id}" in text) is discussion
    if own_id_in_body:
        assert f"{res.item.id} is this item" in (get_section(text, "body") or "")


async def test_a_retype_cli_smoke(svc, invoke):
    item = (await create_item(svc, "task", "Subject")).item

    result = await invoke(["task", str(item.sequence_id), "retype", "bug"])

    assert result.exit_code == 0
    assert "BUG-" in result.output


# ----------------------------------------------------------------- faults
def _fail_when(monkeypatch: pytest.MonkeyPatch, where: str, new_name: str) -> None:
    """Make the named step raise: the rename, the write of the retyped file, or the index commit."""
    if where == "rename":
        real_rename = _aio.path_rename

        async def rename(old: Path, new: Path) -> None:
            if new.name == new_name:
                raise OSError("injected at the rename")
            await real_rename(old, new)

        monkeypatch.setattr(_aio, "path_rename", rename)
        return
    real_replace = _aio.atomic_replace_sync

    def replace_(path: Path, text: str) -> None:
        if (where == "write" and path.name == new_name) or (
            where == "commit" and path.name == ".squads.json"
        ):
            raise OSError(f"injected at the {where}")
        real_replace(path, text)

    monkeypatch.setattr(_aio, "atomic_replace_sync", replace_)


async def _reference_result(tmp_path: Path, source: str, target: str) -> tuple[str, str]:
    """The retyped file's name and final bytes from an undisturbed run of the same scenario."""
    root = tmp_path / "reference"
    root.mkdir()
    prior = get_context()
    bind_context(replace(prior, clock_override=datetime(2026, 6, 7, 10, 0, 0, tzinfo=UTC)))
    result = await service.init(root=root, roles_spec="minimal", _skip_skill_seed=True)
    ref = service.Service(result.paths)
    item = (await create_item(ref, source, "Subject")).item
    res = await ref.retype(item.id, target)
    path = ref.paths.abspath(res.item.path)
    return path.name, path.read_text(encoding="utf-8")


@pytest.mark.parametrize("where", ["rename", "write", "commit"])
@pytest.mark.parametrize(("source", "target", "reset"), PAIRS[:2])
async def test_a_fault_leaves_the_file_recoverable_and_the_squad_repairable(
    svc, tmp_path, monkeypatch, write_ledger, source, target, reset, where
):
    item = (await create_item(svc, source, "Subject")).item
    old_path = item_file(svc.paths, item)
    old_bytes = old_path.read_text(encoding="utf-8")
    new_name, final_bytes = await _reference_result(tmp_path, source, target)
    with monkeypatch.context() as faulty:
        _fail_when(faulty, where, new_name)
        with pytest.raises(OSError, match="injected"):
            await svc.retype(item.id, target)

    candidates = list(old_path.parent.parent.rglob(f"*{item.sequence_id:06d}-*.md"))
    assert len(candidates) == 1
    landed = candidates[0]
    expected_name, expected_bytes = {
        "rename": (old_path.name, old_bytes),
        "write": (new_name, old_bytes),
        "commit": (new_name, final_bytes),
    }[where]
    assert landed.name == expected_name
    assert landed.read_text(encoding="utf-8") == expected_bytes

    await svc.repair()
    assert [i for i in await svc.check() if i.level == "error"] == []
