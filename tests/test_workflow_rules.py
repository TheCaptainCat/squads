import pytest

from squads import _workflow as workflow
from squads._errors import SquadsError
from squads._models._enums import ItemType

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


def test_task_parent_must_be_feature(svc):
    epic = svc.create(ItemType.EPIC, "e").item
    feat = svc.create(ItemType.FEATURE, "f", parent=epic.id).item  # feature→epic OK
    # task under a feature is fine
    task = svc.create(ItemType.TASK, "t", parent=feat.id).item
    assert task.parent == feat.id
    # task under an epic is rejected at create time
    with pytest.raises(SquadsError, match="must be of type feature"):
        svc.create(ItemType.TASK, "bad", parent=epic.id)
    # ...and at link time
    standalone = svc.create(ItemType.TASK, "tech").item
    with pytest.raises(SquadsError, match="must be of type feature"):
        svc.link(standalone.id, epic.id)


def test_feature_parent_must_be_epic(svc):
    feat = svc.create(ItemType.FEATURE, "f").item
    with pytest.raises(SquadsError, match="must be of type epic"):
        svc.create(ItemType.FEATURE, "f2", parent=feat.id)


def test_task_links_bug_via_ref(svc):
    bug = svc.create(ItemType.BUG, "npe").item
    task = svc.create(ItemType.TASK, "fix it").item  # no feature parent (technical/bugfix)
    svc.add_ref(task.id, bug.id, kind="fixes")
    assert svc.refs_out(task.id) == [(bug.id, "fixes")]


# --------------------------------------------------------------------------- subtask → US


def test_subtask_story_records_and_validates(svc):
    feat = svc.create(ItemType.FEATURE, "Login").item
    svc.add_story(feat.id, "reset password")  # US1
    task = svc.create(ItemType.TASK, "Tokens", parent=feat.id).item
    res = svc.add_subtask(task.id, "Validate expiry", story="US1")
    text = svc.paths.abspath(svc.get(task.id).path).read_text(encoding="utf-8")
    assert "(→ US1)" in text
    assert svc.list_subtasks(task.id) == [(res.local_id, "[ ] Validate expiry  (→ US1)")]


def test_subtask_story_unknown_us_rejected(svc):
    feat = svc.create(ItemType.FEATURE, "Login").item
    task = svc.create(ItemType.TASK, "Tokens", parent=feat.id).item
    with pytest.raises(SquadsError, match="US9 not found"):
        svc.add_subtask(task.id, "x", story="US9")


def test_subtask_story_requires_feature_parent(svc):
    task = svc.create(ItemType.TASK, "tech").item  # no parent
    with pytest.raises(SquadsError, match="no feature parent"):
        svc.add_subtask(task.id, "x", story="US1")


# --------------------------------------------------------------------------- check


def test_check_flags_bad_task_parent(svc):
    epic = svc.create(ItemType.EPIC, "e").item
    task = svc.create(ItemType.TASK, "t").item
    # corrupt the index to point a task at an epic
    with svc.store.transaction() as db:
        db.items[task.id].parent = epic.id
    issues = svc.check()
    assert any(i.item == task.id and "must be of type feature" in i.message for i in issues)


def test_check_flags_dangling_subtask_story(svc):
    feat = svc.create(ItemType.FEATURE, "Login").item
    svc.add_story(feat.id, "reset")  # US1
    task = svc.create(ItemType.TASK, "Tokens", parent=feat.id).item
    svc.add_subtask(task.id, "ok", story="US1")
    # now hand-edit the file to reference a non-existent US
    path = svc.paths.abspath(svc.get(task.id).path)
    text = path.read_text(encoding="utf-8").replace("(→ US1)", "(→ US7)")
    path.write_text(text, encoding="utf-8")
    issues = svc.check()
    assert any(i.item == task.id and "US7" in i.message for i in issues)
