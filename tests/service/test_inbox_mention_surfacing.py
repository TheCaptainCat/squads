"""``sq inbox`` finds open `@mentions` only: it accepts the bare or `@`-prefixed slug, surfaces a
mention written inside a sub-entity's discussion exactly like a top-level one, and excludes a
mention on an item that has since reached a terminal status — including the ADR/guide-specific
terminal statuses Accepted and Published, not just Done/Cancelled.
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_inbox_finds_open_mentions_only(svc):
    t1 = (await svc.create("task", "open one")).item
    t2 = (await svc.create("task", "done one")).item
    await svc.comment(t1.id, ["@qa please verify"], as_slug="architect")
    await svc.comment(t2.id, ["@qa check this too"], as_slug="architect")
    await svc.set_status(t2.id, "InProgress")
    await svc.set_status(t2.id, "Done")  # terminal → excluded

    hits = await svc.inbox("qa")
    ids = {it.id for it, _ in hits}
    assert t1.id in ids
    assert t2.id not in ids
    lines = next(lns for it, lns in hits if it.id == t1.id)
    assert any("@qa" in ln for ln in lines)


async def test_inbox_accepts_the_at_prefix(svc):
    t = (await svc.create("task", "t")).item
    await svc.comment(t.id, ["@reviewer take a look"], as_slug="operator")
    assert {i.id for i, _ in await svc.inbox("@reviewer")} == {t.id}


async def test_inbox_surfaces_a_mention_in_story_subtask_and_finding_discussion(svc):
    feat = (await svc.create("feature", "Login feature")).item
    await svc.add_story(feat.id, "Password reset")  # US1
    await svc.comment(
        feat.id, ["@qa please verify acceptance"], as_slug="product-owner", story="US1"
    )
    assert feat.id in {it.id for it, _ in await svc.inbox("qa")}

    task = (await svc.create("task", "Implement reset")).item
    await svc.add_subtask(task.id, "Wire endpoint")  # ST1
    await svc.comment(task.id, ["@reviewer look at this subtask"], as_slug="manager", subtask="ST1")
    assert task.id in {it.id for it, _ in await svc.inbox("reviewer")}

    rev = (await svc.create("review", "Code review")).item
    await svc.add_finding(rev.id, "Null deref")  # F1
    await svc.comment(rev.id, ["@qa does this fix satisfy?"], as_slug="reviewer", finding="F1")
    assert rev.id in {it.id for it, _ in await svc.inbox("qa")}


@pytest.mark.parametrize(
    ("item_type", "terminal_status"),
    [("decision", "Accepted"), ("guide", "Published")],
)
async def test_inbox_excludes_a_mention_once_the_item_reaches_its_terminal_status(
    svc, item_type, terminal_status
):
    item = (await svc.create(item_type, "Item")).item
    await svc.comment(item.id, ["@reviewer please look"], as_slug="manager")
    assert item.id in {it.id for it, _ in await svc.inbox("reviewer")}

    await svc.set_status(item.id, terminal_status)
    assert item.id not in {it.id for it, _ in await svc.inbox("reviewer")}
