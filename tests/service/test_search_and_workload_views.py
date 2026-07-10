"""``sq search`` matches an item's title or body (case-insensitive); ``sq workload`` counts open
vs. closed items per assignee, with unassigned items grouped under ``None``; ``sq mine`` (backed
by ``list_items(assignee=...)``) returns exactly the items assigned to one slug and excludes
items assigned to another.
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_search_matches_title_and_body_but_not_an_absent_term(svc):
    res = await svc.create("task", "Token validation")
    await svc.set_body(res.item.id, "Validate the JWT expiry and signature.")

    by_title = await svc.search("token")
    assert [i.id for i, _ in by_title] == [res.item.id]
    by_body = await svc.search("expiry")
    assert res.item.id in [i.id for i, _ in by_body]
    assert await svc.search("nonexistent-needle") == []


async def test_workload_counts_open_and_closed_per_assignee_and_groups_unassigned(svc):
    await svc.create("task", "t1", assignee="manager")
    done = (await svc.create("task", "t2", assignee="manager")).item
    await svc.set_status(done.id, "InProgress")
    await svc.set_status(done.id, "Done")
    await svc.create("task", "unassigned")

    rows = {r.assignee: r for r in await svc.workload()}
    assert rows["manager"].open == 1
    assert rows["manager"].closed == 1
    assert rows["manager"].total == 2
    assert rows[None].open == 1


async def test_mine_view_returns_exactly_the_items_assigned_to_that_slug(svc):
    """The 'mine' view filters strictly by assignee: an item assigned to slug A is returned,
    an item assigned to a different slug B is not — a positive assertion, not just that the
    slug argument itself validates (that's the separate slug-validation cluster)."""
    await svc.add_dev("python")  # registers python-dev
    mine = (await svc.create("task", "Mine", assignee="manager")).item
    await svc.create("task", "Not mine", assignee="python-dev")

    got = await svc.list_items(assignee="manager")
    assert [i.id for i in got] == [mine.id]
