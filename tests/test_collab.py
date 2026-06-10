import pytest

from squads import _sections as sections
from squads._errors import SquadsError
from squads._itemfile import read_frontmatter
from squads._models._enums import ItemType, Severity, Status

# --------------------------------------------------------------------------- comments


def test_comment_appends_under_anchor_and_resolves_author(svc):
    task = svc.create(ItemType.TASK, "t").item
    svc.comment(task.id, ["first point", "second point"], as_slug="manager")
    text = svc.paths.abspath(svc.get(task.id).path).read_text(encoding="utf-8")
    disc = sections.get_section(text, "discussion")
    assert disc is not None
    assert "Catherine Manager:" in disc  # slug → full name
    assert "- first point" in disc
    assert "- second point" in disc


def test_comment_preserves_body_and_markers(svc):
    task = svc.create(ItemType.TASK, "t").item
    path = svc.paths.abspath(task.path)
    # simulate an agent writing real body prose
    original = path.read_text(encoding="utf-8").replace(
        "_TODO: describe this task._", "Real authored body."
    )
    path.write_text(original, encoding="utf-8")
    svc.comment(task.id, ["a note"], as_slug="operator")
    text = path.read_text(encoding="utf-8")
    assert "Real authored body." in text  # untouched
    assert text.count("<!-- sq:body -->") == 1
    body = sections.get_section(text, "body")
    assert body is not None
    assert body.strip() == "## Description\n\nReal authored body."


def test_locked_edit_body_and_comment_coexist_and_bump(svc):
    """Body + discussion are written through the locked edit path: both persist, updated_at bumps,
    and the result survives an index rebuild (frontmatter is the source of truth)."""
    task = svc.create(ItemType.TASK, "t").item
    before = svc.get(task.id).updated_at
    svc.set_body(task.id, "Authored body prose.")
    svc.comment(task.id, ["a handoff note"], as_slug="manager")
    path = svc.paths.abspath(svc.get(task.id).path)
    text = path.read_text(encoding="utf-8")
    # both regions present, body (set_body replaces the region) untouched by the comment
    assert (sections.get_section(text, "body") or "").strip() == "Authored body prose."
    assert "a handoff note" in (sections.get_section(text, "discussion") or "")
    assert "updated_at" in read_frontmatter(path)  # bump written to the .md, not just the index
    # everything is reconstructable from frontmatter alone, including the bumped updated_at
    svc.repair()
    assert svc.get(task.id).updated_at >= before
    after = svc.paths.abspath(svc.get(task.id).path).read_text(encoding="utf-8")
    assert "Authored body prose." in after and "a handoff note" in after


def test_comment_requires_existing_section(svc):
    epic = svc.create(ItemType.EPIC, "e").item
    with pytest.raises(SquadsError):
        svc.comment(epic.id, ["x"], story="US1")  # epic has no story US1


def test_comment_targets_a_finding(svc):
    rev = svc.create(ItemType.REVIEW, "r").item
    svc.add_finding(rev.id, "Null deref")  # F1
    svc.comment(rev.id, ["please fix"], as_slug="reviewer", finding="F1")
    text = svc.paths.abspath(svc.get(rev.id).path).read_text(encoding="utf-8")
    disc = sections.get_section(text, "finding:F1:discussion")
    assert disc is not None and "please fix" in disc
    # the review's top-level discussion stays untouched
    top = sections.get_section(text, "discussion")
    assert top is not None and "please fix" not in top


def test_comment_rejects_multiple_targets(svc):
    feat = svc.create(ItemType.FEATURE, "f").item
    with pytest.raises(SquadsError, match="only one"):
        svc.comment(feat.id, ["x"], story="US1", subtask="ST1")


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
    text = svc.paths.abspath(svc.get(feat.id).path).read_text(encoding="utf-8")
    assert sections.has_section(text, "story:US1:discussion")
    # comment targets the nested discussion only
    svc.comment(feat.id, ["scope it"], as_slug="product-owner", story="US1")
    text = svc.paths.abspath(svc.get(feat.id).path).read_text(encoding="utf-8")
    us1 = sections.get_section(text, "story:US1:discussion")
    us2 = sections.get_section(text, "story:US2:discussion")
    assert us1 is not None and us2 is not None
    assert "scope it" in us1
    assert us2.strip() == ""
    assert [b.local_id for b in svc.list_stories(feat.id)] == ["US1", "US2"]


def test_story_body_set_via_sq_and_preserved_by_comment(svc):
    feat = svc.create(ItemType.FEATURE, "Login").item
    svc.add_story(feat.id)  # no title → empty heading, placeholder body
    # the body is set through sq (no manual file editing), multiline prose + bullets
    body = "As an admin, I want resets.\n\nAcceptance:\n- link expires in 30m\n- audit logged"
    svc.set_story_body(feat.id, "US1", body)
    detail = svc.get_story(feat.id, "US1")
    assert detail.body == body
    # commenting only touches the discussion, never the body
    svc.comment(feat.id, ["go"], as_slug="operator", story="US1")
    after = svc.get_story(feat.id, "US1")
    assert after.body == body
    assert "go" in after.discussion
    # title is explicit frontmatter state; an untitled story stays untitled (body is separate prose)
    (story,) = svc.list_stories(feat.id)
    assert (story.local_id, story.title) == ("US1", "")


def test_subtask_body_set_append_and_reject_markers(svc):
    task = svc.create(ItemType.TASK, "t").item
    svc.add_subtask(task.id, "Validate")
    svc.set_subtask_body(task.id, "ST1", "First paragraph.\n\nSecond.")
    assert svc.get_subtask(task.id, "ST1").body == "First paragraph.\n\nSecond."
    # append adds a paragraph after the existing body
    svc.set_subtask_body(task.id, "ST1", "Third.", append=True)
    assert svc.get_subtask(task.id, "ST1").body.endswith("Second.\n\nThird.")
    # a body carrying an sq marker is rejected
    with pytest.raises(SquadsError, match="marker"):
        svc.set_subtask_body(task.id, "ST1", "oops <!-- sq:body:end --> oops")


def test_append_overwrites_placeholder(svc):
    task = svc.create(ItemType.TASK, "t").item
    svc.add_subtask(task.id, "Validate")  # body is still the italic placeholder
    svc.set_subtask_body(task.id, "ST1", "Real content.", append=True)
    assert svc.get_subtask(task.id, "ST1").body == "Real content."  # replaced, not appended after


def _head(svc, item_id, tag):
    text = svc.paths.abspath(svc.get(item_id).path).read_text(encoding="utf-8")
    return sections.get_section(text, tag) or ""


def test_assignee_full_name_rendered_under_heading(svc):
    svc.add_dev("python", name="Grace Hopper")  # python-dev
    svc.add_dev("rust", name="Alan Turing")  # rust-dev
    task = svc.create(ItemType.TASK, "t").item

    # set at add time: the :head shows the full name; the slug is the frontmatter state
    svc.add_subtask(task.id, "Validate", assignee="python-dev")
    head = _head(svc, task.id, "subtask:ST1:head")
    assert "**Assignee:** Grace Hopper" in head
    assert svc.list_subtasks(task.id)[0].assignee == "python-dev"  # frontmatter keeps the slug
    # the head sits between the heading and the block's body region
    text = svc.paths.abspath(svc.get(task.id).path).read_text(encoding="utf-8")
    assert text.index("### ST1") < text.index("subtask:ST1:head") < text.index("subtask:ST1:body")

    # reassign updates the rendered name
    svc.set_subtask_assignee(task.id, "ST1", "rust-dev")
    assert "**Assignee:** Alan Turing" in _head(svc, task.id, "subtask:ST1:head")

    # --clear drops the assignee line; the status badge stays
    svc.set_subtask_assignee(task.id, "ST1", None)
    head = _head(svc, task.id, "subtask:ST1:head")
    assert "**Assignee:**" not in head and "**Status:**" in head
    assert svc.list_subtasks(task.id)[0].assignee is None


def test_head_shows_status_severity_and_story(svc):
    svc.add_dev("python", name="Grace Hopper")
    feat = svc.create(ItemType.FEATURE, "Login").item
    svc.add_story(feat.id, "As a user, I want to reset my password")  # US1
    task = svc.create(ItemType.TASK, "Auth", parent=feat.id).item

    # a fresh subtask already shows its status badge (no assignee line yet)
    svc.add_subtask(task.id, "Validate", story="US1")
    head = _head(svc, task.id, "subtask:ST1:head")
    assert "**Status:** ⚪ Todo" in head and "**Assignee:**" not in head
    # the story link resolves to "USn — title"
    assert "**Implements:** US1 — As a user, I want to reset my password" in head

    # status transitions re-render the badge
    svc.set_subtask_status(task.id, "ST1", Status.IN_PROGRESS)
    assert "**Status:** 🟡 In Progress" in _head(svc, task.id, "subtask:ST1:head")

    # findings show a severity badge
    rev = svc.create(ItemType.REVIEW, "r").item
    svc.add_finding(rev.id, "Null deref", severity=Severity.HIGH)
    assert "**Severity:** 🟠 High" in _head(svc, rev.id, "finding:F1:head")


def test_body_set_at_add_time(svc):
    feat = svc.create(ItemType.FEATURE, "f").item
    svc.add_story(feat.id, body="As an admin, I want resets.\n\nAcceptance: link expires in 30m")
    (story,) = svc.list_stories(feat.id)
    assert story.title == ""  # title is explicit; the body is independent prose
    assert svc.get_story(feat.id, story.local_id).body.startswith("As an admin")


def test_update_subtask_title_rerenders_heading_and_summary(svc):
    task = svc.create(ItemType.TASK, "t").item
    svc.add_subtask(task.id, "Old name", body="prose body")
    svc.set_subtask_status(task.id, "ST1", Status.IN_PROGRESS)

    svc.update_subtask(task.id, "ST1", title="New name")

    # frontmatter title updated, other state untouched
    sub = svc.list_subtasks(task.id)[0]
    assert (sub.title, sub.status) == ("New name", Status.IN_PROGRESS)
    text = svc.paths.abspath(svc.get(task.id).path).read_text(encoding="utf-8")
    # the body heading and the parent summary-table row both re-render; the body prose is preserved
    assert "### ST1 — New name" in text and "Old name" not in text
    assert "| ST1 | InProgress |  | New name |" in text
    assert svc.get_subtask(task.id, "ST1").body == "prose body"


def test_update_finding_severity(svc):
    rev = svc.create(ItemType.REVIEW, "r").item
    svc.add_finding(rev.id, "Null deref", severity=Severity.MEDIUM)

    svc.update_finding(rev.id, "F1", severity=Severity.HIGH)

    assert svc.list_findings(rev.id)[0].severity is Severity.HIGH
    text = svc.paths.abspath(svc.get(rev.id).path).read_text(encoding="utf-8")
    assert "severity: high" in text  # frontmatter state
    assert "**Severity:** 🟠 High" in _head(svc, rev.id, "finding:F1:head")  # head badge
    assert "🟠 high" in text  # summary cell


def test_update_subtask_story_remap_validate_and_clear(svc):
    feat = svc.create(ItemType.FEATURE, "Login").item
    svc.add_story(feat.id, "Reset password")  # US1
    svc.add_story(feat.id, "Lockout policy")  # US2
    task = svc.create(ItemType.TASK, "Auth", parent=feat.id).item
    svc.add_subtask(task.id, "Validate", story="US1")

    # remap to a different (existing) story → head "Implements" + summary Story column update
    svc.update_subtask(task.id, "ST1", story="US2")
    assert svc.list_subtasks(task.id)[0].story == "US2"
    assert "**Implements:** US2 — Lockout policy" in _head(svc, task.id, "subtask:ST1:head")

    # an unknown story is rejected
    with pytest.raises(SquadsError, match="US9"):
        svc.update_subtask(task.id, "ST1", story="US9")

    # --no-story clears the mapping
    svc.update_subtask(task.id, "ST1", clear_story=True)
    assert svc.list_subtasks(task.id)[0].story is None
    assert "**Implements:**" not in _head(svc, task.id, "subtask:ST1:head")


def test_update_applies_several_fields_and_validates_status(svc):
    svc.add_dev("python", name="Grace Hopper")  # python-dev
    task = svc.create(ItemType.TASK, "t").item
    svc.add_subtask(task.id, "Old")

    # one call sets title + assignee + status (a valid transition)
    svc.update_subtask(
        task.id, "ST1", title="New", assignee="python-dev", status=Status.IN_PROGRESS
    )
    sub = svc.list_subtasks(task.id)[0]
    assert (sub.title, sub.assignee, sub.status) == ("New", "python-dev", Status.IN_PROGRESS)

    # an invalid transition is rejected without --force, accepted with it
    with pytest.raises(SquadsError, match="cannot move"):
        svc.update_subtask(task.id, "ST1", status=Status.TODO)
    svc.update_subtask(task.id, "ST1", status=Status.TODO, force=True)
    assert svc.list_subtasks(task.id)[0].status is Status.TODO

    # an unregistered assignee is rejected
    with pytest.raises(SquadsError, match="not a registered agent"):
        svc.update_subtask(task.id, "ST1", assignee="ghost")


def test_empty_title_summary_is_blank_not_marker(svc):
    # regression: heading parse must not bleed into the next line's marker
    feat = svc.create(ItemType.FEATURE, "f").item
    svc.add_story(feat.id)
    (story,) = svc.list_stories(feat.id)
    assert (story.local_id, story.title) == ("US1", "")


def test_stories_only_on_features(svc):
    task = svc.create(ItemType.TASK, "t").item
    with pytest.raises(SquadsError):
        svc.add_story(task.id, "As a user...")


def test_subtask_done_toggle(svc):
    task = svc.create(ItemType.TASK, "t").item
    svc.add_subtask(task.id, "Validate expiry")
    svc.set_subtask_done(task.id, "ST1", done=True)
    assert svc.list_subtasks(task.id)[0].status == "Done"
    svc.set_subtask_done(task.id, "ST1", done=False)
    assert svc.list_subtasks(task.id)[0].status == "Todo"


def test_subtask_status_machine(svc):
    task = svc.create(ItemType.TASK, "t").item
    svc.add_subtask(task.id, "Validate")
    svc.set_subtask_status(task.id, "ST1", Status.IN_PROGRESS)
    assert svc.list_subtasks(task.id)[0].status == "InProgress"
    # Todo→Done is not a legal move (must pass through InProgress); already InProgress→Done is ok
    svc.set_subtask_status(task.id, "ST1", Status.DONE)
    assert svc.list_subtasks(task.id)[0].status == "Done"
    with pytest.raises(SquadsError):
        svc.set_story_status(task.id, "ST1", Status.TODO)  # wrong parent type


def test_subtask_done_unknown_id(svc):
    task = svc.create(ItemType.TASK, "t").item
    with pytest.raises(SquadsError):
        svc.set_subtask_done(task.id, "ST9")


def test_subtask_assignee_set_reassigned_and_cleared(svc):
    svc.add_dev("python")  # registers python-dev
    task = svc.create(ItemType.TASK, "t").item
    svc.add_subtask(task.id, "Wire API", assignee="python-dev")
    assert svc.list_subtasks(task.id)[0].assignee == "python-dev"
    # reassignment validates against the roster
    svc.set_subtask_assignee(task.id, "ST1", "manager")
    assert svc.list_subtasks(task.id)[0].assignee == "manager"
    with pytest.raises(SquadsError, match="not a registered agent"):
        svc.set_subtask_assignee(task.id, "ST1", "ghost")
    with pytest.raises(SquadsError, match="not a registered agent"):
        svc.add_subtask(task.id, "x", assignee="ghost")
    # reassigning preserves the status set in between
    svc.set_subtask_status(task.id, "ST1", Status.IN_PROGRESS)
    svc.set_subtask_assignee(task.id, "ST1", "python-dev")
    assert svc.list_subtasks(task.id)[0].status == "InProgress"
    # --clear path: None unassigns, and the summary table reflects it
    svc.set_subtask_assignee(task.id, "ST1", None)
    assert svc.list_subtasks(task.id)[0].assignee is None
    text = svc.paths.abspath(svc.get(task.id).path).read_text(encoding="utf-8")
    assert "| Subtask | Status | Assignee | Title | Story |" in text


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
        db.items[task.sequence_id].parent = "FEAT-999999"
    issues = svc.check()
    assert any("dangling parent" in i.message and i.item == task.id for i in issues)


def test_check_detects_broken_marker(svc):
    task = svc.create(ItemType.TASK, "t").item
    path = svc.paths.abspath(task.path)
    text = path.read_text(encoding="utf-8").replace("<!-- sq:body:end -->", "")  # remove a close
    path.write_text(text, encoding="utf-8")
    issues = svc.check()
    assert any("sq:body" in i.message for i in issues)
