"""Bulk vocabulary rename (`sq migrate rename-type` / `rename-status`): a type/status renamed
project-wide, atomically, with sub-entities and status carried unconditionally (no retype-style
guardrails), refs/parents/prose resynced everywhere, and a full mid-flight rollback on failure.
Driven through the real CLI against a squad that declares its custom type through an actual
`.overrides/workflow.toml` file — the honest end-to-end wiring a real project goes through.
"""

from pathlib import Path

import pytest

from squads._errors import SquadsError
from squads._index._reflog import read_lines, reflog_path
from squads._models._schema import SCHEMA_VERSION
from squads._paths import SquadPaths
from squads._services import _service as service

pytestmark = pytest.mark.anyio

_TICKET_OVERRIDE = """
[items.ticket]
prefix = "TICKET"
folder = "tickets"
lifecycle = "work"
parents = ["feature"]
subentity_kind = "subtask"
parent_required = "feature"
"""


def _write_override(squad_dir: Path, content: str) -> Path:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    path = override_dir / "workflow.toml"
    path.write_text(content, encoding="utf-8")
    return path


async def _seed_scenario(project: SquadPaths):
    """A feature with two tasks (non-initial statuses, sub-entities, cross-refs, prose
    mentions) plus a review and a bug, seeded through the real .overrides-loaded service —
    exactly the shape a bulk rename needs to prove it carries everything unconditionally."""
    _write_override(project.squad_dir, _TICKET_OVERRIDE)
    svc = service.open_service()

    feat = (await svc.create("feature", "widget epic", author="manager")).item
    task1 = (await svc.create("task", "first ticket task", parent=feat.id, author="manager")).item
    task2 = (await svc.create("task", "second ticket task", parent=feat.id, author="manager")).item
    rev = (await svc.create("review", "code review of the widget", author="manager")).item
    bug = (
        await svc.create("bug", "regression found in task1", parent=task1.id, author="manager")
    ).item

    await svc.add_subtask(task1.id, "implement the widget")
    await svc.add_subtask(task2.id, "wire up the widget UI")

    await svc.set_status(task1.id, "InProgress")
    await svc.set_status(task2.id, "InProgress")
    await svc.set_status(task2.id, "Blocked")

    await svc.add_ref(task1.id, task2.id, kind="related")
    await svc.add_ref(rev.id, task1.id, kind="related")
    await svc.set_body(task1.id, f"Coordinates with {task2.id} and is reviewed in {rev.id}.")

    return svc, {"feat": feat, "task1": task1, "task2": task2, "rev": rev, "bug": bug}


# --------------------------------------------------------------------------- rename-type


async def test_rename_type_preserves_status_subentities_and_resyncs_every_edge(
    project: SquadPaths, invoke
) -> None:
    svc, items = await _seed_scenario(project)
    task1_old, task2_old, feat_id = items["task1"].id, items["task2"].id, items["feat"].id
    rev_id, bug_id = items["rev"].id, items["bug"].id

    result = await invoke(["migrate", "rename-type", "task", "ticket"])
    assert result.exit_code == 0, result.output

    db = await svc.store.load()
    ticket_ids = {it.id for it in db.items.values() if it.type == "ticket"}
    assert len(ticket_ids) == 2
    assert not any(it.type == "task" for it in db.items.values())
    assert not list((project.squad_dir / "tasks").glob("TASK-*"))

    new_task1 = next(it for it in db.items.values() if it.title == "first ticket task")
    new_task2 = next(it for it in db.items.values() if it.title == "second ticket task")

    # Status + sub-entities carried unconditionally (unlike retype's guardrails/reset).
    assert new_task1.status == "InProgress"
    assert new_task2.status == "Blocked"
    assert len(new_task1.subentities) == 1

    # Parent/child/refs/prose all resynced to the new id.
    assert new_task1.parent == feat_id and new_task2.parent == feat_id
    new_bug = await svc.get(bug_id)
    assert new_bug.parent == new_task1.id and new_bug.parent != task1_old
    assert any(new_task2.id in r for r in new_task1.refs)
    new_rev = await svc.get(rev_id)
    assert any(new_task1.id in r for r in new_rev.refs)
    task1_text = svc.paths.abspath(new_task1.path).read_text(encoding="utf-8")
    assert new_task2.id in task1_text and task2_old not in task1_text


async def test_rename_type_leaves_check_clean_and_repair_a_pure_no_op(
    project: SquadPaths, invoke
) -> None:
    svc, _items = await _seed_scenario(project)

    result = await invoke(["migrate", "rename-type", "task", "ticket"])
    assert result.exit_code == 0, result.output

    check_result = await invoke(["check"])
    assert check_result.exit_code == 0, check_result.output

    db_before = await svc.store.load()
    before = {seq: it.model_dump(mode="json") for seq, it in db_before.items.items()}
    repair_result = await svc.repair()
    after = {seq: it.model_dump(mode="json") for seq, it in repair_result.db.items.items()}
    assert before == after, "repair changed item data -- index is not a pure rebuild"


async def test_rename_type_refuses_an_undeclared_new_type_and_a_no_op_rename_to_itself(
    svc,
) -> None:
    await svc.create("task", "t")
    with pytest.raises(SquadsError, match="not declared"):
        await svc.rename_type("task", "ticket")
    with pytest.raises(SquadsError, match="itself"):
        await svc.rename_type("task", "task")


async def test_rename_type_refuses_when_a_child_would_have_an_invalid_parent_under_the_new_type(
    svc,
) -> None:
    from squads._workflow._loader import load_workflow_spec
    from squads._workflow._models import ItemSpec, WorkflowSpec

    base = load_workflow_spec()
    generic = ItemSpec(prefix="GEN", folder="generics", lifecycle="work")
    spec = WorkflowSpec.model_validate(
        {
            "items": {**base.items, "generic": generic},
            "statuses": base.statuses,
            "lifecycles": base.lifecycles,
            "prefix_to_type": {**base.prefix_to_type, "GEN": "generic"},
            "alias_to_type": base.alias_to_type,
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
        }
    )
    generic_svc = service.Service(svc.paths, spec=spec)

    feat = (await svc.create("feature", "f")).item
    task = (await svc.create("task", "t", parent=feat.id)).item  # requires a feature parent

    with pytest.raises(SquadsError, match="child item"):
        await generic_svc.rename_type("feature", "generic")

    still = await svc.get(task.id)
    assert still.parent == feat.id  # untouched


async def test_rename_type_mid_flight_failure_restores_disk_and_index(
    svc, monkeypatch, tmp_path
) -> None:
    from squads._services import _service as service
    from squads._services._rename import (
        _apply_type_change,  # pyright: ignore[reportPrivateUsage]
    )
    from squads._workflow._loader import load_workflow_spec
    from squads._workflow._models import ItemSpec, WorkflowSpec

    base = load_workflow_spec()
    ticket = ItemSpec(
        prefix="TICKET",
        folder="tickets",
        lifecycle="work",
        parents=["feature"],
        subentity_kind="subtask",
        parent_required="feature",
    )
    spec = WorkflowSpec.model_validate(
        {
            "items": {**base.items, "ticket": ticket},
            "statuses": base.statuses,
            "lifecycles": base.lifecycles,
            "prefix_to_type": {**base.prefix_to_type, "TICKET": "ticket"},
            "alias_to_type": base.alias_to_type,
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
        }
    )
    ticket_svc = service.Service(svc.paths, spec=spec)

    feat = (await svc.create("feature", "f")).item
    await svc.create("task", "t1", parent=feat.id)
    await svc.create("task", "t2", parent=feat.id)

    def _snapshot(root: Path) -> dict[str, str]:
        return {
            str(p.relative_to(root)): p.read_text(encoding="utf-8")
            for p in root.rglob("*")
            if p.is_file()
        }

    before = _snapshot(svc.paths.squad_dir)

    calls = {"n": 0}
    real = _apply_type_change

    async def _flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:  # let the first item's file move happen, then blow up
            raise RuntimeError("boom")
        return await real(*args, **kwargs)

    monkeypatch.setattr("squads._services._rename._apply_type_change", _flaky)

    with pytest.raises(RuntimeError, match="boom"):
        await ticket_svc.rename_type("task", "ticket")

    assert _snapshot(svc.paths.squad_dir) == before
    db = await svc.store.load()
    assert {it.type for it in db.items.values() if it.title in ("t1", "t2")} == {"task"}


# --------------------------------------------------------------------------- rename-status


async def test_rename_status_moves_only_matching_items_of_the_named_type(
    project: SquadPaths, invoke
) -> None:
    svc, items = await _seed_scenario(project)
    task1_id, task2_id, rev_id = items["task1"].id, items["task2"].id, items["rev"].id

    # task1=InProgress, task2=Blocked, rev has its own lifecycle with InProgress too
    # (proves the rename is scoped per-type, not by status name alone).
    result = await invoke(["migrate", "rename-status", "task", "InProgress", "InReview"])
    assert result.exit_code == 0, result.output

    assert (await svc.get(task1_id)).status == "InReview"
    assert (await svc.get(task2_id)).status == "Blocked"  # different old_status, untouched
    _ = rev_id


async def test_rename_status_invalid_target_fails_closed_with_no_partial_rewrite(
    project: SquadPaths, invoke
) -> None:
    svc, _items = await _seed_scenario(project)
    db_before = await svc.store.load()
    statuses_before = {it.id: it.status for it in db_before.items.values()}

    # "Approved" is a real status (review's lifecycle) but not a member of task's lifecycle.
    result = await invoke(["migrate", "rename-status", "task", "InProgress", "Approved"])
    assert result.exit_code != 0
    assert "not a state" in result.output

    db_after = await svc.store.load()
    statuses_after = {it.id: it.status for it in db_after.items.values()}
    assert statuses_after == statuses_before


async def test_rename_status_refuses_an_undeclared_item_type(svc) -> None:
    with pytest.raises(SquadsError, match="not declared"):
        await svc.rename_status("nosuchtype", "Draft", "Ready")


async def test_rename_status_mid_flight_failure_restores_disk_and_index(svc, monkeypatch) -> None:
    """The rename-status mutation loop has its own rollback wiring, distinct from
    rename-type's — mirror the same failure-injection technique against the sibling
    private helper it actually calls."""
    from squads._services._rename import (
        _append_rename_status_comment,  # pyright: ignore[reportPrivateUsage]
    )

    t1 = (await svc.create("task", "t1")).item
    t2 = (await svc.create("task", "t2")).item
    await svc.set_status(t1.id, "Ready")
    await svc.set_status(t2.id, "Ready")

    def _snapshot(root: Path) -> dict[str, str]:
        return {
            str(p.relative_to(root)): p.read_text(encoding="utf-8")
            for p in root.rglob("*")
            if p.is_file()
        }

    before = _snapshot(svc.paths.squad_dir)

    calls = {"n": 0}
    real = _append_rename_status_comment

    async def _flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:  # let the first item's frontmatter rewrite happen, then blow up
            raise RuntimeError("boom")
        return await real(*args, **kwargs)

    monkeypatch.setattr("squads._services._rename._append_rename_status_comment", _flaky)

    with pytest.raises(RuntimeError, match="boom"):
        await svc.rename_status("task", "Ready", "Blocked")

    assert _snapshot(svc.paths.squad_dir) == before
    db = await svc.store.load()
    assert {it.status for it in db.items.values() if it.title in ("t1", "t2")} == {"Ready"}


# --------------------------------------------------------------------------- audit trail


async def test_rename_type_and_rename_status_each_write_a_reflog_line_and_a_comment(
    project: SquadPaths, invoke
) -> None:
    svc, items = await _seed_scenario(project)
    task1_old = items["task1"].id

    result = await invoke(["migrate", "rename-type", "task", "ticket"])
    assert result.exit_code == 0, result.output

    lines = await read_lines(reflog_path(project.squad_dir))
    rename_lines = [line for line in lines if line.op == "rename-type"]
    assert len(rename_lines) == 2
    assert task1_old in {line.delta["old_id"] for line in rename_lines}

    db = await svc.store.load()
    a_ticket = next(it for it in db.items.values() if it.type == "ticket")
    text = svc.paths.abspath(a_ticket.path).read_text(encoding="utf-8")
    assert "renamed" in text and "TICKET-" in text


# --------------------------------------------------------------------------- reserved meta-types


@pytest.mark.parametrize("meta_type", ["role", "skill", "operator"])
async def test_rename_type_rejects_a_reserved_meta_type(
    project: SquadPaths, invoke, meta_type: str
) -> None:
    result = await invoke(["migrate", "rename-type", meta_type, "task"])
    assert result.exit_code != 0
    assert "reserved meta-type" in result.output


@pytest.mark.parametrize("meta_type", ["role", "skill", "operator"])
async def test_rename_status_rejects_a_reserved_meta_type(
    project: SquadPaths, invoke, meta_type: str
) -> None:
    result = await invoke(["migrate", "rename-status", meta_type, "Draft", "Ready"])
    assert result.exit_code != 0
    assert "reserved meta-type" in result.output


# --------------------------------------------------------------------------- no schema drift


async def test_rename_operations_never_bump_the_on_disk_schema_version(
    project: SquadPaths, invoke
) -> None:
    assert project.config.schema_version == SCHEMA_VERSION

    svc, _items = await _seed_scenario(project)
    await invoke(["migrate", "rename-type", "task", "ticket"])
    db = await svc.store.load()
    a_ticket = next(it for it in db.items.values() if it.type == "ticket")
    await invoke(["migrate", "rename-status", "ticket", a_ticket.status, a_ticket.status])

    from squads._paths import resolve

    assert resolve().config.schema_version == SCHEMA_VERSION
