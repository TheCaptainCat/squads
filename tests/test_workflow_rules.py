import pytest

from squads import _workflow as workflow
from squads._errors import SquadsError
from squads._models._enums import ItemType

pytestmark = pytest.mark.anyio

# --------------------------------------------------------------------------- parent rules (unit)


def test_parent_allowed_rules():
    assert workflow.parent_allowed(ItemType.TASK, ItemType.FEATURE)
    assert not workflow.parent_allowed(ItemType.TASK, ItemType.EPIC)
    assert not workflow.parent_allowed(ItemType.TASK, ItemType.BUG)
    assert workflow.parent_allowed(ItemType.FEATURE, ItemType.EPIC)
    assert not workflow.parent_allowed(ItemType.FEATURE, ItemType.TASK)
    # unconstrained types accept anything
    assert workflow.parent_allowed(ItemType.BUG, ItemType.EPIC)


def test_parent_hint_mentions_refs_for_task():
    assert "feature" in workflow.parent_hint(ItemType.TASK)
    assert "sq ref add" in workflow.parent_hint(ItemType.TASK)


# --------------------------------------------------------------------------- create / link


async def test_task_parent_must_be_feature(svc):
    epic = (await svc.create(ItemType.EPIC, "e")).item
    feat = (await svc.create(ItemType.FEATURE, "f", parent=epic.id)).item  # feature→epic OK
    # task under a feature is fine
    task = (await svc.create(ItemType.TASK, "t", parent=feat.id)).item
    assert task.parent == feat.id
    # task under an epic is rejected at create time
    with pytest.raises(SquadsError, match="must be of type feature"):
        await svc.create(ItemType.TASK, "bad", parent=epic.id)
    # ...and at link time
    standalone = (await svc.create(ItemType.TASK, "tech")).item
    with pytest.raises(SquadsError, match="must be of type feature"):
        await svc.link(standalone.id, epic.id)


async def test_feature_parent_must_be_epic(svc):
    feat = (await svc.create(ItemType.FEATURE, "f")).item
    with pytest.raises(SquadsError, match="must be of type epic"):
        await svc.create(ItemType.FEATURE, "f2", parent=feat.id)


async def test_task_links_bug_via_ref(svc):
    bug = (await svc.create(ItemType.BUG, "npe")).item
    task = (await svc.create(ItemType.TASK, "fix it")).item  # no feature parent (technical/bugfix)
    await svc.add_ref(task.id, bug.id, kind="fixes")
    assert await svc.refs_out(task.id) == [(bug.id, "fixes")]


# --------------------------------------------------------------------------- subtask → US


async def test_subtask_story_records_and_validates(svc):
    feat = (await svc.create(ItemType.FEATURE, "Login")).item
    await svc.add_story(feat.id, "reset password")  # US1
    task = (await svc.create(ItemType.TASK, "Tokens", parent=feat.id)).item
    res = await svc.add_subtask(task.id, "Validate expiry", story="US1")
    text = svc.paths.abspath((await svc.get(task.id)).path).read_text(encoding="utf-8")
    assert "story: US1" in text  # the US mapping lives in the sq-owned :meta region
    (sub,) = await svc.list_subtasks(task.id)
    assert sub.local_id == res.local_id
    assert sub.title == "Validate expiry" and sub.story == "US1" and sub.status == "Todo"


async def test_subtask_story_unknown_us_rejected(svc):
    feat = (await svc.create(ItemType.FEATURE, "Login")).item
    task = (await svc.create(ItemType.TASK, "Tokens", parent=feat.id)).item
    with pytest.raises(SquadsError, match="US9 not found"):
        await svc.add_subtask(task.id, "x", story="US9")


async def test_subtask_story_requires_feature_parent(svc):
    task = (await svc.create(ItemType.TASK, "tech")).item  # no parent
    with pytest.raises(SquadsError, match="no feature parent"):
        await svc.add_subtask(task.id, "x", story="US1")


# --------------------------------------------------------------------------- check


async def test_check_flags_bad_task_parent(svc):
    epic = (await svc.create(ItemType.EPIC, "e")).item
    task = (await svc.create(ItemType.TASK, "t")).item
    # corrupt the index to point a task at an epic
    async with svc.store.transaction() as db:
        db.items[task.sequence_id].parent = epic.id
    issues = await svc.check()
    assert any(i.item == task.id and "must be of type feature" in i.message for i in issues)


async def test_check_flags_dangling_subtask_story(svc):
    feat = (await svc.create(ItemType.FEATURE, "Login")).item
    await svc.add_story(feat.id, "reset")  # US1
    task = (await svc.create(ItemType.TASK, "Tokens", parent=feat.id)).item
    await svc.add_subtask(task.id, "ok", story="US1")
    # now hand-edit the frontmatter to reference a non-existent US, then resync the index from it
    path = svc.paths.abspath((await svc.get(task.id)).path)
    text = path.read_text(encoding="utf-8").replace("story: US1", "story: US7")
    path.write_text(text, encoding="utf-8")
    await svc.repair()
    issues = await svc.check()
    assert any(i.item == task.id and "US7" in i.message for i in issues)
