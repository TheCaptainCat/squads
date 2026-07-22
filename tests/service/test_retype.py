"""``Service.retype()``: the file-move/frontmatter/index side of reclassifying an item in
place, plus its refusal surface. The pure id/status math it relies on is proven once at the
unit layer (tests/unit/test_identity.py).
"""

import pytest

from squads._errors import SquadsError
from squads._itemfile import read_frontmatter
from squads._sections import get_section

pytestmark = pytest.mark.anyio


async def test_retype_moves_the_file_updates_frontmatter_and_index(svc):
    task = (await svc.create("task", "Fix crash")).item
    seq = task.sequence_id

    res = await svc.retype(task.id, "bug")

    assert res.item.sequence_id == seq
    assert res.item.id.startswith("BUG-")
    new_path = svc.paths.abspath(res.item.path)
    assert new_path.exists() and "bugs" in str(new_path)

    fm = read_frontmatter(new_path)
    assert fm["type"] == "bug"
    assert fm["id"] == res.item.id
    assert fm["sequence_id"] == seq

    db = await svc.store.load()
    indexed = db.items[seq]
    assert indexed.type == "bug"
    assert indexed.id == res.item.id


async def test_retype_preserves_body_bytes_verbatim(svc):
    task = (await svc.create("task", "task")).item
    body_text = "## Details\n\nSpecial chars: ← → ✓"
    await svc.set_body(task.id, body_text)

    res = await svc.retype(task.id, "bug")

    text = svc.paths.abspath(res.item.path).read_text(encoding="utf-8")
    body = get_section(text, "body")
    assert body is not None and body_text in body


async def test_retype_appends_a_system_comment_naming_both_ids(svc):
    task = (await svc.create("task", "task")).item
    old_id = task.id
    res = await svc.retype(task.id, "bug")

    disc = get_section(svc.paths.abspath(res.item.path).read_text(encoding="utf-8"), "discussion")
    assert disc is not None and old_id in disc and res.item.id in disc


async def test_retype_rewrites_incoming_refs_children_and_prose_mentions(svc):
    task = (await svc.create("task", "t")).item
    bug = (await svc.create("bug", "b")).item
    await svc.add_ref(bug.id, task.id, kind="blocks")
    child = (await svc.create("bug", "child", parent=task.id)).item
    other = (await svc.create("review", "r")).item
    await svc.set_body(other.id, f"See {task.id} for context.")

    old_id = task.id
    res = await svc.retype(task.id, "feature")

    updated_bug = await svc.get(bug.id)
    assert f"{res.item.id}:blocks" in updated_bug.refs
    assert old_id not in updated_bug.refs[0]

    updated_child = await svc.get(child.id)
    assert updated_child.parent == res.item.id

    body = await svc.read_body(other.id)
    assert old_id not in body and res.item.id in body


async def test_retype_to_a_container_bearing_type_scaffolds_an_empty_container(svc):
    task = (await svc.create("task", "t")).item
    res = await svc.retype(task.id, "feature")
    text = svc.paths.abspath(res.item.path).read_text(encoding="utf-8")
    assert "<!-- sq:stories -->" in text and "<!-- sq:stories:end -->" in text


async def test_retype_leaves_check_and_repair_clean(svc):
    task = (await svc.create("task", "t")).item
    await svc.retype(task.id, "bug")

    issues = await svc.check()
    assert not [i for i in issues if i.level == "error"]

    result = await svc.repair()
    assert result.missing_ids == []


# --------------------------------------------------------------------------- refusals


async def test_retype_refuses_a_roster_type_as_source(svc):
    with pytest.raises(SquadsError, match="only work/records items can be retyped"):
        await svc.retype("ROLE-000001", "task")


@pytest.mark.parametrize("roster_type", ["role", "skill", "operator"])
async def test_retype_refuses_a_roster_type_as_target(svc, roster_type):
    task = (await svc.create("task", "t")).item
    with pytest.raises(SquadsError, match="target must be a work or records type"):
        await svc.retype(task.id, roster_type)


async def test_retype_refuses_a_no_op_retype_to_the_same_type(svc):
    task = (await svc.create("task", "t")).item
    with pytest.raises(SquadsError, match="already of type task"):
        await svc.retype(task.id, "task")


async def test_retype_refuses_an_item_that_still_has_sub_entities(svc):
    feat = (await svc.create("feature", "f")).item
    await svc.add_story(feat.id, "story 1")
    with pytest.raises(SquadsError, match="sub-entities"):
        await svc.retype(feat.id, "epic")


async def test_retype_refuses_when_the_existing_parent_would_become_invalid(svc):
    feat = (await svc.create("feature", "f")).item
    task = (await svc.create("task", "t", parent=feat.id)).item
    # task's parent (a feature) would be invalid for a feature-typed item (needs an epic parent)
    with pytest.raises(SquadsError, match="cannot retype"):
        await svc.retype(task.id, "feature")


async def test_retype_refuses_when_a_child_would_become_invalid(svc):
    feat = (await svc.create("feature", "f")).item
    await svc.create("task", "t", parent=feat.id)  # requires a feature parent
    with pytest.raises(SquadsError, match="child item"):
        await svc.retype(feat.id, "bug")


# --------------------------------------------------------------------------- work <-> records


async def test_retype_from_a_work_type_to_a_records_type_succeeds_when_unparented(svc):
    task = (await svc.create("task", "t")).item

    res = await svc.retype(task.id, "decision")

    assert res.item.id.startswith("ADR-")
    new_path = svc.paths.abspath(res.item.path)
    assert new_path.exists() and "adrs" in str(new_path)


async def test_retype_from_a_records_type_to_a_work_type_succeeds_when_unparented(svc):
    decision = (await svc.create("decision", "d")).item

    res = await svc.retype(decision.id, "task")

    assert res.item.id.startswith("TASK-")
    new_path = svc.paths.abspath(res.item.path)
    assert new_path.exists() and "tasks" in str(new_path)


async def test_retype_refuses_a_parented_item_into_a_no_parent_records_type(svc):
    feat = (await svc.create("feature", "f")).item
    task = (await svc.create("task", "t", parent=feat.id)).item

    with pytest.raises(SquadsError, match="takes no parent"):
        await svc.retype(task.id, "decision")
