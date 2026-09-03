"""``sq inbox`` finds open `@mentions` only: it accepts the bare or `@`-prefixed slug, surfaces a
mention written inside a sub-entity's discussion exactly like a top-level one (attributing it to
the sub-entity region it matched), and excludes a mention on an item that has since reached a
terminal status — including the ADR/guide-specific terminal statuses Accepted and Published, not
just Done/Cancelled.
"""

import pytest

from _helpers import create_item

pytestmark = pytest.mark.anyio


async def test_inbox_finds_open_mentions_only(svc):
    t1 = (await create_item(svc, "task", "open one")).item
    t2 = (await create_item(svc, "task", "done one")).item
    await svc.comment(t1.id, ["@qa please verify"], as_slug="architect")
    await svc.comment(t2.id, ["@qa check this too"], as_slug="architect")
    await svc.set_status(t2.id, "InProgress")
    await svc.set_status(t2.id, "Done")  # terminal → excluded

    hits, _skipped = await svc.inbox("qa")
    ids = {hit.item.id for hit in hits}
    assert t1.id in ids
    assert t2.id not in ids
    lines = next(hit.lines for hit in hits if hit.item.id == t1.id)
    assert any("@qa" in ln.text for ln in lines)


async def test_inbox_accepts_the_at_prefix(svc):
    t = (await create_item(svc, "task", "t")).item
    await svc.comment(t.id, ["@reviewer take a look"], as_slug="operator")
    assert {hit.item.id for hit in (await svc.inbox("@reviewer"))[0]} == {t.id}


async def test_inbox_item_level_mention_carries_no_region_locator(svc):
    """An item-level mention (in the item's own discussion) is distinguishable from a
    sub-entity one by carrying no region locator at all."""
    t = (await create_item(svc, "task", "t")).item
    await svc.comment(t.id, ["@reviewer take a look"], as_slug="operator")

    hits, _skipped = await svc.inbox("reviewer")
    line = next(ln for hit in hits for ln in hit.lines if "@reviewer" in ln.text)
    assert line.region is None


@pytest.mark.parametrize(
    ("kind", "parent_type", "add", "local_id", "comment_kwarg"),
    [
        ("story", "feature", "add_story", "US1", "story"),
        ("subtask", "task", "add_subtask", "ST1", "subtask"),
        ("finding", "review", "add_finding", "F1", "finding"),
    ],
)
async def test_inbox_attributes_a_sub_entity_mention_to_its_region_across_kinds(
    svc, kind, parent_type, add, local_id, comment_kwarg
):
    """A mention inside a sub-entity's discussion is detected (as before) and now also
    attributed to the `<kind>:<local_id>:discussion#<n>` region it matched — across every
    built-in sub-entity kind, not subtasks alone."""
    parent = (await create_item(svc, parent_type, "parent")).item
    await getattr(svc, add)(parent.id, "child sub-entity")
    await svc.comment(
        parent.id, ["@qa please verify"], as_slug="manager", **{comment_kwarg: local_id}
    )

    hits, _skipped = await svc.inbox("qa")
    assert parent.id in {hit.item.id for hit in hits}
    hit = next(hit for hit in hits if hit.item.id == parent.id)
    matched = next(ln for ln in hit.lines if "@qa" in ln.text)
    assert matched.region == f"{kind}:{local_id}:discussion#1"


@pytest.mark.parametrize(
    ("item_type", "terminal_status"),
    [("decision", "Accepted"), ("guide", "Published")],
)
async def test_inbox_excludes_a_mention_once_the_item_reaches_its_terminal_status(
    svc, item_type, terminal_status
):
    item = (await create_item(svc, item_type, "Item")).item
    await svc.comment(item.id, ["@reviewer please look"], as_slug="manager")
    assert item.id in {hit.item.id for hit in (await svc.inbox("reviewer"))[0]}

    await svc.set_status(item.id, terminal_status)
    assert item.id not in {hit.item.id for hit in (await svc.inbox("reviewer"))[0]}


async def test_inbox_a_mention_in_a_sub_entitys_title_reports_once_at_its_own_region(svc):
    """A mention that only exists because a sub-entity is *titled* that way must not surface
    as an unattributed item-level hit — the frontmatter line it's stored on is machine-derived,
    never authored. It should report exactly once, attributed to the sub-entity's own heading
    (the only place the title appears in the body — the roll-up that once repeated it is a
    computed view now, never written into the file)."""
    feature = (await create_item(svc, "feature", "parent")).item
    await svc.add_story(feature.id, "@reviewer in the title")

    hits, _skipped = await svc.inbox("reviewer")
    assert {hit.item.id for hit in hits} == {feature.id}
    lines = next(hit.lines for hit in hits if hit.item.id == feature.id)
    assert len(lines) == 1
    assert lines[0].region == "story:US1"
