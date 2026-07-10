"""Sub-entity state (status/assignee/severity/story) lives entirely in frontmatter — never in
body markers — and every mutation re-renders the derived `:head` badge line plus the parent's
roll-up summary table (CLAUDE.md invariant #1, sub-entity half).
"""

import pytest

from squads._errors import SquadsError
from squads._itemfile import read_frontmatter

pytestmark = pytest.mark.anyio


async def test_subentity_state_lives_in_frontmatter_not_body_markers(svc):
    feat = (await svc.create("feature", "Login")).item
    await svc.add_story(feat.id, "Reset password")  # US1
    task = (await svc.create("task", "Auth", parent=feat.id)).item
    await svc.add_subtask(task.id, "Validate", story="US1")
    await svc.set_subtask_status(task.id, "ST1", "InProgress")

    text = svc.paths.abspath((await svc.get(task.id)).path).read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    assert fm["subentities"] == [
        {"local_id": "ST1", "title": "Validate", "status": "InProgress", "story": "US1"}
    ]
    assert ":meta" not in text
    assert "<!-- sq:subtask:ST1:head -->" in text and "<!-- sq:subtask:ST1:body -->" in text


async def _head(svc, item_id, tag):
    from squads import _sections as sections

    text = svc.paths.abspath((await svc.get(item_id)).path).read_text(encoding="utf-8")
    return sections.get_section(text, tag) or ""


async def test_assignee_render_reassign_and_clear_updates_the_head_badge_not_frontmatter_alone(svc):
    await svc.add_dev("python", name="Grace Hopper")
    await svc.add_dev("rust", name="Alan Turing")
    task = (await svc.create("task", "t")).item

    await svc.add_subtask(task.id, "Validate", assignee="python-dev")
    assert "**Assignee:** Grace Hopper" in await _head(svc, task.id, "subtask:ST1:head")
    assert (await svc.list_subtasks(task.id))[0].assignee == "python-dev"  # slug in frontmatter

    await svc.set_subtask_assignee(task.id, "ST1", "rust-dev")
    assert "**Assignee:** Alan Turing" in await _head(svc, task.id, "subtask:ST1:head")

    await svc.set_subtask_assignee(task.id, "ST1", None)
    head = await _head(svc, task.id, "subtask:ST1:head")
    assert "**Assignee:**" not in head and "**Status:**" in head


async def test_status_transition_and_story_link_rerender_the_head_badge(svc):
    feat = (await svc.create("feature", "Login")).item
    await svc.add_story(feat.id, "As a user, I want to reset my password")  # US1
    task = (await svc.create("task", "Auth", parent=feat.id)).item

    await svc.add_subtask(task.id, "Validate", story="US1")
    head = await _head(svc, task.id, "subtask:ST1:head")
    assert "**Status:** ⚪ Todo" in head
    assert "**Implements:** US1 — As a user, I want to reset my password" in head

    await svc.set_subtask_status(task.id, "ST1", "InProgress")
    assert "**Status:** 🟡 In Progress" in await _head(svc, task.id, "subtask:ST1:head")


async def test_finding_severity_badge_renders_in_the_head_and_survives_an_update(svc):
    rev = (await svc.create("review", "r")).item
    await svc.add_finding(rev.id, "Null deref", severity="medium")
    await svc.update_finding(rev.id, "F1", severity="high")

    assert (await svc.list_findings(rev.id))[0].severity == "high"
    text = svc.paths.abspath((await svc.get(rev.id)).path).read_text(encoding="utf-8")
    assert "severity: high" in text  # frontmatter state
    assert "**Severity:** 🟠 High" in await _head(svc, rev.id, "finding:F1:head")  # head badge
    assert "🟠 high" in text  # summary table cell


async def test_update_subtask_title_rerenders_heading_and_summary_preserving_body(svc):
    task = (await svc.create("task", "t")).item
    await svc.add_subtask(task.id, "Old name", body="prose body")
    await svc.set_subtask_status(task.id, "ST1", "InProgress")

    await svc.update_subtask(task.id, "ST1", title="New name")

    sub = (await svc.list_subtasks(task.id))[0]
    assert (sub.title, sub.status) == ("New name", "InProgress")
    text = svc.paths.abspath((await svc.get(task.id)).path).read_text(encoding="utf-8")
    assert "### ST1 — New name" in text and "Old name" not in text
    assert "| ST1 | InProgress |  | New name |" in text
    assert (await svc.get_subtask(task.id, "ST1")).body == "prose body"


async def test_update_subtask_story_remap_validates_and_clears(svc):
    feat = (await svc.create("feature", "Login")).item
    await svc.add_story(feat.id, "Reset password")  # US1
    await svc.add_story(feat.id, "Lockout policy")  # US2
    task = (await svc.create("task", "Auth", parent=feat.id)).item
    await svc.add_subtask(task.id, "Validate", story="US1")

    await svc.update_subtask(task.id, "ST1", story="US2")
    assert (await svc.list_subtasks(task.id))[0].story == "US2"
    assert "**Implements:** US2 — Lockout policy" in await _head(svc, task.id, "subtask:ST1:head")

    with pytest.raises(SquadsError, match="US9"):
        await svc.update_subtask(task.id, "ST1", story="US9")

    await svc.update_subtask(task.id, "ST1", clear_story=True)
    assert (await svc.list_subtasks(task.id))[0].story is None
    assert "**Implements:**" not in await _head(svc, task.id, "subtask:ST1:head")


async def test_update_applies_several_fields_at_once_and_still_validates_status_and_assignee(svc):
    await svc.add_dev("python", name="Grace Hopper")
    task = (await svc.create("task", "t")).item
    await svc.add_subtask(task.id, "Old")

    await svc.update_subtask(
        task.id, "ST1", title="New", assignee="python-dev", status="InProgress"
    )
    sub = (await svc.list_subtasks(task.id))[0]
    assert (sub.title, sub.assignee, sub.status) == ("New", "python-dev", "InProgress")

    with pytest.raises(SquadsError, match="cannot move"):
        await svc.update_subtask(task.id, "ST1", status="Todo")
    await svc.update_subtask(task.id, "ST1", status="Todo", force=True)
    assert (await svc.list_subtasks(task.id))[0].status == "Todo"

    with pytest.raises(SquadsError, match="not a registered agent"):
        await svc.update_subtask(task.id, "ST1", assignee="ghost")


async def test_body_set_at_add_time_is_independent_of_the_title(svc):
    feat = (await svc.create("feature", "f")).item
    await svc.add_story(
        feat.id, body="As an admin, I want resets.\n\nAcceptance: link expires in 30m"
    )
    (story,) = await svc.list_stories(feat.id)
    assert story.title == ""  # title is explicit; the body is independent prose
    assert (await svc.get_story(feat.id, story.local_id)).body.startswith("As an admin")
