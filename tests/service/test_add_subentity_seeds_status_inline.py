"""``add_block`` (and its ``add_story``/``add_subtask``/``add_finding`` delegators) accept an
optional ``status`` to seed a fresh sub-entity directly at a non-initial state, at parity with
``update``. The provided value is scope-checked against the KIND'S OWN lifecycle — not just the
spec's global status set — so a status that only exists on a different kind's machine is
rejected rather than silently accepted.
"""

import pytest

from squads._errors import SquadsError

pytestmark = pytest.mark.anyio


async def test_add_story_seeds_the_given_status_instead_of_the_initial_one(svc):
    feat = (await svc.create("feature", "Login")).item
    await svc.add_story(feat.id, "Reset password", status="InProgress")

    (story,) = await svc.list_stories(feat.id)
    assert story.status == "InProgress"


async def test_add_subtask_seeds_the_given_status_and_round_trips_in_frontmatter(svc):
    from squads._itemfile import read_frontmatter

    task = (await svc.create("task", "Auth")).item
    await svc.add_subtask(task.id, "Validate", status="Blocked")

    (subtask,) = await svc.list_subtasks(task.id)
    assert subtask.status == "Blocked"
    text = svc.paths.abspath((await svc.get(task.id)).path).read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    assert fm["subentities"][0]["status"] == "Blocked"


async def test_add_finding_seeds_the_given_status_alongside_its_severity_default(svc):
    rev = (await svc.create("review", "r")).item
    finding = await svc.add_finding(rev.id, "Null deref", status="Fixed")

    detail = await svc.get_block(rev.id, "finding", finding.local_id)
    assert detail.info.status == "Fixed"
    assert detail.info.severity == "medium"  # the severity default is untouched by --status


async def test_add_finding_severity_flag_behaviour_is_unchanged_by_the_new_status_axis(svc):
    rev = (await svc.create("review", "r")).item
    finding = await svc.add_finding(rev.id, "Race condition", severity="high")

    detail = await svc.get_block(rev.id, "finding", finding.local_id)
    assert detail.info.severity == "high"
    assert detail.info.status == "Open"  # unchanged: initial status when --status is omitted


async def test_add_without_status_still_seeds_the_kinds_initial_status(svc):
    task = (await svc.create("task", "t")).item
    await svc.add_subtask(task.id, "Old-style call, no flags")

    (subtask,) = await svc.list_subtasks(task.id)
    assert subtask.status == "Todo"


async def test_a_status_outside_the_kinds_own_lifecycle_is_rejected_not_seeded(svc):
    rev = (await svc.create("review", "r")).item

    # "InProgress" is a valid *story/subtask* status but not a member of the finding
    # lifecycle (Open/Fixed/Verified/WontFix) — must fail closed, scoped to the kind.
    with pytest.raises(SquadsError, match="InProgress"):
        await svc.add_finding(rev.id, "Null deref", status="InProgress")

    assert await svc.list_findings(rev.id) == []


async def test_a_finding_only_status_is_rejected_on_a_story(svc):
    feat = (await svc.create("feature", "Login")).item

    with pytest.raises(SquadsError, match="WontFix"):
        await svc.add_story(feat.id, "Reset password", status="WontFix")

    assert await svc.list_stories(feat.id) == []
