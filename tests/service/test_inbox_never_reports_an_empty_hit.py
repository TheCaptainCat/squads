"""`sq inbox` must never list an item with no lines under it.

An empty hit is not a report, it is a puzzle: the human render prints the item with nothing beneath
it and no clue what called the reader out, and a `--json` consumer that renders per line shows an
empty entry. It is what you get whenever the admission gate is *wider* than what the line scan can
emit — the gate read the whole file (frontmatter included) while the scan skipped the frontmatter
block, so a mention living only in an item's own `title` or `description` admitted the item and then
contributed nothing.

Two halves, and both are needed. The authored item-level fields are surfaced explicitly, the way
`search` already surfaces them — that recovers the real hits. And the gate is now the emit itself,
so no future frontmatter-only mention source can reintroduce the class: it either gets surfaced or
the item is left out, never listed empty.

The `:summary` and raw-frontmatter exclusions themselves are correct and are re-pinned here rather
than relaxed: a *sub-entity's* title recurs in its own heading region, so excluding the block leaves
it attributed exactly once, whereas an item's own title has no second occurrence anywhere. Treating
those two as the same thing is what created the defect.
"""

import pytest

from _helpers import create_item
from squads._sections import join_frontmatter, split_frontmatter

pytestmark = pytest.mark.anyio


async def test_no_reported_item_ever_has_zero_lines(svc):
    """The class-level invariant, over a squad carrying a mention in every placement at once. This
    is the assertion that holds no matter which surface a future mention source appears in, and the
    one the per-shape tests below are specific instances of."""
    in_title = (await create_item(svc, "task", "@reviewer look at the parser")).item
    in_desc = (
        await create_item(svc, "task", "a clean title", description="ping @reviewer about this")
    ).item
    in_body = (await create_item(svc, "task", "another clean title")).item
    await svc.set_body(in_body.id, "the body mentions @reviewer here")
    in_discussion = (await create_item(svc, "task", "a fourth")).item
    await svc.comment(in_discussion.id, ["@reviewer please look"], as_slug="manager")
    in_subentity_title = (await create_item(svc, "feature", "a feature")).item
    await svc.add_story(in_subentity_title.id, "@reviewer in the story title")

    hits, _skipped = await svc.inbox("reviewer")

    assert {hit.item.id for hit in hits} == {
        in_title.id,
        in_desc.id,
        in_body.id,
        in_discussion.id,
        in_subentity_title.id,
    }
    for hit in hits:
        assert hit.lines, f"{hit.item.id} was reported with no lines: {hit}"


async def test_a_mention_only_in_the_items_own_title_reports_the_title(svc):
    """The shape `sq create task '@reviewer …'` produces. The title lives only in the frontmatter
    block, so the line scan cannot see it — before this it admitted the item and emitted nothing."""
    item = (await create_item(svc, "task", "@reviewer fix the parser")).item

    hits, _skipped = await svc.inbox("reviewer")

    assert [hit.item.id for hit in hits] == [item.id]
    assert [(ln.text, ln.region) for ln in hits[0].lines] == [("@reviewer fix the parser", None)]


async def test_a_mention_only_in_the_items_own_description_reports_the_description(svc):
    """The damaging half: `--desc` is first-class authored input (`sq create --desc`,
    `sq update --desc`), so a human writing `--desc 'ping @qa'` is ordinary use. `region` is `None`
    because the description genuinely is item-level, not attributable to any sub-entity."""
    item = (
        await create_item(svc, "task", "a clean title", description="ping @reviewer about this")
    ).item

    hits, _skipped = await svc.inbox("reviewer")

    assert [hit.item.id for hit in hits] == [item.id]
    assert [(ln.text, ln.region) for ln in hits[0].lines] == [("ping @reviewer about this", None)]


async def test_a_mention_added_to_the_description_later_is_reported(svc):
    """Via `sq update --desc` rather than at create time — the write path differs, and the read must
    not depend on which one wrote the field."""
    item = (await create_item(svc, "task", "a clean title")).item
    await svc.update(item.id, description="now mentioning @reviewer")

    hits, _skipped = await svc.inbox("reviewer")

    assert [ln.text for hit in hits for ln in hit.lines] == ["now mentioning @reviewer"]


async def test_a_mention_in_a_label_is_reported(svc):
    """`sq update --label` is authored input too, and a label is likewise frontmatter-only. Covered
    explicitly rather than left to the residual case, so the closed set of authored item-level
    fields is stated by a test and not only by a comment."""
    item = (await create_item(svc, "task", "a clean title")).item
    await svc.update(item.id, add_labels=["@reviewer"])

    hits, _skipped = await svc.inbox("reviewer")

    assert [hit.item.id for hit in hits] == [item.id]
    assert [(ln.text, ln.region) for ln in hits[0].lines] == [("@reviewer", None)]


async def test_inbox_and_search_agree_about_the_same_authored_text(svc):
    """The two surfaces disagreeing about the same text is what made the defect visible: `search`
    found the description and `inbox` printed a blank. Pinned as a relationship between the two
    rather than two independent expectations, since that is the property that broke."""
    item = (
        await create_item(svc, "task", "a clean title", description="ping @reviewer about this")
    ).item

    inbox_ids = {hit.item.id for hit in (await svc.inbox("reviewer"))[0]}
    search_ids = {result.item.id for result in (await svc.search("@reviewer"))[0]}

    assert item.id in inbox_ids
    assert inbox_ids == search_ids


async def test_a_mention_only_in_sq_managed_metadata_is_left_out_rather_than_listed_empty(svc):
    """The residual case the emit-gate produces, pinned so the choice is deliberate and not an
    accident of ordering.

    An `@` token inside sq-managed machine metadata (here the `extra` config map) is not a mention
    anyone authored, so there is nothing to surface and the item is left out entirely. Left out —
    never listed with no lines, which is the failure mode this whole module exists to forbid.
    """
    item = (await create_item(svc, "task", "a clean title")).item
    path = svc.paths.abspath(item.path)
    fm, body = split_frontmatter(path.read_text(encoding="utf-8"))
    fm["extra"] = {"note": "handed over by @reviewer"}
    path.write_text(join_frontmatter(fm, body), encoding="utf-8")

    hits, _skipped = await svc.inbox("reviewer")

    assert hits == []


async def test_a_mention_in_a_sub_entity_title_is_still_attributed_only_to_its_own_region(svc):
    """The exclusion that is *correct*, re-pinned from the other direction: surfacing the item's own
    authored fields must not have reintroduced the duplicate/unattributed sub-entity-title hit. A
    sub-entity's title is not one of the item's own authored fields, and recurs in its own heading
    region — so it stays exactly one hit, carrying its region."""
    feature = (await create_item(svc, "feature", "a clean parent title")).item
    await svc.add_story(feature.id, "@reviewer in the story title")

    hits, _skipped = await svc.inbox("reviewer")

    assert [hit.item.id for hit in hits] == [feature.id]
    assert [(ln.text, ln.region) for ln in hits[0].lines] == [
        ("### US1 — @reviewer in the story title", "story:US1")
    ]


async def test_an_item_titled_with_a_mention_and_carrying_one_in_its_body_reports_both(svc):
    """Two lines, in file order: the authored title first, then the body line. Without this a fix
    that *replaced* the line scan with the authored fields would pass every test above."""
    item = (await create_item(svc, "task", "@reviewer fix the parser")).item
    await svc.set_body(item.id, "and @reviewer here too")

    hits, _skipped = await svc.inbox("reviewer")

    assert [(ln.text, ln.region) for ln in hits[0].lines] == [
        ("@reviewer fix the parser", None),
        ("and @reviewer here too", None),
    ]


async def test_a_terminal_item_titled_with_a_mention_is_still_excluded(svc):
    """Surfacing the authored fields must not smuggle a closed item back into the inbox: the open
    filter runs before any of this and still governs."""
    item = (await create_item(svc, "task", "@reviewer fix the parser")).item
    await svc.set_status(item.id, "InProgress")
    await svc.set_status(item.id, "Done")

    assert await svc.inbox("reviewer") == ([], [])
