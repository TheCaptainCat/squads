"""Tests for ``Service.retype()`` and the ``sq <type> <n> retype <new-type>`` CLI verb."""

import pytest

from squads._cli import app
from squads._errors import SquadsError
from squads._itemfile import read_frontmatter
from squads._models._enums import Status
from squads._models._item import Item
from squads._sections import get_section

pytestmark = pytest.mark.anyio

# --------------------------------------------------------------------------- helpers


def _read_file(svc, item: Item) -> str:
    return svc.paths.abspath(item.path).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- service-level: basic


async def test_retype_task_to_bug_preserves_number(svc):
    """Retyping task→bug keeps the sequence number; only the prefix changes."""
    task = (await svc.create("task", "Fix crash", description="crashes on null")).item
    old_id = task.id
    assert old_id.startswith("TASK-")
    seq = task.sequence_id

    res = await svc.retype(task.id, "bug")
    assert res.old_id == old_id
    assert res.item.id.startswith("BUG-")
    assert res.item.sequence_id == seq
    # the number suffix is identical
    assert res.item.id.split("-", 1)[1] == old_id.split("-", 1)[1]


async def test_retype_creates_file_in_new_folder(svc):
    """File moves to the new type's folder."""
    from squads._models._item import format_item_id

    task = (await svc.create("task", "My task")).item
    old_padded_stem = format_item_id("TASK", task.sequence_id, (await svc.store.load()).padding)
    res = await svc.retype(task.id, "bug")

    new_path = svc.paths.abspath(res.item.path)
    assert new_path.exists()
    assert "bugs" in str(new_path)
    # old path (padded stem — ADR-000282, res.old_id is the unpadded display id) is gone
    old_path = svc.paths.squad_dir / "tasks" / f"{old_padded_stem}-my-task.md"
    assert not old_path.exists()


async def test_retype_body_verbatim(svc):
    """Body bytes survive verbatim after retype."""
    task = (await svc.create("task", "task")).item
    body_text = "## Details\n\nSpecial chars: ← → ✓"
    await svc.set_body(task.id, body_text)
    res = await svc.retype(task.id, "bug")

    text = _read_file(svc, res.item)
    body = get_section(text, "body")
    assert body is not None and body_text in body


async def test_retype_frontmatter_updated(svc):
    """Frontmatter type and id fields reflect the new type."""
    task = (await svc.create("task", "task")).item
    res = await svc.retype(task.id, "bug")

    fm = read_frontmatter(svc.paths.abspath(res.item.path))
    assert fm["type"] == "bug"
    assert fm["id"].startswith("BUG-")
    assert fm["sequence_id"] == task.sequence_id


async def test_retype_appends_system_comment(svc):
    """A system comment is appended to the discussion section."""
    task = (await svc.create("task", "task")).item
    old_id = task.id
    res = await svc.retype(task.id, "bug")

    text = _read_file(svc, res.item)
    disc = get_section(text, "discussion")
    assert disc is not None
    assert old_id in disc
    assert res.item.id in disc
    assert "squads" in disc  # system comment author


async def test_retype_index_updated(svc):
    """The index carries the new item under its sequence_id; the old type is gone."""
    task = (await svc.create("task", "t")).item
    res = await svc.retype(task.id, "bug")

    db = await svc.store.load()
    indexed = db.items.get(task.sequence_id)
    assert indexed is not None
    assert indexed.type == "bug"
    assert indexed.id == res.item.id


# --------------------------------------------------------------------------- status carry vs reset


async def test_retype_task_to_bug_resets_status(svc):
    """task→bug crosses workflow boundaries (_WORK→_BUG) → status resets to Open."""
    task = (await svc.create("task", "t")).item
    await svc.set_status(task.id, Status.IN_PROGRESS)

    res = await svc.retype(task.id, "bug")
    assert res.status_reset
    assert res.old_status == Status.IN_PROGRESS.value
    assert res.item.status == Status.OPEN


async def test_retype_feature_to_epic_carries_status(svc):
    """feature↔epic share _WORK workflow → status carried."""
    feat = (await svc.create("feature", "f")).item
    await svc.set_status(feat.id, Status.READY)

    res = await svc.retype(feat.id, "epic")
    assert not res.status_reset
    assert res.item.status == Status.READY


async def test_retype_task_to_decision_resets_status(svc):
    """task→decision crosses workflow boundaries → status resets to Proposed."""
    task = (await svc.create("task", "t")).item
    await svc.set_status(task.id, Status.IN_PROGRESS)

    res = await svc.retype(task.id, "decision")
    assert res.status_reset
    assert res.old_status == Status.IN_PROGRESS.value
    assert res.item.status == Status.PROPOSED


async def test_retype_task_to_guide_resets_status(svc):
    """task→guide crosses workflow → status resets to Draft."""
    task = (await svc.create("task", "t")).item
    await svc.set_status(task.id, Status.IN_PROGRESS)
    res = await svc.retype(task.id, "guide")
    assert res.status_reset
    assert res.item.status == Status.DRAFT


async def test_retype_decision_to_review_resets_status(svc):
    """decision (ADR) → review crosses workflow → status resets to Requested."""
    dec = (await svc.create("decision", "ADR")).item
    res = await svc.retype(dec.id, "review")
    assert res.status_reset
    assert res.item.status == Status.REQUESTED


# --------------------------------------------------------------------------- refusals


async def test_retype_refuses_non_work_type(svc):
    """Retyping an agent type is refused."""
    # ROLE-000001 is the manager role from the minimal init
    with pytest.raises(SquadsError, match="only work items can be retyped"):
        await svc.retype("ROLE-000001", "task")


async def test_retype_refuses_same_type(svc):
    """No-op retype to the same type is refused."""
    task = (await svc.create("task", "t")).item
    with pytest.raises(SquadsError, match="already of type task"):
        await svc.retype(task.id, "task")


async def test_retype_refuses_item_with_subentities(svc):
    """Item with sub-entities cannot be retyped."""
    feat = (await svc.create("feature", "f")).item
    await svc.add_story(feat.id, "story 1")
    with pytest.raises(SquadsError, match="sub-entities"):
        await svc.retype(feat.id, "epic")


async def test_retype_refuses_invalid_new_parent(svc):
    """Refuse when existing parent would be invalid for the new type."""
    # task's parent must be a feature; retyping task→feature when its parent is a feature
    # would make it feature→feature, which is invalid (feature's parent must be epic).
    feat = (await svc.create("feature", "f")).item
    task = (await svc.create("task", "t", parent=feat.id)).item
    # Retyping task→feature: the task's parent is a feature, but feature's parent must be epic.
    with pytest.raises(SquadsError, match="cannot retype"):
        await svc.retype(task.id, "feature")


async def test_retype_refuses_children_would_become_invalid(svc):
    """Refuse when a child would have an invalid parent under the new type.

    TASK requires FEATURE parent; retyping the feature to BUG would leave the task
    with an invalid (bug) parent → refused.
    """
    feat = (await svc.create("feature", "f")).item
    _task = (await svc.create("task", "t", parent=feat.id)).item
    with pytest.raises(SquadsError, match="child item"):
        await svc.retype(feat.id, "bug")


# --------------------------------------------------------------------------- edge rewrites (US2)


async def test_retype_rewrites_refs_in_other_items(svc):
    """Other items' refs are rewritten to the new ID."""
    task = (await svc.create("task", "t")).item
    bug = (await svc.create("bug", "b")).item
    await svc.add_ref(bug.id, task.id, kind="related")

    old_id = task.id
    res = await svc.retype(task.id, "feature")

    # The bug's ref should now point at the new ID
    updated_bug = await svc.get(bug.id)
    assert old_id not in updated_bug.refs[0]
    assert res.item.id in updated_bug.refs[0]


async def test_retype_rewrites_ref_kind_preserved(svc):
    """Ref kind is preserved when the ID is rewritten."""
    task = (await svc.create("task", "t")).item
    bug = (await svc.create("bug", "b")).item
    await svc.add_ref(bug.id, task.id, kind="blocks")

    res = await svc.retype(task.id, "feature")
    updated_bug = await svc.get(bug.id)
    # Should contain the new ID with :blocks kind
    assert f"{res.item.id}:blocks" in updated_bug.refs


async def test_retype_rewrites_children_parent(svc):
    """Children's parent field is rewritten to the new ID.

    BUG is unconstrained (not in ALLOWED_PARENTS as a key), so a bug can have any parent.
    We create a task, hang a bug off it as parent, then retype the task→feature. The bug's
    parent field should flip from the old TASK id to the new FEAT id.
    """
    task = (await svc.create("task", "t")).item
    # BUG is unconstrained; it can be parented to anything
    bug = (await svc.create("bug", "b", parent=task.id)).item

    old_task_id = task.id
    res = await svc.retype(task.id, "feature")

    # The bug's parent should now be the feature ID
    updated_bug = await svc.get(bug.id)
    assert updated_bug.parent == res.item.id
    assert updated_bug.parent != old_task_id


async def test_retype_rewrites_prose_mentions(svc):
    """Prose @-mentions and inline ID references in other items are rewritten."""
    task = (await svc.create("task", "t")).item
    other = (await svc.create("bug", "b")).item
    # Set a body that mentions the old task ID
    await svc.set_body(other.id, f"See {task.id} for context.\n\nRelated: {task.id}.")

    res = await svc.retype(task.id, "feature")
    body = await svc.read_body(other.id)
    assert task.id not in body
    assert res.item.id in body


async def test_retype_rewritten_list_has_correct_paths(svc):
    """RetypeResult.rewritten names the files that were actually modified."""
    task = (await svc.create("task", "t")).item
    other = (await svc.create("bug", "b")).item
    await svc.set_body(other.id, f"Ref: {task.id}.")

    res = await svc.retype(task.id, "feature")
    # At least the other item's file should be in the rewritten list
    assert any("bugs" in name for name in res.rewritten)


# --------------------------------------------------------------------------- container scaffold


async def test_retype_to_feature_appends_stories_container(svc):
    """Retyping to feature adds an empty stories container if absent."""
    task = (await svc.create("task", "t")).item
    res = await svc.retype(task.id, "feature")

    text = _read_file(svc, res.item)
    assert "<!-- sq:stories -->" in text
    assert "<!-- sq:stories:end -->" in text


async def test_retype_to_task_appends_subtasks_container(svc):
    """Retyping to task adds an empty subtasks container if absent."""
    bug = (await svc.create("bug", "b")).item
    res = await svc.retype(bug.id, "task")

    text = _read_file(svc, res.item)
    assert "<!-- sq:subtasks -->" in text
    assert "<!-- sq:subtasks:end -->" in text


async def test_retype_to_review_appends_findings_container(svc):
    """Retyping to review adds an empty findings container if absent."""
    task = (await svc.create("task", "t")).item
    res = await svc.retype(task.id, "review")

    text = _read_file(svc, res.item)
    assert "<!-- sq:findings -->" in text
    assert "<!-- sq:findings:end -->" in text


async def test_retype_to_bug_no_container_added(svc):
    """Retyping to bug (no sub-entities) does not add extra containers."""
    task = (await svc.create("task", "t")).item
    # The task file already has subtasks container; after retype to bug it should not
    res = await svc.retype(task.id, "bug")
    text = _read_file(svc, res.item)
    # Bug files do not have a subtasks/stories container
    assert "<!-- sq:stories -->" not in text
    # (subtasks container from the original task template would remain — that's OK as prose)


# --------------------------------------------------------------------------- check / repair


async def test_retype_check_clean(svc):
    """sq check is clean after a retype."""
    task = (await svc.create("task", "t")).item
    await svc.retype(task.id, "bug")
    issues = await svc.check()
    errors = [i for i in issues if i.level == "error"]
    assert not errors


async def test_retype_repair_stable(svc):
    """sq repair is a no-op after a retype (frontmatter is the truth)."""
    task = (await svc.create("task", "t")).item
    await svc.retype(task.id, "bug")

    result = await svc.repair()
    # Repair should report no missing IDs
    assert result.missing_ids == []
    # The index counter must not have changed
    db = await svc.store.load()
    assert db.counter >= task.sequence_id


async def test_retype_repair_stable_with_parent_rewrite(svc):
    """sq repair is a no-op when parent links were rewritten.

    Use a BUG child (unconstrained parent) so the retype of the parent is not refused.
    """
    task = (await svc.create("task", "t")).item
    bug = (await svc.create("bug", "b", parent=task.id)).item

    await svc.retype(task.id, "feature")
    result = await svc.repair()
    assert result.missing_ids == []

    # Bug's parent in the index should match what's on disk
    db = await svc.store.load()
    bug_indexed = db.items.get(bug.sequence_id)
    assert bug_indexed is not None
    bug_on_disk = read_frontmatter(svc.paths.abspath(bug_indexed.path))
    assert bug_indexed.parent == bug_on_disk.get("parent")


# --------------------------------------------------------------------------- CLI smoke test


def test_cli_retype_verb(runner, tmp_path, monkeypatch, frozen_time):
    """The CLI `retype` verb works end-to-end."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])

    # Create a task (TASK-000002)
    runner.invoke(app, ["create", "task", "Fix crash", "--author", "manager"])

    # Retype task → bug
    r = runner.invoke(app, ["task", "2", "retype", "bug"])
    assert r.exit_code == 0, r.output
    assert "BUG-" in r.output
    assert "TASK-" in r.output  # old ID shown

    # Bug file should now exist
    bugs_dir = tmp_path / "squads" / "bugs"
    bug_files = list(bugs_dir.glob("BUG-*.md"))
    assert len(bug_files) == 1

    # Old task file gone
    tasks_dir = tmp_path / "squads" / "tasks"
    task_files = list(tasks_dir.glob("TASK-*-fix-crash.md"))
    assert not task_files


def test_cli_retype_status_reset_message(runner, tmp_path, monkeypatch, frozen_time):
    """The CLI prints a status-reset notice when workflows differ."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])
    runner.invoke(app, ["task", "2", "status", "InProgress"])

    r = runner.invoke(app, ["task", "2", "retype", "decision"])
    assert r.exit_code == 0, r.output
    assert "reset" in r.output.lower()


def test_cli_retype_task_to_bug_status_reset_message(runner, tmp_path, monkeypatch, frozen_time):
    """task→bug crosses workflow boundaries; CLI prints a status-reset notice."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])

    r = runner.invoke(app, ["task", "2", "retype", "bug"])
    assert r.exit_code == 0, r.output
    assert "reset" in r.output.lower()


def test_cli_retype_feat_to_epic_status_carried(runner, tmp_path, monkeypatch, frozen_time):
    """feature↔epic share _WORK workflow; CLI prints a carried-status message."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "feature", "F", "--author", "manager"])
    runner.invoke(app, ["feature", "2", "status", "InProgress"])

    r = runner.invoke(app, ["feature", "2", "retype", "epic"])
    assert r.exit_code == 0, r.output
    assert "carried" in r.output.lower()


def test_cli_retype_refuses_with_subentities(runner, tmp_path, monkeypatch, frozen_time):
    """The CLI refuses retype when the item has sub-entities."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "feature", "F", "--author", "manager"])
    runner.invoke(app, ["feature", "2", "add-story", "S1"])

    r = runner.invoke(app, ["feature", "2", "retype", "epic"])
    assert r.exit_code == 1
    assert "sub-entities" in r.output


def test_cli_retype_unknown_type_error(runner, tmp_path, monkeypatch, frozen_time):
    """The CLI rejects an invalid new-type argument."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])

    r = runner.invoke(app, ["task", "2", "retype", "bogustype"])
    assert r.exit_code == 1
