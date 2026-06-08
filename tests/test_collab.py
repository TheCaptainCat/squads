import pytest

from squads import sections
from squads.errors import SquadsError
from squads.models import ItemType, Status

# --------------------------------------------------------------------------- comments


def test_comment_appends_under_anchor_and_resolves_author(svc):
    task = svc.create(ItemType.TASK, "t").item
    svc.comment(task.id, ["first point", "second point"], as_slug="manager")
    text = svc.paths.abspath(svc.get(task.id).path).read_text()
    disc = sections.get_section(text, "discussion")
    assert "Catherine Manager:" in disc  # slug → full name
    assert "- first point" in disc
    assert "- second point" in disc


def test_comment_preserves_body_and_markers(svc):
    task = svc.create(ItemType.TASK, "t").item
    path = svc.paths.abspath(task.path)
    # simulate an agent writing real body prose
    original = path.read_text().replace("_TODO: describe this task._", "Real authored body.")
    path.write_text(original)
    svc.comment(task.id, ["a note"], as_slug="operator")
    text = path.read_text()
    assert "Real authored body." in text  # untouched
    assert text.count("<!-- sq:body -->") == 1
    assert sections.get_section(text, "body").strip() == "## Description\n\nReal authored body."


def test_comment_requires_existing_section(svc):
    epic = svc.create(ItemType.EPIC, "e").item
    with pytest.raises(SquadsError):
        svc.comment(epic.id, ["x"], story="US1")  # epic has no story US1


def test_operator_author(svc):
    assert svc.author("operator") == "Operator"
    assert svc.author("architect") == "Robert Architect"
    assert svc.author("ghost") == "ghost"  # unknown slug → itself


# --------------------------------------------------------------------------- stories / subtasks


def test_story_scaffold_and_nested_discussion(svc):
    feat = svc.create(ItemType.FEATURE, "Login").item
    res = svc.add_story(feat.id, "Password reset")
    assert res.local_id == "US1"
    # the scaffold returns a writable, free-form body region for the agent
    assert res.body_tag == "story:US1:body"
    assert res.start_line and res.end_line and res.end_line > res.start_line
    assert svc.add_story(feat.id).local_id == "US2"  # title is optional
    text = svc.paths.abspath(svc.get(feat.id).path).read_text()
    assert sections.has_section(text, "story:US1:discussion")
    # comment targets the nested discussion only
    svc.comment(feat.id, ["scope it"], as_slug="product-owner", story="US1")
    assert "scope it" in sections.get_section(
        text := svc.paths.abspath(svc.get(feat.id).path).read_text(), "story:US1:discussion"
    )
    assert sections.get_section(text, "story:US2:discussion").strip() == ""
    assert [s[0] for s in svc.list_stories(feat.id)] == ["US1", "US2"]


def test_story_body_is_freeform_and_agent_owned(svc):
    feat = svc.create(ItemType.FEATURE, "Login").item
    res = svc.add_story(feat.id)  # no title → empty heading, placeholder body
    path = svc.paths.abspath(svc.get(feat.id).path)
    # an agent replaces the placeholder with multiline prose + bullets
    body = "As an admin, I want resets.\n\nAcceptance:\n- link expires in 30m\n- audit logged"
    text = sections.replace_section(path.read_text(), res.body_tag, body)
    path.write_text(text)
    # sq leaves the body alone; commenting only touches the discussion
    svc.comment(feat.id, ["go"], as_slug="operator", story="US1")
    after = path.read_text()
    assert sections.get_section(after, res.body_tag).strip() == body
    # list summary derives from the free-form body when there is no title
    assert svc.list_stories(feat.id) == [("US1", "As an admin, I want resets.")]


def test_empty_title_summary_is_blank_not_marker(svc):
    # regression: heading parse must not bleed into the next line's marker
    feat = svc.create(ItemType.FEATURE, "f").item
    svc.add_story(feat.id)
    assert svc.list_stories(feat.id) == [("US1", "")]


def test_stories_only_on_features(svc):
    task = svc.create(ItemType.TASK, "t").item
    with pytest.raises(SquadsError):
        svc.add_story(task.id, "As a user...")


def test_subtask_done_toggle(svc):
    task = svc.create(ItemType.TASK, "t").item
    svc.add_subtask(task.id, "Validate expiry")
    svc.set_subtask_done(task.id, "ST1", done=True)
    assert svc.list_subtasks(task.id) == [("ST1", "[x] Validate expiry")]
    svc.set_subtask_done(task.id, "ST1", done=False)
    assert svc.list_subtasks(task.id) == [("ST1", "[ ] Validate expiry")]


def test_subtask_done_unknown_id(svc):
    task = svc.create(ItemType.TASK, "t").item
    with pytest.raises(SquadsError):
        svc.set_subtask_done(task.id, "ST9")


# --------------------------------------------------------------------------- inbox


def test_inbox_finds_open_mentions_only(svc):
    t1 = svc.create(ItemType.TASK, "open one").item
    t2 = svc.create(ItemType.TASK, "done one").item
    svc.comment(t1.id, ["@qa please verify"], as_slug="architect")
    svc.comment(t2.id, ["@qa check this too"], as_slug="architect")
    svc.set_status(t2.id, Status.IN_PROGRESS)
    svc.set_status(t2.id, Status.DONE)  # terminal → excluded from inbox
    hits = svc.inbox("qa")
    ids = {it.id for it, _ in hits}
    assert t1.id in ids
    assert t2.id not in ids
    # mention lines are surfaced
    lines = next(lns for it, lns in hits if it.id == t1.id)
    assert any("@qa" in ln for ln in lines)


def test_inbox_accepts_at_prefix(svc):
    t = svc.create(ItemType.TASK, "t").item
    svc.comment(t.id, ["@reviewer take a look"], as_slug="operator")
    assert {i.id for i, _ in svc.inbox("@reviewer")} == {t.id}


# --------------------------------------------------------------------------- check


def test_check_clean_after_init(svc):
    svc.create(ItemType.FEATURE, "f")
    assert svc.check() == []


def test_check_detects_dangling_parent(svc):
    task = svc.create(ItemType.TASK, "t").item
    # corrupt the index directly: point at a non-existent parent
    with svc.store.transaction() as db:
        db.items[task.id].parent = "FEAT-999999"
    issues = svc.check()
    assert any("dangling parent" in i.message and i.item == task.id for i in issues)


def test_check_detects_broken_marker(svc):
    task = svc.create(ItemType.TASK, "t").item
    path = svc.paths.abspath(task.path)
    path.write_text(path.read_text().replace("<!-- sq:body:end -->", ""))  # remove a close
    issues = svc.check()
    assert any("sq:body" in i.message for i in issues)
