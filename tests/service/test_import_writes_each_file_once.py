"""``Service.import_events()`` holds each item file's text in memory across the whole import and
writes it once, before the index commit, however many events touch it. The result is
byte-identical to applying the same events one at a time through the interactive verbs, and an
import that fails leaves every file as it was.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from _helpers import create_item
from squads import _actor as actor
from squads import _aio
from squads import _clock as clock
from squads._context import bind_context, get_context
from squads._errors import SquadsError
from squads._services import _service as service

pytestmark = pytest.mark.anyio

type Step = tuple[str, ...]

START = datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC)

#: Existing items every scenario can target: three tasks.
EXISTING = ("e1", "e2", "e3")

SCENARIOS: dict[str, list[Step]] = {
    "one event, existing": [("comment", "e1", "hello")],
    "one event, created": [("create", "a", "task", "Created")],
    "several comments, existing": [
        ("comment", "e1", "one"),
        ("comment", "e1", "two"),
        ("comment", "e1", "three"),
    ],
    "several comments, created": [
        ("create", "a", "task", "Created"),
        ("comment", "a", "one"),
        ("comment", "a", "two"),
        ("comment", "a", "three"),
    ],
    "every kind, created": [
        ("create", "a", "task", "Created"),
        ("comment", "a", "note"),
        ("body", "a", "the body"),
        ("status", "a", "Ready"),
        ("ref", "a", "e1"),
        ("retitle", "a", "Created and renamed"),
        ("add", "a", "subtask", "s1", "First step"),
        ("sub-status", "a", "subtask", "s1", "InProgress"),
        ("sub-comment", "a", "subtask", "s1", "on the step"),
    ],
    "every kind, existing": [
        ("comment", "e1", "note"),
        ("body", "e1", "the body"),
        ("status", "e1", "Ready"),
        ("ref", "e1", "e2"),
        ("retitle", "e1", "Existing and renamed"),
        ("add", "e1", "subtask", "s1", "First step"),
        ("sub-status", "e1", "subtask", "s1", "InProgress"),
        ("sub-comment", "e1", "subtask", "s1", "on the step"),
    ],
    "interleaved across three items": [
        ("comment", "e1", "a"),
        ("create", "a", "task", "Created"),
        ("comment", "e2", "b"),
        ("comment", "a", "c"),
        ("comment", "e1", "d"),
        ("status", "e2", "Ready"),
        ("ref", "a", "e2"),
        ("comment", "a", "e"),
    ],
    "a sub-entity added then edited": [
        ("add", "e1", "subtask", "s1", "Step"),
        ("add", "e1", "subtask", "s2", "Another step"),
        ("sub-status", "e1", "subtask", "s1", "InProgress"),
        ("sub-comment", "e1", "subtask", "s2", "remark"),
        ("sub-status", "e1", "subtask", "s2", "InProgress"),
    ],
    "a rename then more events": [
        ("retitle", "e1", "Moved file"),
        ("comment", "e1", "after the move"),
        ("status", "e1", "Ready"),
    ],
    "a created item renamed": [
        ("create", "a", "task", "Before"),
        ("retitle", "a", "After"),
        ("comment", "a", "named now"),
    ],
}

#: How many distinct files each scenario touches.
TOUCHED: dict[str, int] = {
    "one event, existing": 1,
    "one event, created": 1,
    "several comments, existing": 1,
    "several comments, created": 1,
    "every kind, created": 1,
    "every kind, existing": 1,
    "interleaved across three items": 3,
    "a sub-entity added then edited": 1,
    "a rename then more events": 1,
    "a created item renamed": 1,
}


async def _setup(svc: Any) -> dict[str, str]:
    return {name: (await create_item(svc, "task", f"Existing {name}")).item.id for name in EXISTING}


def _at(index: int) -> datetime:
    return START + timedelta(minutes=index)


def _as_event(step: Step, index: int, ids: dict[str, str], created: set[str]) -> dict[str, Any]:
    """The import event for *step*; created items are addressed by handle, existing by id."""

    def target(name: str) -> str:
        return name if name in created else ids[name]

    op = step[0]
    event: dict[str, Any] = {"as": "manager", "at": _at(index).isoformat()}
    if op == "create":
        event |= {"op": "create", "type": step[2], "title": step[3], "handle": step[1]}
    elif op == "comment":
        event |= {"op": "comment", "target": target(step[1]), "message": step[2]}
    elif op == "body":
        event |= {"op": "body", "target": target(step[1]), "body": step[2]}
    elif op == "status":
        event |= {"op": "status", "target": target(step[1]), "status": step[2]}
    elif op == "ref":
        event |= {"op": "ref", "target": target(step[1]), "to": target(step[2]), "kind": "blocks"}
    elif op == "retitle":
        event |= {"op": "update", "target": target(step[1]), "title": step[2]}
    elif op == "add":
        event |= {
            "op": "add-subtask",
            "target": target(step[1]),
            "title": step[4],
            "handle": step[3],
        }
    elif op == "sub-status":
        event |= {
            "op": "sub-status",
            "target": target(step[1]),
            "kind": step[2],
            "local": step[3],
            "status": step[4],
        }
    else:
        event |= {
            "op": "comment",
            "target": target(step[1]),
            "message": step[4],
            "sub": [step[2], step[3]],
        }
    return event


async def _as_verb(svc: Any, step: Step, ids: dict[str, str], locals_: dict[str, str]) -> None:
    """Apply *step* through the interactive service method it corresponds to."""
    op = step[0]
    if op == "create":
        ids[step[1]] = (await svc.create(step[2], step[3], author="manager")).item.id
    elif op == "comment":
        await svc.comment(ids[step[1]], [step[2]], as_slug="manager")
    elif op == "body":
        await svc.set_body(ids[step[1]], step[2])
    elif op == "status":
        await svc.set_status(ids[step[1]], step[2])
    elif op == "ref":
        await svc.add_ref(ids[step[1]], ids[step[2]], kind="blocks")
    elif op == "retitle":
        await svc.update(ids[step[1]], title=step[2])
    elif op == "add":
        locals_[step[3]] = (await svc.add_block(ids[step[1]], step[2], step[4])).local_id
    elif op == "sub-status":
        await svc.set_block_status(ids[step[1]], step[2], locals_[step[3]], step[4])
    else:
        await svc.comment(
            ids[step[1]], [step[4]], as_slug="manager", sub=(step[2], locals_[step[3]])
        )


def _tree(svc: Any) -> dict[str, str]:
    """Every squad file's text (item files, the index, the reflog), keyed by relative path."""
    squad_dir = svc.paths.squad_dir
    return {
        str(p.relative_to(squad_dir)): p.read_text(encoding="utf-8")
        for p in sorted(squad_dir.rglob("*"))
        if p.is_file() and p.suffix in {".md", ".json", ".jsonl"}
    }


async def _reference_squad(tmp_path: Path) -> Any:
    root = tmp_path / "reference"
    root.mkdir()
    result = await service.init(root=root, roles_spec="minimal", _skip_skill_seed=True)
    return service.Service(result.paths)


async def _import(svc: Any, steps: list[Step], ids: dict[str, str]) -> Any:
    created = {s[1] for s in steps if s[0] == "create"}
    lines = [json.dumps(_as_event(s, i, ids, created)) for i, s in enumerate(steps)]
    return await svc.import_events("\n".join(lines))


@pytest.mark.parametrize("name", list(SCENARIOS))
async def test_an_import_writes_each_touched_file_once(svc, write_ledger, name):
    ids = await _setup(svc)

    result = await _import(svc, SCENARIOS[name], ids)

    assert result.plan.ok, result.plan.issues
    unit = next(u for u in reversed(write_ledger.finished) if u.method == "_apply_import")
    assert set(unit.counts.values()) == {1}
    assert len(unit.counts) == TOUCHED[name]


@pytest.mark.parametrize("name", list(SCENARIOS))
async def test_an_import_equals_the_same_events_applied_one_at_a_time(
    svc, tmp_path, write_ledger, name
):
    steps = SCENARIOS[name]
    imported_ids = await _setup(svc)
    result = await _import(svc, steps, imported_ids)
    assert result.plan.ok, result.plan.issues

    reference = await _reference_squad(tmp_path)
    ids = await _setup(reference)
    locals_: dict[str, str] = {}
    for index, step in enumerate(steps):
        prior = get_context()
        try:
            clock.set_now(_at(index))
            actor.set_actor("manager")
            await _as_verb(reference, step, ids, locals_)
        finally:
            bind_context(prior)

    assert _tree(svc) == _tree(reference)


async def test_an_import_cli_smoke(svc, invoke, tmp_path):
    ids = await _setup(svc)
    events = tmp_path / "events.jsonl"
    events.write_text(
        "\n".join(
            json.dumps(e)
            for e in [
                {"op": "comment", "target": ids["e1"], "message": "one", "as": "manager"},
                {"op": "comment", "target": ids["e1"], "message": "two", "as": "manager"},
            ]
        ),
        encoding="utf-8",
    )

    result = await invoke(["import", str(events)])

    assert result.exit_code == 0


# ----------------------------------------------------------------- faults
async def _fault_scenario(svc: Any) -> tuple[str, dict[str, str]]:
    ids = await _setup(svc)
    steps = SCENARIOS["interleaved across three items"]
    created = {s[1] for s in steps if s[0] == "create"}
    text = "\n".join(json.dumps(_as_event(s, i, ids, created)) for i, s in enumerate(steps))
    return text, ids


@pytest.mark.parametrize("where", ["before-flush", "between-files", "at-commit"])
async def test_a_fault_leaves_each_file_as_it_was_or_final_and_the_squad_repairable(
    svc, tmp_path, monkeypatch, write_ledger, where
):
    text, _ids = await _fault_scenario(svc)
    before = _tree(svc)

    reference = await _reference_squad(tmp_path)
    await _setup(reference)
    await reference.import_events(text)
    final = _tree(reference)

    real_replace = _aio.atomic_replace_sync
    item_writes: list[str] = []

    def replace_(path: Path, content: str) -> None:
        if where == "between-files" and path.suffix == ".md":
            item_writes.append(path.name)
            if len(item_writes) == 2:
                raise OSError("injected between two files")
        if where == "at-commit" and path.name == ".squads.json":
            raise OSError("injected at the commit")
        real_replace(path, content)

    with monkeypatch.context() as faulty:
        if where == "before-flush":

            async def boom(*args: Any, **kwargs: Any) -> Any:
                raise OSError("injected before the flush")

            faulty.setattr(type(svc), "_set_status_core", boom)
        else:
            faulty.setattr(_aio, "atomic_replace_sync", replace_)
        with pytest.raises(OSError, match="injected"):
            await svc.import_events(text)

    for rel, text_after in _tree(svc).items():
        if rel.endswith(".md"):
            assert text_after in {before.get(rel), final.get(rel)}, rel
    if where == "before-flush":
        assert {k: v for k, v in _tree(svc).items() if k.endswith(".md")} == {
            k: v for k, v in before.items() if k.endswith(".md")
        }

    await svc.repair()
    assert [i for i in await svc.check() if i.level == "error"] == []


async def test_a_hold_cannot_be_opened_inside_a_hold_or_outside_a_transaction(svc):
    with pytest.raises(SquadsError, match="only inside an open transaction"):
        async with svc._deferred_item_writes():
            pass

    async with svc.store.transaction(), svc._deferred_item_writes():
        with pytest.raises(SquadsError, match="already open"):
            async with svc._deferred_item_writes():
                pass
        assert svc.store.held_item_files() is not None

    assert svc.store.held_item_files() is None
