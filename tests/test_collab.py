import pytest

from squads import _sections as sections
from squads._errors import SquadsError
from squads._itemfile import read_frontmatter
from squads._models._enums import Severity, Status

pytestmark = pytest.mark.anyio

# --------------------------------------------------------------------------- comments


async def test_comment_appends_under_anchor_and_resolves_author(svc):
    task = (await svc.create("task", "t")).item
    await svc.comment(task.id, ["first point", "second point"], as_slug="manager")
    text = svc.paths.abspath((await svc.get(task.id)).path).read_text(encoding="utf-8")
    disc = sections.get_section(text, "discussion")
    assert disc is not None
    assert "Catherine Manager:" in disc  # slug → full name
    assert "- first point" in disc
    assert "- second point" in disc


async def test_comment_preserves_body_and_markers(svc):
    task = (await svc.create("task", "t")).item
    path = svc.paths.abspath(task.path)
    # simulate an agent writing real body prose
    original = path.read_text(encoding="utf-8").replace(
        "_TODO: describe this task._", "Real authored body."
    )
    path.write_text(original, encoding="utf-8")
    await svc.comment(task.id, ["a note"], as_slug="operator")
    text = path.read_text(encoding="utf-8")
    assert "Real authored body." in text  # untouched
    assert text.count("<!-- sq:body -->") == 1
    body = sections.get_section(text, "body")
    assert body is not None
    assert body.strip() == "## Description\n\nReal authored body."


async def test_locked_edit_body_and_comment_coexist_and_bump(svc):
    """Body + discussion are written through the locked edit path: both persist, updated_at bumps,
    and the result survives an index rebuild (frontmatter is the source of truth)."""
    task = (await svc.create("task", "t")).item
    before = (await svc.get(task.id)).updated_at
    await svc.set_body(task.id, "Authored body prose.")
    await svc.comment(task.id, ["a handoff note"], as_slug="manager")
    path = svc.paths.abspath((await svc.get(task.id)).path)
    text = path.read_text(encoding="utf-8")
    # both regions present, body (set_body replaces the region) untouched by the comment
    assert (sections.get_section(text, "body") or "").strip() == "Authored body prose."
    assert "a handoff note" in (sections.get_section(text, "discussion") or "")
    assert "updated_at" in read_frontmatter(path)  # bump written to the .md, not just the index
    # everything is reconstructable from frontmatter alone, including the bumped updated_at
    await svc.repair()
    assert (await svc.get(task.id)).updated_at >= before
    after = svc.paths.abspath((await svc.get(task.id)).path).read_text(encoding="utf-8")
    assert "Authored body prose." in after and "a handoff note" in after


async def test_comment_requires_existing_section(svc):
    epic = (await svc.create("epic", "e")).item
    with pytest.raises(SquadsError):
        await svc.comment(epic.id, ["x"], story="US1")  # epic has no story US1


async def test_comment_targets_a_finding(svc):
    rev = (await svc.create("review", "r")).item
    await svc.add_finding(rev.id, "Null deref")  # F1
    await svc.comment(rev.id, ["please fix"], as_slug="reviewer", finding="F1")
    text = svc.paths.abspath((await svc.get(rev.id)).path).read_text(encoding="utf-8")
    disc = sections.get_section(text, "finding:F1:discussion")
    assert disc is not None and "please fix" in disc
    # the review's top-level discussion stays untouched
    top = sections.get_section(text, "discussion")
    assert top is not None and "please fix" not in top


async def test_comment_rejects_multiple_targets(svc):
    feat = (await svc.create("feature", "f")).item
    with pytest.raises(SquadsError, match="only one"):
        await svc.comment(feat.id, ["x"], story="US1", subtask="ST1")


async def test_operator_author(svc):
    assert await svc.author("operator") == "Operator"
    assert await svc.author("architect") == "Robert Architect"
    assert await svc.author("ghost") == "ghost"  # unknown slug → itself


# --------------------------------------------------------------------------- stories / subtasks


async def test_story_scaffold_and_nested_discussion(svc):
    feat = (await svc.create("feature", "Login")).item
    res = await svc.add_story(feat.id, "Password reset")
    assert res.local_id == "US1"
    # the scaffold returns a writable, free-form body region for the agent
    assert res.body_tag == "story:US1:body"
    assert res.start_line and res.end_line and res.end_line > res.start_line
    assert (await svc.add_story(feat.id)).local_id == "US2"  # title is optional
    text = svc.paths.abspath((await svc.get(feat.id)).path).read_text(encoding="utf-8")
    assert sections.has_section(text, "story:US1:discussion")
    # comment targets the nested discussion only
    await svc.comment(feat.id, ["scope it"], as_slug="product-owner", story="US1")
    text = svc.paths.abspath((await svc.get(feat.id)).path).read_text(encoding="utf-8")
    us1 = sections.get_section(text, "story:US1:discussion")
    us2 = sections.get_section(text, "story:US2:discussion")
    assert us1 is not None and us2 is not None
    assert "scope it" in us1
    assert us2.strip() == ""
    assert [b.local_id for b in await svc.list_stories(feat.id)] == ["US1", "US2"]


async def test_story_body_set_via_sq_and_preserved_by_comment(svc):
    feat = (await svc.create("feature", "Login")).item
    await svc.add_story(feat.id)  # no title → empty heading, placeholder body
    # the body is set through sq (no manual file editing), multiline prose + bullets
    body = "As an admin, I want resets.\n\nAcceptance:\n- link expires in 30m\n- audit logged"
    await svc.set_story_body(feat.id, "US1", body)
    detail = await svc.get_story(feat.id, "US1")
    assert detail.body == body
    # commenting only touches the discussion, never the body
    await svc.comment(feat.id, ["go"], as_slug="operator", story="US1")
    after = await svc.get_story(feat.id, "US1")
    assert after.body == body
    assert "go" in after.discussion
    # title is explicit frontmatter state; an untitled story stays untitled (body is separate prose)
    (story,) = await svc.list_stories(feat.id)
    assert (story.local_id, story.title) == ("US1", "")


async def test_subtask_body_set_append_and_reject_markers(svc):
    task = (await svc.create("task", "t")).item
    await svc.add_subtask(task.id, "Validate")
    await svc.set_subtask_body(task.id, "ST1", "First paragraph.\n\nSecond.")
    assert (await svc.get_subtask(task.id, "ST1")).body == "First paragraph.\n\nSecond."
    # append adds a paragraph after the existing body
    await svc.set_subtask_body(task.id, "ST1", "Third.", append=True)
    assert (await svc.get_subtask(task.id, "ST1")).body.endswith("Second.\n\nThird.")
    # a body carrying an sq marker is rejected
    with pytest.raises(SquadsError, match="marker"):
        await svc.set_subtask_body(task.id, "ST1", "oops <!-- sq:body:end --> oops")


async def test_append_overwrites_placeholder(svc):
    task = (await svc.create("task", "t")).item
    await svc.add_subtask(task.id, "Validate")  # body is still the italic placeholder
    await svc.set_subtask_body(task.id, "ST1", "Real content.", append=True)
    assert (
        await svc.get_subtask(task.id, "ST1")
    ).body == "Real content."  # replaced, not appended after


async def _head(svc, item_id, tag):
    text = svc.paths.abspath((await svc.get(item_id)).path).read_text(encoding="utf-8")
    return sections.get_section(text, tag) or ""


async def test_assignee_full_name_rendered_under_heading(svc):
    await svc.add_dev("python", name="Grace Hopper")  # python-dev
    await svc.add_dev("rust", name="Alan Turing")  # rust-dev
    task = (await svc.create("task", "t")).item

    # set at add time: the :head shows the full name; the slug is the frontmatter state
    await svc.add_subtask(task.id, "Validate", assignee="python-dev")
    head = await _head(svc, task.id, "subtask:ST1:head")
    assert "**Assignee:** Grace Hopper" in head
    assert (await svc.list_subtasks(task.id))[
        0
    ].assignee == "python-dev"  # frontmatter keeps the slug
    # the head sits between the heading and the block's body region
    text = svc.paths.abspath((await svc.get(task.id)).path).read_text(encoding="utf-8")
    assert text.index("### ST1") < text.index("subtask:ST1:head") < text.index("subtask:ST1:body")

    # reassign updates the rendered name
    await svc.set_subtask_assignee(task.id, "ST1", "rust-dev")
    assert "**Assignee:** Alan Turing" in await _head(svc, task.id, "subtask:ST1:head")

    # --clear drops the assignee line; the status badge stays
    await svc.set_subtask_assignee(task.id, "ST1", None)
    head = await _head(svc, task.id, "subtask:ST1:head")
    assert "**Assignee:**" not in head and "**Status:**" in head
    assert (await svc.list_subtasks(task.id))[0].assignee is None


async def test_head_shows_status_severity_and_story(svc):
    await svc.add_dev("python", name="Grace Hopper")
    feat = (await svc.create("feature", "Login")).item
    await svc.add_story(feat.id, "As a user, I want to reset my password")  # US1
    task = (await svc.create("task", "Auth", parent=feat.id)).item

    # a fresh subtask already shows its status badge (no assignee line yet)
    await svc.add_subtask(task.id, "Validate", story="US1")
    head = await _head(svc, task.id, "subtask:ST1:head")
    assert "**Status:** ⚪ Todo" in head and "**Assignee:**" not in head
    # the story link resolves to "USn — title"
    assert "**Implements:** US1 — As a user, I want to reset my password" in head

    # status transitions re-render the badge
    await svc.set_subtask_status(task.id, "ST1", Status.IN_PROGRESS)
    assert "**Status:** 🟡 In Progress" in await _head(svc, task.id, "subtask:ST1:head")

    # findings show a severity badge
    rev = (await svc.create("review", "r")).item
    await svc.add_finding(rev.id, "Null deref", severity=Severity.HIGH)
    assert "**Severity:** 🟠 High" in await _head(svc, rev.id, "finding:F1:head")


async def test_body_set_at_add_time(svc):
    feat = (await svc.create("feature", "f")).item
    await svc.add_story(
        feat.id, body="As an admin, I want resets.\n\nAcceptance: link expires in 30m"
    )
    (story,) = await svc.list_stories(feat.id)
    assert story.title == ""  # title is explicit; the body is independent prose
    assert (await svc.get_story(feat.id, story.local_id)).body.startswith("As an admin")


async def test_update_subtask_title_rerenders_heading_and_summary(svc):
    task = (await svc.create("task", "t")).item
    await svc.add_subtask(task.id, "Old name", body="prose body")
    await svc.set_subtask_status(task.id, "ST1", Status.IN_PROGRESS)

    await svc.update_subtask(task.id, "ST1", title="New name")

    # frontmatter title updated, other state untouched
    sub = (await svc.list_subtasks(task.id))[0]
    assert (sub.title, sub.status) == ("New name", Status.IN_PROGRESS)
    text = svc.paths.abspath((await svc.get(task.id)).path).read_text(encoding="utf-8")
    # the body heading and the parent summary-table row both re-render; the body prose is preserved
    assert "### ST1 — New name" in text and "Old name" not in text
    assert "| ST1 | InProgress |  | New name |" in text
    assert (await svc.get_subtask(task.id, "ST1")).body == "prose body"


async def test_update_finding_severity(svc):
    rev = (await svc.create("review", "r")).item
    await svc.add_finding(rev.id, "Null deref", severity=Severity.MEDIUM)

    await svc.update_finding(rev.id, "F1", severity=Severity.HIGH)

    assert (await svc.list_findings(rev.id))[0].severity is Severity.HIGH
    text = svc.paths.abspath((await svc.get(rev.id)).path).read_text(encoding="utf-8")
    assert "severity: high" in text  # frontmatter state
    assert "**Severity:** 🟠 High" in await _head(svc, rev.id, "finding:F1:head")  # head badge
    assert "🟠 high" in text  # summary cell


async def test_update_subtask_story_remap_validate_and_clear(svc):
    feat = (await svc.create("feature", "Login")).item
    await svc.add_story(feat.id, "Reset password")  # US1
    await svc.add_story(feat.id, "Lockout policy")  # US2
    task = (await svc.create("task", "Auth", parent=feat.id)).item
    await svc.add_subtask(task.id, "Validate", story="US1")

    # remap to a different (existing) story → head "Implements" + summary Story column update
    await svc.update_subtask(task.id, "ST1", story="US2")
    assert (await svc.list_subtasks(task.id))[0].story == "US2"
    assert "**Implements:** US2 — Lockout policy" in await _head(svc, task.id, "subtask:ST1:head")

    # an unknown story is rejected
    with pytest.raises(SquadsError, match="US9"):
        await svc.update_subtask(task.id, "ST1", story="US9")

    # --no-story clears the mapping
    await svc.update_subtask(task.id, "ST1", clear_story=True)
    assert (await svc.list_subtasks(task.id))[0].story is None
    assert "**Implements:**" not in await _head(svc, task.id, "subtask:ST1:head")


async def test_update_applies_several_fields_and_validates_status(svc):
    await svc.add_dev("python", name="Grace Hopper")  # python-dev
    task = (await svc.create("task", "t")).item
    await svc.add_subtask(task.id, "Old")

    # one call sets title + assignee + status (a valid transition)
    await svc.update_subtask(
        task.id, "ST1", title="New", assignee="python-dev", status=Status.IN_PROGRESS
    )
    sub = (await svc.list_subtasks(task.id))[0]
    assert (sub.title, sub.assignee, sub.status) == ("New", "python-dev", Status.IN_PROGRESS)

    # an invalid transition is rejected without --force, accepted with it
    with pytest.raises(SquadsError, match="cannot move"):
        await svc.update_subtask(task.id, "ST1", status=Status.TODO)
    await svc.update_subtask(task.id, "ST1", status=Status.TODO, force=True)
    assert (await svc.list_subtasks(task.id))[0].status == Status.TODO

    # an unregistered assignee is rejected
    with pytest.raises(SquadsError, match="not a registered agent"):
        await svc.update_subtask(task.id, "ST1", assignee="ghost")


async def test_empty_title_summary_is_blank_not_marker(svc):
    # regression: heading parse must not bleed into the next line's marker
    feat = (await svc.create("feature", "f")).item
    await svc.add_story(feat.id)
    (story,) = await svc.list_stories(feat.id)
    assert (story.local_id, story.title) == ("US1", "")


async def test_stories_only_on_features(svc):
    task = (await svc.create("task", "t")).item
    with pytest.raises(SquadsError):
        await svc.add_story(task.id, "As a user...")


async def test_subtask_done_toggle(svc):
    task = (await svc.create("task", "t")).item
    await svc.add_subtask(task.id, "Validate expiry")
    await svc.set_subtask_done(task.id, "ST1", done=True)
    assert (await svc.list_subtasks(task.id))[0].status == "Done"
    await svc.set_subtask_done(task.id, "ST1", done=False)
    assert (await svc.list_subtasks(task.id))[0].status == "Todo"


async def test_subtask_status_machine(svc):
    task = (await svc.create("task", "t")).item
    await svc.add_subtask(task.id, "Validate")
    await svc.set_subtask_status(task.id, "ST1", Status.IN_PROGRESS)
    assert (await svc.list_subtasks(task.id))[0].status == "InProgress"
    # Todo→Done is not a legal move (must pass through InProgress); already InProgress→Done is ok
    await svc.set_subtask_status(task.id, "ST1", Status.DONE)
    assert (await svc.list_subtasks(task.id))[0].status == "Done"
    with pytest.raises(SquadsError):
        await svc.set_story_status(task.id, "ST1", Status.TODO)  # wrong parent type


async def test_subtask_done_unknown_id(svc):
    task = (await svc.create("task", "t")).item
    with pytest.raises(SquadsError):
        await svc.set_subtask_done(task.id, "ST9")


async def test_subtask_assignee_set_reassigned_and_cleared(svc):
    await svc.add_dev("python")  # registers python-dev
    task = (await svc.create("task", "t")).item
    await svc.add_subtask(task.id, "Wire API", assignee="python-dev")
    assert (await svc.list_subtasks(task.id))[0].assignee == "python-dev"
    # reassignment validates against the roster
    await svc.set_subtask_assignee(task.id, "ST1", "manager")
    assert (await svc.list_subtasks(task.id))[0].assignee == "manager"
    with pytest.raises(SquadsError, match="not a registered agent"):
        await svc.set_subtask_assignee(task.id, "ST1", "ghost")
    with pytest.raises(SquadsError, match="not a registered agent"):
        await svc.add_subtask(task.id, "x", assignee="ghost")
    # reassigning preserves the status set in between
    await svc.set_subtask_status(task.id, "ST1", Status.IN_PROGRESS)
    await svc.set_subtask_assignee(task.id, "ST1", "python-dev")
    assert (await svc.list_subtasks(task.id))[0].status == "InProgress"
    # --clear path: None unassigns, and the summary table reflects it
    await svc.set_subtask_assignee(task.id, "ST1", None)
    assert (await svc.list_subtasks(task.id))[0].assignee is None
    text = svc.paths.abspath((await svc.get(task.id)).path).read_text(encoding="utf-8")
    assert "| Subtask | Status | Assignee | Title | Story |" in text


# --------------------------------------------------------------------------- inbox


async def test_inbox_finds_open_mentions_only(svc):
    t1 = (await svc.create("task", "open one")).item
    t2 = (await svc.create("task", "done one")).item
    await svc.comment(t1.id, ["@qa please verify"], as_slug="architect")
    await svc.comment(t2.id, ["@qa check this too"], as_slug="architect")
    await svc.set_status(t2.id, Status.IN_PROGRESS)
    await svc.set_status(t2.id, Status.DONE)  # terminal → excluded from inbox
    hits = await svc.inbox("qa")
    ids = {it.id for it, _ in hits}
    assert t1.id in ids
    assert t2.id not in ids
    # mention lines are surfaced
    lines = next(lns for it, lns in hits if it.id == t1.id)
    assert any("@qa" in ln for ln in lines)


async def test_inbox_accepts_at_prefix(svc):
    t = (await svc.create("task", "t")).item
    await svc.comment(t.id, ["@reviewer take a look"], as_slug="operator")
    assert {i.id for i, _ in await svc.inbox("@reviewer")} == {t.id}


async def test_inbox_surfaces_mention_in_subentity_discussion(svc):
    # FEAT-000062 US3 no-regression: @mentions written in sub-entity discussions (story, subtask,
    # finding) must be surfaced by sq inbox exactly like item-level mentions.
    # Story discussion on a feature
    feat = (await svc.create("feature", "Login feature")).item
    await svc.add_story(feat.id, "Password reset")  # US1
    await svc.comment(
        feat.id, ["@qa please verify acceptance"], as_slug="product-owner", story="US1"
    )
    ids = {it.id for it, _ in await svc.inbox("qa")}
    assert feat.id in ids

    # Subtask discussion on a task
    task = (await svc.create("task", "Implement reset")).item
    await svc.add_subtask(task.id, "Wire endpoint")  # ST1
    await svc.comment(task.id, ["@reviewer look at this subtask"], as_slug="manager", subtask="ST1")
    ids = {it.id for it, _ in await svc.inbox("reviewer")}
    assert task.id in ids

    # Finding discussion on a review
    rev = (await svc.create("review", "Code review")).item
    await svc.add_finding(rev.id, "Null deref")  # F1
    await svc.comment(rev.id, ["@qa does this fix satisfy?"], as_slug="reviewer", finding="F1")
    ids = {it.id for it, _ in await svc.inbox("qa")}
    assert rev.id in ids


# --------------------------------------------------------------------------- check


async def test_check_clean_after_init(svc):
    await svc.create("feature", "f")
    assert await svc.check() == []


async def test_check_detects_dangling_parent(svc):
    task = (await svc.create("task", "t")).item
    # corrupt the index directly: point at a non-existent parent
    async with svc.store.transaction() as db:
        db.items[task.sequence_id].parent = "FEAT-999999"
    issues = await svc.check()
    assert any("dangling parent" in i.message and i.item == task.id for i in issues)


async def test_check_detects_broken_marker(svc):
    task = (await svc.create("task", "t")).item
    path = svc.paths.abspath(task.path)
    text = path.read_text(encoding="utf-8").replace("<!-- sq:body:end -->", "")  # remove a close
    path.write_text(text, encoding="utf-8")
    issues = await svc.check()
    assert any("sq:body" in i.message for i in issues)


# --------------------------------------------------------------------------- marker-injection guard


# Build the well-formed marker string at runtime so this source file itself does
# not contain a literal marker tag (which would be caught by sq check).
_MARKER_TAG = "<!-- sq:body -->"
_BACKTICK_MARKER_TAG = f"`{_MARKER_TAG}`"


async def test_comment_with_marker_tag_rejected(svc):
    """A comment message containing a well-formed sq marker tag raises SquadsError."""
    task = (await svc.create("task", "t")).item
    with pytest.raises(SquadsError, match="marker"):
        await svc.comment(task.id, [f"see the {_MARKER_TAG} region"], as_slug="manager")


async def test_comment_with_backtick_marker_rejected(svc):
    """Backtick-wrapping does not neutralize a marker tag in a comment."""
    task = (await svc.create("task", "t")).item
    with pytest.raises(SquadsError, match="marker"):
        await svc.comment(task.id, [f"see {_BACKTICK_MARKER_TAG}"], as_slug="manager")


async def test_comment_marker_leaves_file_untouched(svc):
    """A rejected comment must not partially write to the item file."""
    task = (await svc.create("task", "t")).item
    path = svc.paths.abspath((await svc.get(task.id)).path)
    text_before = path.read_text(encoding="utf-8")
    with pytest.raises(SquadsError):
        await svc.comment(task.id, [f"inject {_MARKER_TAG} here"], as_slug="manager")
    assert path.read_text(encoding="utf-8") == text_before  # file completely untouched
    assert await svc.check() == []  # no marker integrity issues


async def test_comment_marker_in_any_message_rejected(svc):
    """All -m messages are validated; a marker in a later message also rejects."""
    task = (await svc.create("task", "t")).item
    with pytest.raises(SquadsError, match="marker"):
        await svc.comment(
            task.id, ["safe first line", f"bad {_MARKER_TAG} line"], as_slug="manager"
        )


async def test_subentity_targeted_comment_with_marker_rejected(svc):
    """A sub-entity-targeted comment (story/subtask/finding) is also guarded."""
    feat = (await svc.create("feature", "f")).item
    await svc.add_story(feat.id, "A story")  # US1
    with pytest.raises(SquadsError, match="marker"):
        await svc.comment(feat.id, [f"inject {_MARKER_TAG}"], as_slug="product-owner", story="US1")


async def test_add_story_title_with_marker_rejected(svc):
    """Creating a story with a marker tag in the title raises SquadsError."""
    feat = (await svc.create("feature", "f")).item
    with pytest.raises(SquadsError, match="marker"):
        await svc.add_story(feat.id, f"title {_MARKER_TAG} here")


async def test_add_subtask_title_with_marker_rejected(svc):
    """Creating a subtask with a marker tag in the title raises SquadsError."""
    task = (await svc.create("task", "t")).item
    with pytest.raises(SquadsError, match="marker"):
        await svc.add_subtask(task.id, f"subtask {_MARKER_TAG}")


async def test_add_finding_title_with_marker_rejected(svc):
    """Creating a finding with a marker tag in the title raises SquadsError."""
    rev = (await svc.create("review", "r")).item
    with pytest.raises(SquadsError, match="marker"):
        await svc.add_finding(rev.id, f"finding {_MARKER_TAG}")


async def test_update_subentity_title_with_marker_rejected(svc):
    """Updating a sub-entity title to include a marker tag raises SquadsError."""
    task = (await svc.create("task", "t")).item
    await svc.add_subtask(task.id, "clean title")
    with pytest.raises(SquadsError, match="marker"):
        await svc.update_subtask(task.id, "ST1", title=f"inject {_MARKER_TAG}")
    # the title must be unchanged after rejection
    assert (await svc.list_subtasks(task.id))[0].title == "clean title"


async def test_item_update_title_description_not_affected(svc):
    """Item-level update --title and --description with non-marker bracket/backtick content pass."""
    task = (await svc.create("task", "t")).item
    # bracket content that is not a well-formed marker tag → allowed
    ok = await svc.update(task.id, title="[x] done label")
    assert ok.title == "[x] done label"
    # a description containing backticks → allowed
    ok2 = await svc.update(task.id, description="Use `sq:body` syntax (plain text)")
    assert "sq:body" in ok2.description
    # a title containing sq: text without the HTML-comment wrapper → allowed
    ok3 = await svc.update(task.id, title="Edit the sq:body region")
    assert ok3.title == "Edit the sq:body region"


async def test_body_guard_message_unchanged(svc):
    """The existing body-guard message is preserved verbatim (regression guard)."""
    task = (await svc.create("task", "t")).item
    with pytest.raises(SquadsError, match="body must not contain sq marker comments"):
        await svc.set_body(task.id, f"bad body {_MARKER_TAG}")
