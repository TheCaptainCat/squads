"""Feature-acceptance sweep for vocabulary rename migrations (`sq migrate rename-type` /
`sq migrate rename-status`).

Independent of the per-task unit/smoke tests (test_rename.py): this module drives the real
CLI surface against a squad that declares its custom type through an actual
`.overrides/workflow.toml` file on disk (not a hand-built `WorkflowSpec` passed straight to a
`Service` — that bypasses the loader/merge/validate path a real project actually goes through),
seeds realistic data (sub-entities, non-initial statuses, cross-refs, prose mentions), and
proves the acceptance criteria end-to-end rather than trusting green unit tests.
"""

from pathlib import Path

import pytest

from squads._index._reflog import read_lines, reflog_path
from squads._migrations._registry import MIGRATIONS
from squads._models._schema import SCHEMA_VERSION, schema_tuple
from squads._paths import SquadPaths
from squads._services import _service as service

pytestmark = pytest.mark.anyio

# --------------------------------------------------------------------------- helpers

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


def _snapshot_statuses(items) -> dict[str, str]:
    return {it.id: it.status for it in items.values()}


async def _seed_scenario(project: SquadPaths):
    """Seed a realistic squad: FEAT/TASK/REV carrying sub-entities, non-initial statuses,
    cross-refs, and prose @mentions/ID mentions between them. Returns the ticket-aware
    Service (loaded from the real .overrides/workflow.toml) plus the created items.

    Proves the feature's own documented pattern: the
    `.overrides/workflow.toml` declaring `ticket` (subentity_kind="subtask", same kind as
    `task`) is written and loaded through the real loader/merge/validate path FIRST, and
    ordinary work -- including adding subtasks -- then continues on a pre-existing `task`
    item while both types share that kind, before rename-type ever runs.
    """
    _write_override(project.squad_dir, _TICKET_OVERRIDE)
    # open_service() reads .overrides/workflow.toml from disk through the real
    # loader/merge/validate path -- the honest end-to-end wiring this sweep is for. Relies
    # on the `project` fixture having chdir'd into the squad root, same as open_service()'s
    # other callers (the CLI root callback, test_workflow_override.py).
    svc = service.open_service()

    feat = (await svc.create("feature", "widget epic", author="manager")).item
    task1 = (await svc.create("task", "first ticket task", parent=feat.id, author="manager")).item
    task2 = (await svc.create("task", "second ticket task", parent=feat.id, author="manager")).item
    rev = (await svc.create("review", "code review of the widget", author="manager")).item
    bug = (
        await svc.create("bug", "regression found in task1", parent=task1.id, author="manager")
    ).item

    # Sub-entities on all three types (only task's must survive the rename unconditionally).
    # task1/task2 are pre-existing `task` items and `ticket` (same subentity_kind) is already
    # declared -- the exact two-types-share-a-kind scenario that used to break add_subtask.
    await svc.add_story(feat.id, "as a user I want widgets")
    await svc.add_subtask(task1.id, "implement the widget")
    await svc.add_subtask(task2.id, "wire up the widget UI")
    await svc.add_finding(rev.id, "missing null check")

    # Non-initial statuses (retype's guardrails would reset these on a genuine reclassification).
    await svc.set_status(task1.id, "InProgress")
    await svc.set_status(task2.id, "InProgress")
    await svc.set_status(task2.id, "Blocked")
    await svc.set_status(rev.id, "InReview")

    # Cross-refs: between the two renamed items, and from an unrenamed REV into a renamed TASK.
    await svc.add_ref(task1.id, task2.id, kind="related")
    await svc.add_ref(rev.id, task1.id, kind="related")

    # Prose: ID mentions of renamed items embedded in body/comment text, plus an @mention.
    await svc.set_body(
        task1.id, f"Coordinates with {task2.id} and is reviewed in {rev.id}. @qa please check."
    )
    await svc.comment(
        rev.id,
        [f"raised while looking at {task1.id}", "@qa please verify after the rename"],
        as_slug="manager",
    )

    return svc, {"feat": feat, "task1": task1, "task2": task2, "rev": rev, "bug": bug}


# --------------------------------------------------------------------------- AC1: rename-type


async def test_rename_type_end_to_end_preserves_subentities_status_and_refs(
    project: SquadPaths, invoke
) -> None:
    """rename-type task ticket, driven through the real CLI against a real workflow.toml
    override: ids/folder rewritten, parent/refs/prose fixed up, sub-entities and status
    carried unconditionally (the whole point of the feature, unlike retype's guardrails)."""
    svc, items = await _seed_scenario(project)
    task1_old, task2_old, feat_id = items["task1"].id, items["task2"].id, items["feat"].id
    rev_id, bug_id = items["rev"].id, items["bug"].id

    result = await invoke(["migrate", "rename-type", "task", "ticket"])
    assert result.exit_code == 0, result.output

    db = await svc.store.load()
    ticket_ids = {it.id for it in db.items.values() if it.type == "ticket"}
    assert len(ticket_ids) == 2
    assert all(tid.startswith("TICKET-") for tid in ticket_ids)
    assert not any(it.type == "task" for it in db.items.values())

    new_task1 = next(it for it in db.items.values() if it.title == "first ticket task")
    new_task2 = next(it for it in db.items.values() if it.title == "second ticket task")

    # Status carried unconditionally -- retype would refuse/reset given sub-entities present.
    assert new_task1.status == "InProgress"
    assert new_task2.status == "Blocked"

    # Sub-entities carried unchanged.
    assert len(new_task1.subentities) == 1
    assert new_task1.subentities[0].title == "implement the widget"
    assert len(new_task2.subentities) == 1

    # Folder actually moved on disk.
    assert not list((project.squad_dir / "tasks").glob("TASK-*"))
    ticket_files = list((project.squad_dir / "tickets").glob("TICKET-*"))
    assert len(ticket_files) == 2

    # Parent link (feature -> task) still resolves, now to the new id.
    assert new_task1.parent == feat_id
    assert new_task2.parent == feat_id

    # Child link (bug's parent was task1) rewritten to the new ticket id.
    new_bug = await svc.get(bug_id)
    assert new_bug.parent == new_task1.id
    assert new_bug.parent != task1_old

    # Cross-ref between the two renamed items resynced both ways.
    assert any(new_task2.id in r for r in new_task1.refs)
    assert not any(task2_old in r for r in new_task1.refs)

    # Ref from the unrenamed REV into the renamed TASK resynced.
    new_rev = await svc.get(rev_id)
    assert any(new_task1.id in r for r in new_rev.refs)
    assert not any(task1_old in r for r in new_rev.refs)

    # Prose ID mentions rewritten in the renamed item's own body and in another item's comment.
    task1_text = svc.paths.abspath(new_task1.path).read_text(encoding="utf-8")
    assert new_task2.id in task1_text
    assert task2_old not in task1_text
    assert new_rev.id in task1_text  # rev wasn't renamed, unaffected either way

    rev_text = svc.paths.abspath(new_rev.path).read_text(encoding="utf-8")
    assert new_task1.id in rev_text
    assert task1_old not in rev_text
    assert "@qa" in rev_text  # role mentions are untouched by a type rename


async def test_rename_type_check_and_repair_clean_no_diff(project: SquadPaths, invoke) -> None:
    """sq check and sq repair are both clean after rename-type; repair produces no diff --
    the frontmatter/index reconstruct identically (proves frontmatter is the source of truth)."""
    svc, _items = await _seed_scenario(project)

    result = await invoke(["migrate", "rename-type", "task", "ticket"])
    assert result.exit_code == 0, result.output

    check_result = await invoke(["check"])
    assert check_result.exit_code == 0, check_result.output

    db_before = await svc.store.load()
    before_snapshot = {seq: it.model_dump(mode="json") for seq, it in db_before.items.items()}

    repair_result = await svc.repair()
    assert repair_result.missing_ids == []

    db_after = repair_result.db
    after_snapshot = {seq: it.model_dump(mode="json") for seq, it in db_after.items.items()}

    assert before_snapshot == after_snapshot, (
        "repair changed item data -- index is not a pure rebuild"
    )


# --------------------------------------------------------------------------- AC2: rename-status


async def test_rename_status_invalid_target_fails_closed_no_partial_rewrite(
    project: SquadPaths, invoke
) -> None:
    """rename-status to a status that exists in the spec but is NOT a member of the type's own
    lifecycle fails cleanly, with every item's status left untouched (no partial rewrite)."""
    svc, _items = await _seed_scenario(project)
    db_before = await svc.store.load()
    statuses_before = _snapshot_statuses(db_before.items)

    # "Approved" is a real status (review's lifecycle) but not a member of task's lifecycle.
    result = await invoke(["migrate", "rename-status", "task", "InProgress", "Approved"])
    assert result.exit_code != 0
    assert "not a state" in result.output

    db_after = await svc.store.load()
    statuses_after = _snapshot_statuses(db_after.items)
    assert statuses_after == statuses_before, "a failed rename-status left a partial rewrite"


async def test_rename_status_happy_path_moves_all_matching_items(
    project: SquadPaths, invoke
) -> None:
    """rename-status moves every item of the type currently at old_status to new_status, and
    leaves non-matching items (other statuses, other types) untouched."""
    svc, items = await _seed_scenario(project)
    task1_id, task2_id, rev_id = items["task1"].id, items["task2"].id, items["rev"].id

    # task1=InProgress, task2=Blocked, rev=InReview (a different type, same-named status exists
    # in review's own lifecycle too -- proves the rename is scoped per-type).
    result = await invoke(["migrate", "rename-status", "task", "InProgress", "InReview"])
    assert result.exit_code == 0, result.output

    moved_task1 = await svc.get(task1_id)
    untouched_task2 = await svc.get(task2_id)
    untouched_rev = await svc.get(rev_id)
    assert moved_task1.status == "InReview"
    assert untouched_task2.status == "Blocked"  # different old_status, untouched
    assert untouched_rev.status == "InReview"  # already InReview before the call, untouched type


# --------------------------------------------------------------------------- AC3: audit trail


async def test_rename_type_writes_reflog_and_comment_per_renamed_item(
    project: SquadPaths, invoke
) -> None:
    svc, items = await _seed_scenario(project)
    task1_old, task2_old = items["task1"].id, items["task2"].id

    result = await invoke(["migrate", "rename-type", "task", "ticket"])
    assert result.exit_code == 0, result.output

    lines = await read_lines(reflog_path(project.squad_dir))
    rename_lines = [line for line in lines if line.op == "rename-type"]
    assert len(rename_lines) == 2
    old_ids_logged = {line.delta["old_id"] for line in rename_lines}
    assert old_ids_logged == {task1_old, task2_old}

    db = await svc.store.load()
    for it in db.items.values():
        if it.type == "ticket":
            text = svc.paths.abspath(it.path).read_text(encoding="utf-8")
            assert "renamed" in text and "TICKET-" in text  # system audit comment landed


async def test_rename_status_writes_reflog_and_comment_per_moved_item(
    project: SquadPaths, invoke
) -> None:
    svc, items = await _seed_scenario(project)
    task1_id = items["task1"].id

    result = await invoke(["migrate", "rename-status", "task", "InProgress", "InReview"])
    assert result.exit_code == 0, result.output

    lines = await read_lines(reflog_path(project.squad_dir))
    status_lines = [line for line in lines if line.op == "rename-status"]
    assert len(status_lines) == 1
    assert status_lines[0].target == task1_id
    assert status_lines[0].delta == {
        "type": "task",
        "old_status": "InProgress",
        "new_status": "InReview",
    }

    moved = await svc.get(task1_id)
    text = svc.paths.abspath(moved.path).read_text(encoding="utf-8")
    assert "status renamed" in text
    assert "InProgress" in text and "InReview" in text


# --------------------------------------------------------------------------- AC4: reserved meta


@pytest.mark.parametrize("meta_type", ["role", "skill", "operator"])
async def test_rename_type_rejects_reserved_meta_type(
    project: SquadPaths, invoke, meta_type: str
) -> None:
    result = await invoke(["migrate", "rename-type", meta_type, "task"])
    assert result.exit_code != 0
    assert "reserved meta-type" in result.output


@pytest.mark.parametrize("meta_type", ["role", "skill", "operator"])
async def test_rename_status_rejects_reserved_meta_type(
    project: SquadPaths, invoke, meta_type: str
) -> None:
    result = await invoke(["migrate", "rename-status", meta_type, "Draft", "Ready"])
    assert result.exit_code != 0
    assert "reserved meta-type" in result.output


# --------------------------------------------------------------------------- AC5: no schema drift


async def test_rename_operations_do_not_bump_schema_version(project: SquadPaths, invoke) -> None:
    disk_before = project.config.schema_version
    assert disk_before == SCHEMA_VERSION

    svc, items = await _seed_scenario(project)
    await invoke(["migrate", "rename-type", "task", "ticket"])
    ticket_ids = [it for it in items.values() if it.type == "task"]
    _ = ticket_ids
    db = await svc.store.load()
    a_ticket = next(it for it in db.items.values() if it.type == "ticket")
    await invoke(["migrate", "rename-status", "ticket", a_ticket.status, a_ticket.status])
    # (a same-status "rename" is a legal no-op move; the point is exercising the command path)

    from squads._paths import resolve

    disk_after = resolve().config.schema_version
    assert disk_after == SCHEMA_VERSION == disk_before


def test_migrations_registry_has_no_rename_entry() -> None:
    """Guards the re-baseline decision: rename-type/rename-status are on-demand `sq migrate`
    sub-commands like `repad`, deliberately never registered in the SCHEMA_VERSION-gated
    up-chain."""
    assert not any("rename" in m.summary.lower() for m in MIGRATIONS)
    highest = max(schema_tuple(m.to_schema) for m in MIGRATIONS)
    assert highest == schema_tuple(SCHEMA_VERSION), (
        "a schema-gated migration exists past the current SCHEMA_VERSION -- "
        "rename-type/rename-status must never be registered here"
    )
