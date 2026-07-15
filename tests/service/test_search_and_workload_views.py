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
    assert [r.item.id for r in by_title] == [res.item.id]
    by_body = await svc.search("expiry")
    assert res.item.id in [r.item.id for r in by_body]
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


async def test_search_status_filter_ands_with_the_query_and_type(svc):
    open_task = await svc.create("task", "Retry the payment webhook")
    done_task = (await svc.create("task", "Retry the payment queue")).item
    await svc.set_status(done_task.id, "InProgress")
    await svc.set_status(done_task.id, "Done")
    await svc.create("bug", "Retry the payment gateway")

    only_open_tasks = await svc.search("retry", item_type="task", status="Draft")
    assert [r.item.id for r in only_open_tasks] == [open_task.item.id]

    only_done = await svc.search("retry", status="Done")
    assert [r.item.id for r in only_done] == [done_task.id]


async def test_search_hit_regions_distinguish_body_sub_entity_and_discussion_comment(svc):
    feature = (await svc.create("feature", "Login flow")).item
    await svc.set_body(feature.id, "Ship the frostbite login redesign.")
    await svc.add_story(feature.id, "frostbite onboarding", body="Cover the frostbite case.")
    await svc.comment(feature.id, ["mention frostbite in the release notes"], as_slug="manager")

    results = await svc.search("frostbite")
    assert len(results) == 1
    regions = {h.region for h in results[0].hits}
    assert "body" in regions
    assert "story:US1" in regions
    assert any(r.startswith("discussion#") for r in regions)


async def test_search_result_carries_item_type_and_status(svc):
    task = (await svc.create("task", "Investigate flaky retry")).item
    await svc.set_status(task.id, "InProgress")

    results = await svc.search("flaky")
    assert results[0].item.type == "task"
    assert results[0].item.status == "InProgress"


async def test_mine_view_returns_exactly_the_items_assigned_to_that_slug(svc):
    """The 'mine' view filters strictly by assignee: an item assigned to slug A is returned,
    an item assigned to a different slug B is not — a positive assertion, not just that the
    slug argument itself validates (that's the separate slug-validation cluster)."""
    await svc.add_dev("python")  # registers python-dev
    mine = (await svc.create("task", "Mine", assignee="manager")).item
    await svc.create("task", "Not mine", assignee="python-dev")

    got = await svc.list_items(assignee="manager")
    assert [i.id for i in got] == [mine.id]
