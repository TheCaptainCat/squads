"""A parent chain that revisits an item is refused wherever a parent is set, and reported
wherever an existing one is read.

The parent relation is the squad's hierarchy: every consumer of it walks upward or downward
assuming the walk terminates. One always-on floor validator (``parent_acyclic``) covers all
four parent-setting entry points at once — item create, the shared update core the bulk
importer routes through, the link verb and the retype prospective all gate through the same
:class:`~squads._services._validators.ValidatorEngine` — and, because the same engine backs
``sq check``, reports a cycle that reached the corpus without passing any gate.

Three shapes are covered rather than one instance: a self-parent, a mutual pair, and a longer
chain that closes on itself. They are the same walk with a visited set, so a guard that catches
only the first leaves the identical condition reachable in two commands instead of one.

Identity in the visited set is the sequence number, never the raw id string: a stored ``parent``
may carry a different zero-pad width than the item's own ``id``, and a set of id strings walks
straight past that repeat.
"""

import json
from pathlib import Path

import pytest

from _helpers import BUILTIN_PREFIX, create_item
from squads import _sections as sections
from squads._errors import SquadsError
from squads._index._resolver import item_file
from squads._itemfile import read_frontmatter
from squads._models._item import Item

pytestmark = pytest.mark.anyio


def _edit_frontmatter(path: Path, **fields: object) -> None:
    """Rewrite frontmatter fields directly, bypassing every service seam — the only way left to
    build a cyclic corpus now that the gate refuses one, and the shape an adopted corpus or a
    hand-edited file arrives in."""
    text = path.read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    fm.update(fields)
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")


async def _seed_cycle_on_disk(svc, pairs: list[tuple[Item, str]]) -> None:
    """Write each ``(item, parent_id)`` edge into frontmatter, then rebuild the index from
    markdown so the corpus carries the cycle without any gate having seen it."""
    for item, parent_id in pairs:
        _edit_frontmatter(item_file(svc.paths, item), parent=parent_id)
    await svc.repair()


# --------------------------------------------------------------------------- the update door


async def test_an_item_cannot_be_made_its_own_parent(svc):
    bug = (await create_item(svc, "bug", "Alpha")).item
    with pytest.raises(SquadsError, match="forms a cycle"):
        await svc.update(bug.id, parent=bug.id)
    assert (await svc.get(bug.id)).parent is None


async def test_a_self_parent_is_refused_on_both_exposed_bundled_types(svc):
    """``bug`` and ``review`` are the whole set of bundled types that are category ``work``,
    declare an empty ``parents`` allowlist and inherit no ``no_parent`` — i.e. the two the
    lenient allowlist used to let through."""
    for item_type in ("bug", "review"):
        item = (await create_item(svc, item_type, f"{item_type} root")).item
        with pytest.raises(SquadsError, match="forms a cycle"):
            await svc.update(item.id, parent=item.id)


async def test_a_mutual_pair_is_refused_on_the_edge_that_closes_it(svc):
    first = (await create_item(svc, "bug", "Alpha")).item
    second = (await create_item(svc, "review", "Beta")).item
    await svc.update(first.id, parent=second.id)  # the opening edge is legitimate
    with pytest.raises(SquadsError, match="forms a cycle"):
        await svc.update(second.id, parent=first.id)
    assert (await svc.get(second.id)).parent is None


async def test_a_three_item_chain_is_refused_on_the_edge_that_closes_it(svc):
    a = (await create_item(svc, "bug", "A")).item
    b = (await create_item(svc, "review", "B")).item
    c = (await create_item(svc, "bug", "C")).item
    await svc.update(a.id, parent=b.id)
    await svc.update(b.id, parent=c.id)
    with pytest.raises(SquadsError, match="forms a cycle"):
        await svc.update(c.id, parent=a.id)
    assert (await svc.get(c.id)).parent is None


async def test_the_refusal_names_the_whole_chain_and_the_command_that_breaks_it(svc):
    first = (await create_item(svc, "bug", "Alpha")).item
    second = (await create_item(svc, "review", "Beta")).item
    await svc.update(first.id, parent=second.id)
    with pytest.raises(SquadsError) as excinfo:
        await svc.update(second.id, parent=first.id)
    message = str(excinfo.value)
    # Both endpoints of the loop, in walk order, with the revisited item at both ends.
    assert f"{second.id} -> {first.id} -> {second.id}" in message
    # The remedy clears the parent of the item whose own edge closes the loop.
    assert f"sq {first.type} {first.sequence_id} update --no-parent" in message


# --------------------------------------------------------------------------- the other doors


async def test_create_with_a_parent_that_would_close_a_cycle_is_refused(svc):
    """A brand-new item cannot be born into a cycle: its declared parent's chain is walked the
    same way. The pre-existing cycle is seeded on disk, since no gate would admit one."""
    a = (await create_item(svc, "bug", "A")).item
    b = (await create_item(svc, "review", "B")).item
    await _seed_cycle_on_disk(svc, [(a, b.id), (b, a.id)])
    with pytest.raises(SquadsError, match="forms a cycle"):
        await create_item(svc, "bug", "newcomer", parent=a.id)


async def test_the_link_verb_refuses_a_cycle(svc):
    first = (await create_item(svc, "bug", "Alpha")).item
    second = (await create_item(svc, "review", "Beta")).item
    await svc.link(first.id, second.id)
    with pytest.raises(SquadsError, match="forms a cycle"):
        await svc.link(second.id, first.id)
    assert (await svc.get(second.id)).parent is None


async def test_the_retype_prospective_refuses_an_item_sitting_in_a_cycle(svc):
    a = (await create_item(svc, "bug", "A")).item
    b = (await create_item(svc, "review", "B")).item
    await _seed_cycle_on_disk(svc, [(a, b.id), (b, a.id)])
    with pytest.raises(SquadsError, match="forms a cycle"):
        await svc.retype(a.id, "review")


async def test_the_bulk_importer_refuses_an_event_stream_that_closes_a_cycle(svc):
    """The importer routes its update events through the same shared update core, so the one
    floor member covers it too: its validate-first pre-pass reports the closing edge as an
    issue and the whole stream is left unapplied — neither edge is written."""
    first = (await create_item(svc, "bug", "Alpha")).item
    second = (await create_item(svc, "review", "Beta")).item
    text = "\n".join(
        json.dumps(e)
        for e in (
            {"op": "update", "target": first.id, "parent": second.id, "as": "manager"},
            {"op": "update", "target": second.id, "parent": first.id, "as": "manager"},
        )
    )
    result = await svc.import_events(text)
    assert not result.plan.ok
    assert any("forms a cycle" in i.message for i in result.plan.issues)
    assert result.applied is None
    assert (await svc.get(first.id)).parent is None
    assert (await svc.get(second.id)).parent is None


# --------------------------------------------------------------------------- identity by number


async def test_a_cycle_stored_at_a_different_padding_width_is_still_caught(svc):
    """The stored ``parent`` string carries a zero-pad width the items' own ids do not — the
    state a repad leaves behind. Identity keyed on the id string compares the two spellings of
    the same item, finds no repeat, and walks forever."""
    a = (await create_item(svc, "bug", "A")).item
    b = (await create_item(svc, "review", "B")).item
    repadded = f"{b.prefix}-{b.sequence_id:09d}"
    assert repadded != b.id, "the fixture must actually differ in width from the canonical id"
    await _seed_cycle_on_disk(svc, [(a, repadded), (b, a.id)])
    issues = await svc.check()
    cycles = [i for i in issues if "forms a cycle" in i.message]
    assert {i.item for i in cycles} == {a.id, b.id}


# --------------------------------------------------------------------------- report + recovery


async def test_check_reports_an_existing_cycle_naming_both_endpoints(svc):
    a = (await create_item(svc, "bug", "A")).item
    b = (await create_item(svc, "review", "B")).item
    await _seed_cycle_on_disk(svc, [(a, b.id), (b, a.id)])
    issues = await svc.check()
    cycles = [i for i in issues if "forms a cycle" in i.message]
    assert {i.item for i in cycles} == {a.id, b.id}
    assert all(i.level == "error" for i in cycles)
    for issue in cycles:
        assert a.id in issue.message and b.id in issue.message


async def test_repair_reports_a_cycle_without_rearranging_the_hierarchy(svc):
    """Breaking a cycle means choosing which edge to drop — a judgement about someone's
    hierarchy, not a mechanical rewrite. ``repair`` therefore leaves both edges exactly as it
    found them."""
    a = (await create_item(svc, "bug", "A")).item
    b = (await create_item(svc, "review", "B")).item
    await _seed_cycle_on_disk(svc, [(a, b.id), (b, a.id)])
    await svc.repair()  # a second pass: converges, does not touch the edges
    assert (await svc.get(a.id)).parent == b.id
    assert (await svc.get(b.id)).parent == a.id


async def test_an_item_inside_a_cycle_is_not_updatable_until_the_cycle_is_broken(svc):
    """Deliberate fail-closed consequence of floor placement: the refusal is about the item's
    parent chain, so it lands on a status change too."""
    a = (await create_item(svc, "bug", "A")).item
    b = (await create_item(svc, "review", "B")).item
    await _seed_cycle_on_disk(svc, [(a, b.id), (b, a.id)])
    with pytest.raises(SquadsError, match="forms a cycle"):
        await svc.update(a.id, status="InProgress")


async def test_clearing_the_parent_still_succeeds_on_an_item_inside_a_cycle(svc):
    """The recovery path the refusal message names. It works because ``clear_parent`` nulls
    ``item.parent`` before the gate reads it — without that, the fail-closed refusal above
    would be unrecoverable."""
    a = (await create_item(svc, "bug", "A")).item
    b = (await create_item(svc, "review", "B")).item
    await _seed_cycle_on_disk(svc, [(a, b.id), (b, a.id)])
    cleared = await svc.update(a.id, clear_parent=True)
    assert cleared.parent is None
    assert not [i for i in await svc.check() if "forms a cycle" in i.message]
    # And the item is updatable again once the loop is gone.
    assert (await svc.update(a.id, status="InProgress")).status == "InProgress"


# --------------------------------------------------------------------------- non-findings


async def test_a_dangling_parent_is_reported_once_by_the_eligibility_rule(svc):
    """A parent that resolves to nothing stops the ancestor walk rather than being re-reported
    as a cycle, so a single broken edge stays a single finding."""
    a = (await create_item(svc, "bug", "A")).item
    await _seed_cycle_on_disk(svc, [(a, "BUG-999999")])
    messages = [i.message for i in await svc.check() if i.item == a.id]
    assert any("dangling parent" in m for m in messages)
    assert not [m for m in messages if "forms a cycle" in m]


async def test_an_ordinary_hierarchy_is_untouched(svc):
    epic = (await create_item(svc, "epic", "Epic")).item
    feat = (await create_item(svc, "feature", "Feature", parent=epic.id)).item
    task = (await create_item(svc, "task", "Task", parent=feat.id)).item
    assert (await svc.get(task.id)).parent == feat.id
    assert not [i for i in await svc.check() if "forms a cycle" in i.message]


# --------------------------------------------------------- the shared status-transition core


async def test_the_status_shortcut_refuses_an_item_inside_a_cycle(svc):
    """``set_status`` backs the ``status`` verb, which documents itself as a shortcut for
    ``update --status``. It is a mutation path of its own, so the gate has to live on the
    transition core rather than on the update seam or the two verbs disagree."""
    a = (await create_item(svc, "bug", "A")).item
    b = (await create_item(svc, "review", "B")).item
    await _seed_cycle_on_disk(svc, [(a, b.id), (b, a.id)])
    before = (await svc.get(a.id)).status
    with pytest.raises(SquadsError, match="forms a cycle"):
        await svc.set_status(a.id, "InProgress")
    assert (await svc.get(a.id)).status == before


async def test_force_does_not_carry_the_status_shortcut_past_the_gate(svc):
    """``force`` overrides the lifecycle's own transition edge, never the catalog."""
    a = (await create_item(svc, "bug", "A")).item
    b = (await create_item(svc, "review", "B")).item
    await _seed_cycle_on_disk(svc, [(a, b.id), (b, a.id)])
    with pytest.raises(SquadsError, match="forms a cycle"):
        await svc.set_status(a.id, "InProgress", force=True)


async def test_the_roster_status_entry_point_refuses_an_item_inside_a_cycle(svc):
    """The roster status axis is unreachable through ``update`` by design, so its own entry
    point is the only door onto it — and it shares the same transition core."""
    entry = await svc.add_operator("Reviewer Of Record", slug="rec")
    await _seed_cycle_on_disk(svc, [(entry, entry.id)])
    with pytest.raises(SquadsError, match="forms a cycle"):
        await svc.set_roster_status(entry.id, "Archived")


async def test_the_status_shortcut_is_reopened_by_clearing_the_closing_edge(svc):
    """The recovery route is not blocked by the new refusal: ``clear_parent`` never runs
    through the transition core, so the way out of a cycle stays open."""
    a = (await create_item(svc, "bug", "A")).item
    b = (await create_item(svc, "review", "B")).item
    await _seed_cycle_on_disk(svc, [(a, b.id), (b, a.id)])
    await svc.update(b.id, clear_parent=True)
    assert (await svc.set_status(a.id, "InProgress")).status == "InProgress"


# ------------------------------------------------ naming both ends when the head is restyled


async def test_a_reclassification_names_both_ends_of_the_loop_as_the_one_item(svc):
    """A retype gates the item as it *would* look, so the chain's head carries a prospective id
    while the index still spells the same item the old way. Printed as-is, the one loop reads as
    two different items — the endpoint is therefore named as the head, with the stored spelling
    alongside."""
    a = (await create_item(svc, "bug", "A")).item
    b = (await create_item(svc, "review", "B")).item
    await _seed_cycle_on_disk(svc, [(a, b.id), (b, a.id)])
    prospective = f"{BUILTIN_PREFIX['review']}-{a.sequence_id}"

    with pytest.raises(SquadsError) as excinfo:
        await svc.retype(a.id, "review")

    message = str(excinfo.value)
    assert f"{prospective} -> {b.id} -> {prospective} (stored as {a.id})" in message
    # The remedy is untouched: it still clears the parent of the item whose edge closes the loop.
    assert f"sq {b.type} {b.sequence_id} update --no-parent" in message


async def test_an_ordinary_refusal_carries_no_stored_as_aside(svc):
    """The aside is specific to a head under a prospective id — every other refusal, where the
    endpoint already spells itself the way the index does, reads exactly as it did."""
    first = (await create_item(svc, "bug", "Alpha")).item
    second = (await create_item(svc, "review", "Beta")).item
    await svc.update(first.id, parent=second.id)
    with pytest.raises(SquadsError) as excinfo:
        await svc.update(second.id, parent=first.id)
    assert "stored as" not in str(excinfo.value)
