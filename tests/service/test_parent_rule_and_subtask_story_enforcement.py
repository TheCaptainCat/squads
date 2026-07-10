"""The parent-type rule table (tests/unit/test_parent_allowed_rule_table.py) enforced at
create/link time and by ``sq check``; and the sibling sub-entity rule that a subtask's
``--story`` must reference a real user story on the task's own parent feature — requiring
a feature parent to be meaningful at all, and flagged by ``sq check`` when it goes dangling.
A task's ``fixes``/``addresses`` ref to a bug validates the same ref-kind rule table.
"""

import pytest

from squads._errors import SquadsError

pytestmark = pytest.mark.anyio


async def test_task_parent_must_be_a_feature_at_create_and_link_time(svc):
    epic = (await svc.create("epic", "e")).item
    feat = (await svc.create("feature", "f", parent=epic.id)).item
    task = (await svc.create("task", "t", parent=feat.id)).item
    assert task.parent == feat.id

    with pytest.raises(SquadsError, match="must be of type feature"):
        await svc.create("task", "bad", parent=epic.id)

    standalone = (await svc.create("task", "tech")).item
    with pytest.raises(SquadsError, match="must be of type feature"):
        await svc.link(standalone.id, epic.id)


async def test_feature_parent_must_be_an_epic(svc):
    feat = (await svc.create("feature", "f")).item
    with pytest.raises(SquadsError, match="must be of type epic"):
        await svc.create("feature", "f2", parent=feat.id)


async def test_check_flags_a_task_whose_parent_was_corrupted_to_a_non_feature(svc):
    epic = (await svc.create("epic", "e")).item
    task = (await svc.create("task", "t")).item
    async with svc.store.transaction() as db:
        db.items[task.sequence_id].parent = epic.id
    issues = await svc.check()
    assert any(i.item == task.id and "must be of type feature" in i.message for i in issues)


async def test_a_technical_task_links_a_bug_via_the_fixes_ref_kind(svc):
    """A task with no feature parent (a pure bugfix task) still validates the fixes/addresses
    ref-kind rule — the same rule-table mechanism, applied to ref kinds rather than parents."""
    bug = (await svc.create("bug", "npe")).item
    task = (await svc.create("task", "fix it")).item
    await svc.add_ref(task.id, bug.id, kind="fixes")
    assert await svc.refs_out(task.id) == [(bug.id, "fixes")]


async def test_subtask_story_records_and_validates_against_the_parent_features_user_stories(svc):
    feat = (await svc.create("feature", "Login")).item
    await svc.add_story(feat.id, "reset password")  # US1
    task = (await svc.create("task", "Tokens", parent=feat.id)).item
    res = await svc.add_subtask(task.id, "Validate expiry", story="US1")
    (sub,) = await svc.list_subtasks(task.id)
    assert sub.local_id == res.local_id
    assert sub.story == "US1" and sub.status == "Todo"


async def test_subtask_story_rejects_an_unknown_user_story(svc):
    feat = (await svc.create("feature", "Login")).item
    task = (await svc.create("task", "Tokens", parent=feat.id)).item
    with pytest.raises(SquadsError, match="US9 not found"):
        await svc.add_subtask(task.id, "x", story="US9")


async def test_subtask_story_requires_a_feature_parent_to_be_meaningful_at_all(svc):
    task = (await svc.create("task", "tech")).item  # no parent
    with pytest.raises(SquadsError, match="no feature parent"):
        await svc.add_subtask(task.id, "x", story="US1")


async def test_check_flags_a_subtask_story_reference_that_has_gone_dangling(svc):
    feat = (await svc.create("feature", "Login")).item
    await svc.add_story(feat.id, "reset")  # US1
    task = (await svc.create("task", "Tokens", parent=feat.id)).item
    await svc.add_subtask(task.id, "ok", story="US1")
    path = svc.paths.abspath((await svc.get(task.id)).path)
    text = path.read_text(encoding="utf-8").replace("story: US1", "story: US7")
    path.write_text(text, encoding="utf-8")
    await svc.repair()
    issues = await svc.check()
    assert any(i.item == task.id and "US7" in i.message for i in issues)
