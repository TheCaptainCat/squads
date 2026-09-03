"""Sub-entity state (status/assignee/severity/story) lives entirely in frontmatter — never in
body markers (CLAUDE.md invariant #1, sub-entity half). Every mutation re-renders only the
block's own ``### <local_id> — title`` heading; it materialises no presentation region for that
state — no ``:head`` badge line, no parent ``:summary`` roll-up table. Those are computed on
request instead (``_cli._common._subentity_badge_line`` and a declared ``subentity``-source
view), proven byte-identical in ``tests/unit/test_computed_subentity_renderings_are_stable.py``.
"""

import pytest

from _helpers import create_item
from squads._errors import SquadsError
from squads._itemfile import read_frontmatter

pytestmark = pytest.mark.anyio


async def test_subentity_state_lives_in_frontmatter_not_body_markers(svc):
    feat = (await create_item(svc, "feature", "Login")).item
    await svc.add_story(feat.id, "Reset password")
    task = (await create_item(svc, "task", "Auth", parent=feat.id)).item
    await svc.add_subtask(task.id, "Validate", story="US1")
    await svc.set_subtask_status(task.id, "ST1", "InProgress")

    text = svc.paths.abspath((await svc.get(task.id)).path).read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    assert fm["subentities"] == [
        {"local_id": "ST1", "title": "Validate", "status": "InProgress", "story": "US1"}
    ]
    assert ":meta" not in text
    assert "<!-- sq:subtask:ST1:body -->" in text
    assert "<!-- sq:subtask:ST1:head -->" not in text
    assert "<!-- sq:summary -->" not in text


async def test_assignee_reassign_and_clear_updates_frontmatter_only_no_head_region(svc):
    await svc.add_dev("python", name="Grace Hopper")
    await svc.add_dev("rust", name="Alan Turing")
    task = (await create_item(svc, "task", "t")).item

    await svc.add_subtask(task.id, "Validate", assignee="python-dev")
    assert (await svc.list_subtasks(task.id))[0].assignee == "python-dev"  # slug in frontmatter

    await svc.set_subtask_assignee(task.id, "ST1", "rust-dev")
    assert (await svc.list_subtasks(task.id))[0].assignee == "rust-dev"

    await svc.set_subtask_assignee(task.id, "ST1", None)
    assert (await svc.list_subtasks(task.id))[0].assignee is None

    text = svc.paths.abspath((await svc.get(task.id)).path).read_text(encoding="utf-8")
    assert "<!-- sq:subtask:ST1:head -->" not in text


async def test_status_transition_and_story_link_update_frontmatter_only(svc):
    feat = (await create_item(svc, "feature", "Login")).item
    await svc.add_story(feat.id, "As a user, I want to reset my password")
    task = (await create_item(svc, "task", "Auth", parent=feat.id)).item

    await svc.add_subtask(task.id, "Validate", story="US1")
    sub = (await svc.list_subtasks(task.id))[0]
    assert (sub.status, sub.story) == ("Todo", "US1")

    await svc.set_subtask_status(task.id, "ST1", "InProgress")
    assert (await svc.list_subtasks(task.id))[0].status == "InProgress"


async def test_finding_severity_updates_frontmatter_and_never_touches_a_summary_table(svc):
    rev = (await create_item(svc, "review", "r")).item
    await svc.add_finding(rev.id, "Null deref", severity="medium")
    await svc.update_finding(rev.id, "F1", severity="high")

    assert (await svc.list_findings(rev.id))[0].severity == "high"
    text = svc.paths.abspath((await svc.get(rev.id)).path).read_text(encoding="utf-8")
    assert "severity: high" in text  # frontmatter state
    assert "<!-- sq:summary -->" not in text
    assert "| F1 | 🟠 high |" not in text  # no materialised summary-table row


async def test_update_subtask_title_rerenders_heading_preserving_body_and_no_summary_row(svc):
    task = (await create_item(svc, "task", "t")).item
    await svc.add_subtask(task.id, "Old name", body="prose body")
    await svc.set_subtask_status(task.id, "ST1", "InProgress")

    await svc.update_subtask(task.id, "ST1", title="New name")

    sub = (await svc.list_subtasks(task.id))[0]
    assert (sub.title, sub.status) == ("New name", "InProgress")
    text = svc.paths.abspath((await svc.get(task.id)).path).read_text(encoding="utf-8")
    assert "### ST1 — New name" in text and "Old name" not in text
    assert "| ST1 | InProgress |" not in text  # no materialised summary-table row
    assert (await svc.get_subtask(task.id, "ST1")).body == "prose body"


async def test_update_subtask_story_remap_validates_and_clears(svc):
    feat = (await create_item(svc, "feature", "Login")).item
    await svc.add_story(feat.id, "Reset password")
    await svc.add_story(feat.id, "Lockout policy")
    task = (await create_item(svc, "task", "Auth", parent=feat.id)).item
    await svc.add_subtask(task.id, "Validate", story="US1")

    await svc.update_subtask(task.id, "ST1", story="US2")
    assert (await svc.list_subtasks(task.id))[0].story == "US2"

    with pytest.raises(SquadsError, match="US9"):
        await svc.update_subtask(task.id, "ST1", story="US9")

    await svc.update_subtask(task.id, "ST1", clear_story=True)
    assert (await svc.list_subtasks(task.id))[0].story is None


async def test_update_applies_several_fields_at_once_and_still_validates_status_and_assignee(svc):
    await svc.add_dev("python", name="Grace Hopper")
    task = (await create_item(svc, "task", "t")).item
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
    feat = (await create_item(svc, "feature", "f")).item
    await svc.add_story(
        feat.id, body="As an admin, I want resets.\n\nAcceptance: link expires in 30m"
    )
    (story,) = await svc.list_stories(feat.id)
    assert story.title == ""  # title is explicit; the body is independent prose
    assert (await svc.get_story(feat.id, story.local_id)).body.startswith("As an admin")
