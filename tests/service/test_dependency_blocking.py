"""``sq blocked``: the two ref-kind spellings (``blocks``/``depends-on``) produce the identical
(blocked, [blockers]) pair, an item blocked through both spellings at once still appears exactly
once with the union of its blockers, and a closed blocker no longer counts. Also pins a design
distinction that was never directly asserted before: an item's own ``Ready`` status and the
``depends-on`` blocked-state are orthogonal axes — an item can be Ready (its own prose is done)
while still blocked (something else it depends on isn't).
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_depends_on_and_blocks_are_equivalent_spellings(svc):
    blocker = (await svc.create("task", "blocker")).item
    dependent = (await svc.create("task", "dependent")).item

    await svc.add_ref(dependent.id, blocker.id, kind="depends-on")

    pairs = await svc.blocked()
    assert len(pairs) == 1
    blocked_item, blockers = pairs[0]
    assert blocked_item.id == dependent.id
    assert [b.id for b in blockers] == [blocker.id]


async def test_an_item_blocked_via_both_edge_spellings_appears_once_with_the_union(svc):
    blocker_a = (await svc.create("task", "blocker-a")).item
    blocker_b = (await svc.create("task", "blocker-b")).item
    dependent = (await svc.create("task", "dependent")).item

    await svc.add_ref(blocker_a.id, dependent.id, kind="blocks")
    await svc.add_ref(dependent.id, blocker_b.id, kind="depends-on")

    pairs = await svc.blocked()
    assert len(pairs) == 1
    blocked_item, blockers = pairs[0]
    assert blocked_item.id == dependent.id
    assert {b.id for b in blockers} == {blocker_a.id, blocker_b.id}


async def test_a_closed_blocker_no_longer_counts(svc):
    blocker = (await svc.create("task", "blocker")).item
    dependent = (await svc.create("task", "dependent")).item
    await svc.add_ref(dependent.id, blocker.id, kind="depends-on")

    await svc.set_status(blocker.id, "InProgress")
    await svc.set_status(blocker.id, "Done")
    assert await svc.blocked() == []


async def test_an_item_can_be_ready_and_blocked_at_the_same_time(svc):
    """Ready-ness is about the item's OWN prose being done; blocked-ness is about a
    still-open dependency. The two facts hold on the same item simultaneously — orthogonal
    axes, not a state machine where one implies the other."""
    blocker = (await svc.create("task", "still open")).item
    dependent = (await svc.create("task", "prose is done")).item
    await svc.add_ref(dependent.id, blocker.id, kind="depends-on")

    await svc.set_status(dependent.id, "Ready")  # own status: Ready
    assert (await svc.get(dependent.id)).status == "Ready"

    blocked_ids = {it.id for it, _ in await svc.blocked()}
    assert dependent.id in blocked_ids  # still blocked by the still-open blocker
