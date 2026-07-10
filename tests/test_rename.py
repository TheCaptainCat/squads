"""Tests for ``Service.rename_type()`` (the bulk vocabulary-rename service)."""

from pathlib import Path

import pytest

from squads._errors import SquadsError
from squads._itemfile import read_frontmatter
from squads._services import _service as service
from squads._services._rename import (
    _append_rename_comment,  # pyright: ignore[reportPrivateUsage]
    _append_rename_status_comment,  # pyright: ignore[reportPrivateUsage]
    _apply_type_change,  # pyright: ignore[reportPrivateUsage]
)
from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import ItemSpec, WorkflowSpec

pytestmark = pytest.mark.anyio

# --------------------------------------------------------------------------- helpers

# "ticket" mirrors "task" exactly (same lifecycle/parent/sub-entity kind) except its
# prefix/folder — a genuine same-semantics rename, matching the feature's own example.
_TICKET = ItemSpec(
    prefix="TICKET",
    folder="tickets",
    lifecycle="work",
    parents=["feature"],
    subentity_kind="subtask",
    parent_required="feature",
)


def _svc_with_ticket(paths) -> service.Service:
    base = load_workflow_spec()
    spec = WorkflowSpec.model_validate(
        {
            "items": {**base.items, "ticket": _TICKET},
            "statuses": base.statuses,
            "lifecycles": base.lifecycles,
            "prefix_to_type": {**base.prefix_to_type, "TICKET": "ticket"},
            "alias_to_type": base.alias_to_type,
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
        }
    )
    return service.Service(paths, spec=spec)


def _snapshot_tree(root: Path) -> dict[str, str]:
    """relative-path -> text for every file under *root* (order-independent comparison)."""
    return {
        str(p.relative_to(root)): p.read_text(encoding="utf-8")
        for p in root.rglob("*")
        if p.is_file()
    }


# --------------------------------------------------------------------------- real rename (AC1)


async def test_rename_moves_id_folder_refs_and_children(svc, tmp_path):
    """task->ticket rewrites the id/folder, carries status+subtasks, and fixes up refs/parents."""
    ticket_svc = _svc_with_ticket(svc.paths)
    feat = (await svc.create("feature", "f")).item
    task = (await svc.create("task", "t", parent=feat.id)).item
    await svc.set_status(task.id, "InProgress")
    await svc.add_subtask(task.id, "do the thing")

    other = (await svc.create("bug", "b")).item
    await svc.add_ref(other.id, task.id, kind="related")
    child_bug = (await svc.create("bug", "child", parent=task.id)).item

    res = await ticket_svc.rename_type("task", "ticket")

    assert res.renamed == 1
    old_id, new_id = res.ids[0]
    assert old_id == task.id
    assert new_id.startswith("TICKET-")

    moved = await ticket_svc.get(new_id)
    assert moved.status == "InProgress"  # carried, not reset
    assert len(moved.subentities) == 1  # sub-entities carried unchanged

    new_path = ticket_svc.paths.abspath(moved.path)
    assert new_path.is_file()
    assert "tickets" in str(new_path)
    assert not list((svc.paths.squad_dir / "tasks").glob("TASK-*"))

    updated_other = await ticket_svc.get(other.id)
    assert new_id in updated_other.refs[0] and old_id not in updated_other.refs[0]

    updated_child = await ticket_svc.get(child_bug.id)
    assert updated_child.parent == new_id


async def test_rename_check_and_repair_clean(svc):
    """sq check / sq repair are clean after a bulk rename."""
    ticket_svc = _svc_with_ticket(svc.paths)
    feat = (await svc.create("feature", "f")).item
    await svc.create("task", "t1", parent=feat.id)
    await svc.create("task", "t2", parent=feat.id)

    res = await ticket_svc.rename_type("task", "ticket")
    assert res.renamed == 2

    issues = await ticket_svc.check()
    assert not [i for i in issues if i.level == "error"]
    repair_result = await ticket_svc.repair()
    assert repair_result.missing_ids == []


async def test_rename_cross_refs_between_renamed_items_resynced(svc):
    """Two renamed items referencing each other are both fixed up (same-type cross-ref)."""
    ticket_svc = _svc_with_ticket(svc.paths)
    feat = (await svc.create("feature", "f")).item
    t1 = (await svc.create("task", "t1", parent=feat.id)).item
    t2 = (await svc.create("task", "t2", parent=feat.id)).item
    await svc.add_ref(t1.id, t2.id, kind="related")

    await ticket_svc.rename_type("task", "ticket")

    t1_after = await ticket_svc.get(t1.id)  # id is stale-looking but resolves by sequence
    assert all("TASK-" not in r for r in t1_after.refs)


# --------------------------------------------------------------------------- fail-closed (atomic)


async def test_rename_refuses_undeclared_new_type(svc, tmp_path):
    """new_type must already be declared in the active spec — no auto-declare."""
    before = _snapshot_tree(svc.paths.squad_dir)
    await svc.create("task", "t")

    with pytest.raises(SquadsError, match="not declared"):
        await svc.rename_type("task", "ticket")

    # the create above IS on disk; re-snapshot after it, then prove the failed rename
    # touched nothing further.
    after_create = _snapshot_tree(svc.paths.squad_dir)
    assert before != after_create  # sanity: create did write something
    with pytest.raises(SquadsError):
        await svc.rename_type("task", "ticket")
    assert _snapshot_tree(svc.paths.squad_dir) == after_create


async def test_rename_refuses_reserved_meta_type(svc):
    """role/skill/operator are reserved meta-types and cannot be renamed either way."""
    ticket_svc = _svc_with_ticket(svc.paths)
    with pytest.raises(SquadsError, match="reserved meta-type"):
        await ticket_svc.rename_type("role", "ticket")
    with pytest.raises(SquadsError, match="reserved meta-type"):
        await ticket_svc.rename_type("task", "role")


async def test_rename_refuses_same_type(svc):
    with pytest.raises(SquadsError, match="itself"):
        await svc.rename_type("task", "task")


async def test_rename_refuses_invalid_parent_child(svc):
    """A child requiring the old parent type would be invalid under the new type -> refused,
    with nothing on disk touched."""
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
    task = (await svc.create("task", "t", parent=feat.id)).item  # task requires a feature parent

    before = _snapshot_tree(svc.paths.squad_dir)
    with pytest.raises(SquadsError, match="child item"):
        await generic_svc.rename_type("feature", "generic")
    assert _snapshot_tree(svc.paths.squad_dir) == before

    # the task is unaffected
    still = await svc.get(task.id)
    assert still.id == task.id


async def test_rename_no_items_is_a_noop(svc):
    """Renaming a type with zero live items succeeds trivially."""
    ticket_svc = _svc_with_ticket(svc.paths)
    res = await ticket_svc.rename_type("task", "ticket")
    assert res.renamed == 0
    assert res.ids == []


async def test_rename_mid_flight_failure_restores_disk_and_index(svc, monkeypatch, tmp_path):
    """An error after the first item's file has already moved rolls the filesystem back too —
    the index is never written mid-transaction, but the file move/rewrite is eager, so the
    rollback is what actually keeps the squad byte-identical."""
    ticket_svc = _svc_with_ticket(svc.paths)
    feat = (await svc.create("feature", "f")).item
    await svc.create("task", "t1", parent=feat.id)
    await svc.create("task", "t2", parent=feat.id)

    before = _snapshot_tree(svc.paths.squad_dir)

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

    assert _snapshot_tree(svc.paths.squad_dir) == before
    db = await svc.store.load()
    assert {it.type for it in db.items.values() if it.title in ("t1", "t2")} == {"task"}


async def test_rename_failure_after_rewrite_ids_restores_everything(svc, monkeypatch):
    """A failure in the post-rewrite audit loop — after rewrite_ids + _resync_edges have
    already touched every squad file — still rolls back to byte-identical disk (and hence
    index + reflog, both under the same squad_dir snapshot)."""
    ticket_svc = _svc_with_ticket(svc.paths)
    feat = (await svc.create("feature", "f")).item
    await svc.create("task", "t1", parent=feat.id)
    await svc.create("task", "t2", parent=feat.id)

    before = _snapshot_tree(svc.paths.squad_dir)

    calls = {"n": 0}
    real = _append_rename_comment

    async def _flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:  # first item's comment/reflog land; whole-squad rewrite is done
            raise RuntimeError("boom-after-rewrite")
        return await real(*args, **kwargs)

    monkeypatch.setattr("squads._services._rename._append_rename_comment", _flaky)

    with pytest.raises(RuntimeError, match="boom-after-rewrite"):
        await ticket_svc.rename_type("task", "ticket")

    assert _snapshot_tree(svc.paths.squad_dir) == before


# --------------------------------------------------------------------------- audit trail (AC3)


async def test_rename_writes_reflog_and_comment_per_item(svc):
    """Each renamed item gets a reflog line and a system discussion comment."""
    from squads._index._reflog import read_lines, reflog_path

    ticket_svc = _svc_with_ticket(svc.paths)
    task = (await svc.create("task", "t")).item
    old_id = task.id

    res = await ticket_svc.rename_type("task", "ticket")
    new_id = res.ids[0][1]

    lines = await read_lines(reflog_path(svc.paths.squad_dir))
    entry = next(line for line in lines if line.op == "rename-type")
    assert entry.delta["old_id"] == old_id
    assert entry.delta["new_id"] == new_id
    assert entry.delta["old_type"] == "task"
    assert entry.delta["new_type"] == "ticket"

    moved = await ticket_svc.get(new_id)
    text = ticket_svc.paths.abspath(moved.path).read_text(encoding="utf-8")
    assert old_id in text and new_id in text  # the audit comment names both ids

    fm = read_frontmatter(ticket_svc.paths.abspath(moved.path))
    assert fm["type"] == "ticket"


async def test_extra_field_stays_settable_after_type_rename(svc):
    """guide->doc: --set tags still works post-rename (EXTRA_FIELDS keys by spec identity,
    not by the bundled literal type name)."""
    base = load_workflow_spec()
    doc_type = ItemSpec(
        prefix="DOC",
        folder="docs",
        lifecycle=base.items["guide"].lifecycle,
        extra_fields=["tags"],
    )
    doc_spec = WorkflowSpec.model_validate(
        {
            "items": {**base.items, "doc": doc_type},
            "statuses": base.statuses,
            "lifecycles": base.lifecycles,
            "prefix_to_type": {**base.prefix_to_type, "DOC": "doc"},
            "alias_to_type": base.alias_to_type,
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
        }
    )
    doc_svc = service.Service(svc.paths, spec=doc_spec)

    await svc.create("guide", "g")
    res = await doc_svc.rename_type("guide", "doc")
    new_id = res.ids[0][1]

    updated = await doc_svc.update(new_id, set_extra={"tags": "a,b"})
    assert updated.extra["tags"] == ["a", "b"]

    with pytest.raises(SquadsError, match="not a settable field"):
        await doc_svc.update(new_id, set_extra={"target_ref": "TASK-1"})


# --------------------------------------------------------------------------- rename_status (AC2)


async def test_rename_status_moves_matching_items_only(svc):
    """All task items at old_status move to new_status; a task NOT at old_status is untouched."""
    t1 = (await svc.create("task", "t1")).item
    t2 = (await svc.create("task", "t2")).item
    other = (await svc.create("task", "other")).item
    await svc.set_status(t1.id, "Ready")
    await svc.set_status(t2.id, "Ready")
    await svc.set_status(other.id, "InProgress")

    res = await svc.rename_status("task", "Ready", "Blocked")

    assert res.renamed == 2
    assert {new.status for new in [await svc.get(t1.id), await svc.get(t2.id)]} == {"Blocked"}
    assert (await svc.get(other.id)).status == "InProgress"  # untouched


async def test_rename_status_scoped_to_one_type(svc):
    """A bug sharing old_status with a task is not touched by a task-scoped rename."""
    task = (await svc.create("task", "t")).item
    bug = (await svc.create("bug", "b")).item
    await svc.set_status(task.id, "InProgress")
    await svc.set_status(bug.id, "InProgress")  # bug's own lifecycle also has InProgress

    await svc.rename_status("task", "InProgress", "Blocked")

    assert (await svc.get(task.id)).status == "Blocked"
    assert (await svc.get(bug.id)).status == "InProgress"  # different type, untouched


async def test_rename_status_leaves_subentities_untouched(svc):
    """Sub-entity status vocabulary (a separate axis) is never touched by a top-level rename."""
    task = (await svc.create("task", "t")).item
    await svc.add_subtask(task.id, "do the thing")
    before_sub_status = (await svc.get(task.id)).subentities[0].status

    await svc.rename_status("task", "Draft", "Ready")

    moved = await svc.get(task.id)
    assert moved.status == "Ready"
    assert moved.subentities[0].status == before_sub_status


async def test_rename_status_refuses_non_member_new_status(svc):
    """new_status must resolve as a STATE of the type's own lifecycle."""
    before = _snapshot_tree(svc.paths.squad_dir)
    await svc.create("task", "t")
    after_create = _snapshot_tree(svc.paths.squad_dir)
    assert before != after_create

    with pytest.raises(SquadsError, match="not a state"):
        await svc.rename_status("task", "Draft", "NoSuchState")

    assert _snapshot_tree(svc.paths.squad_dir) == after_create


async def test_rename_status_refuses_reserved_meta_type(svc):
    with pytest.raises(SquadsError, match="reserved meta-type"):
        await svc.rename_status("role", "Draft", "Active")


async def test_rename_status_refuses_undeclared_type(svc):
    with pytest.raises(SquadsError, match="not declared"):
        await svc.rename_status("nosuchtype", "Draft", "Ready")


async def test_rename_status_no_items_is_a_noop(svc):
    res = await svc.rename_status("task", "Draft", "Ready")
    assert res.renamed == 0
    assert res.ids == []


async def test_rename_status_mid_flight_failure_restores_disk_and_index(svc, monkeypatch):
    """An error partway through the mutation loop rolls the filesystem (and hence index +
    reflog) back to byte-identical, even though frontmatter was already rewritten eagerly."""
    t1 = (await svc.create("task", "t1")).item
    t2 = (await svc.create("task", "t2")).item
    await svc.set_status(t1.id, "Ready")
    await svc.set_status(t2.id, "Ready")

    before = _snapshot_tree(svc.paths.squad_dir)

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

    assert _snapshot_tree(svc.paths.squad_dir) == before
    db = await svc.store.load()
    assert {it.status for it in db.items.values() if it.title in ("t1", "t2")} == {"Ready"}


async def test_rename_status_writes_reflog_and_comment_per_item(svc):
    """Each moved item gets a reflog line and a system discussion comment."""
    from squads._index._reflog import read_lines, reflog_path

    task = (await svc.create("task", "t")).item
    await svc.set_status(task.id, "Ready")

    await svc.rename_status("task", "Ready", "Blocked")

    lines = await read_lines(reflog_path(svc.paths.squad_dir))
    entry = next(line for line in lines if line.op == "rename-status")
    assert entry.target == task.id
    assert entry.delta["type"] == "task"
    assert entry.delta["old_status"] == "Ready"
    assert entry.delta["new_status"] == "Blocked"

    moved = await svc.get(task.id)
    assert moved.status == "Blocked"
    text = svc.paths.abspath(moved.path).read_text(encoding="utf-8")
    assert "Ready" in text and "Blocked" in text  # the audit comment names both statuses

    fm = read_frontmatter(svc.paths.abspath(moved.path))
    assert fm["status"] == "Blocked"
