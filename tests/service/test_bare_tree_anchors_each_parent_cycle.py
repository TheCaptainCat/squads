"""A bare tree anchors each parent cycle instead of dropping the whole component.

The forest a bare tree roots at is "every item with no resolvable parent in view". Every member
of a parent cycle has a resolvable parent — another member — so the component, and everything
hanging below it, was absent from the bare tree at exit 0 while ``list`` still returned it.
Nothing on the surface said so. A component is now rooted at one of its own cycle members and
renders from there, truncated at the repeat, exactly as a tree rooted inside the cycle already
did.

The anchor is chosen from the items **on** the cycle, lowest sequence first — not from "the
lowest item not rendered yet". The two rules agree on most corpora and differ where it hurts,
which is why every fixture here hangs an item *below* the cycle carrying a lower sequence number
than any member: the second rule anchors that item at itself and then renders it a second time
as a child when the descent reaches it through the cycle. Every assertion therefore counts
occurrences per id rather than testing presence — a presence test passes with the wrong rule in.

The corpus is staged by writing frontmatter and re-indexing, because the write door refuses a
cycle. That is the shape an adopted corpus, a hand-edited file, or a squad poisoned before the
gate existed arrives in.
"""

from collections import Counter

import pytest

from _helpers import create_item
from squads import _sections as sections
from squads._index._resolver import item_file
from squads._itemfile import read_frontmatter
from squads._models._item import Item
from squads._services._base import ItemFilter

pytestmark = pytest.mark.anyio


def _set_parent_in_frontmatter(paths, item, parent_id: str, *, width: int) -> None:
    """Point *item* at *parent_id*, written at a chosen zero-pad width.

    The widths are mixed across every fixture on purpose: a stored parent may carry a different
    pad width than the item's own id (the state ``sq migrate repad`` leaves behind), and any
    resolution comparing id strings walks straight past the repeat.
    """
    path = item_file(paths, item)
    text = path.read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    prefix, _, number = parent_id.rpartition("-")
    fm["parent"] = f"{prefix}-{int(number):0{width}d}"
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")


def _rendered_ids(nodes) -> list[str]:
    """Every id in the rendering, in full, with repeats kept."""
    out: list[str] = []
    for n in nodes:
        out.append(n.item.id)
        out.extend(_rendered_ids(n.children))
    return out


def _anchor_ids(nodes) -> list[str]:
    """Anchored ids anywhere in the rendering — not only at the roots, so a flag leaking onto a
    descendant is caught rather than assumed away."""
    out: list[str] = []
    for n in nodes:
        if n.anchor:
            out.append(n.item.id)
        out.extend(_anchor_ids(n.children))
    return out


async def _ring(svc, size: int, label: str) -> list[Item]:
    """*size* items whose parents close a loop, indexed by a rebuild."""
    members = [(await create_item(svc, "bug", f"{label} {n}")).item for n in range(size)]
    for index, member in enumerate(members):
        _set_parent_in_frontmatter(
            svc.paths,
            member,
            members[(index + 1) % size].id,
            width=6 if index % 2 else 9,
        )
    return members


async def _poisoned_squad(svc):
    """The driven shape: an item below the cycle carrying the lowest sequence of all, a
    five-item cycle, and one ordinary item outside the component."""
    below = (await create_item(svc, "bug", "Hangs below the cycle")).item
    ring = await _ring(svc, 5, "Ring")
    unrelated = (await create_item(svc, "epic", "Unrelated")).item
    _set_parent_in_frontmatter(svc.paths, below, ring[2].id, width=9)
    await svc.repair()
    assert below.sequence_id < min(m.sequence_id for m in ring), (
        "the fixture must hang a lower-sequence item below the cycle, or the two candidate "
        "anchor rules are indistinguishable here"
    )
    return below, ring, unrelated


async def test_the_whole_cyclic_component_renders_once_from_the_bare_tree(svc):
    below, ring, unrelated = await _poisoned_squad(svc)
    rendered = _rendered_ids(await svc.tree_view())
    assert {below.id, unrelated.id} | {m.id for m in ring} <= set(rendered)
    repeated = [item_id for item_id, count in Counter(rendered).items() if count > 1]
    assert repeated == [], f"rendered more than once: {repeated}"


async def test_the_anchor_is_the_lowest_sequence_on_the_cycle_not_the_lowest_item_below_it(svc):
    """The rule that separates the two candidate anchor rules.

    ``below`` has the lowest sequence number in the whole component and is not on the cycle.
    Anchoring at "the lowest item not rendered yet" picks it; anchoring at "the lowest item that
    closes the loop" picks the first ring member. Only the second keeps every item at one place
    in the tree.
    """
    below, ring, _unrelated = await _poisoned_squad(svc)
    nodes = await svc.tree_view()
    assert _anchor_ids(nodes) == [min(ring, key=lambda m: m.sequence_id).id]
    assert below.id not in _anchor_ids(nodes)


async def test_two_disjoint_cycles_each_get_their_own_anchor(svc):
    first = await _ring(svc, 2, "First")
    second = await _ring(svc, 3, "Second")
    await svc.repair()
    nodes = await svc.tree_view()
    rendered = _rendered_ids(nodes)
    assert sorted(_anchor_ids(nodes)) == sorted(
        [min(ring, key=lambda m: m.sequence_id).id for ring in (first, second)]
    )
    assert {m.id for m in first + second} <= set(rendered)
    assert max(Counter(rendered).values()) == 1


async def test_a_corpus_with_no_cycle_keeps_exactly_the_roots_it_had(svc):
    """The change is in the root computation, which every tree call goes through — so the
    corpora that have no cycle at all are the regression that matters most."""
    epic = (await create_item(svc, "epic", "Epic")).item
    feat = (await create_item(svc, "feature", "Feature", parent=epic.id)).item
    await create_item(svc, "task", "Task", parent=feat.id)
    standalone = (await create_item(svc, "bug", "Standalone")).item
    nodes = await svc.tree_view()
    assert {epic.id, standalone.id} <= {n.item.id for n in nodes}
    assert feat.id not in {n.item.id for n in nodes}  # still a child, not promoted to a root
    assert _anchor_ids(nodes) == []


async def test_an_anchor_kept_only_as_an_ancestor_is_both_path_only_and_an_anchor(svc):
    """Under a filter matching something below the cycle the members enter the keep set as
    ancestors, so the anchor is a path-only node as well. The two are independent states that
    combine — a renderer treating them as alternatives loses one of them."""
    below, ring, _unrelated = await _poisoned_squad(svc)
    nodes = await svc.tree_view(filter=ItemFilter(assignee="manager"))
    assert _rendered_ids(nodes) == [], "fixture check: nothing is assigned yet"

    path = item_file(svc.paths, below)
    text = path.read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    fm["assignee"] = "manager"
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")
    await svc.repair()

    nodes = await svc.tree_view(filter=ItemFilter(assignee="manager"))
    root = next(n for n in nodes if n.item.id == min(ring, key=lambda m: m.sequence_id).id)
    assert root.anchor and root.path_only
    assert below.id in _rendered_ids(nodes)


async def test_a_cycle_the_filter_has_already_broken_is_not_anchored(svc):
    """Detection runs on the candidate set, not the index.

    Hide one member behind the default visibility gate and the survivors are an ordinary chain
    whose top already has no resolvable parent in view, already becomes a root and already
    renders. Detecting against the index would invent an anchor for a component that is not
    broken — and could name one that is not in the view at all.
    """
    ring = await _ring(svc, 3, "Ring")
    hidden, *survivors = ring
    path = item_file(svc.paths, hidden)
    text = path.read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    fm["status"] = "Verified"
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")
    await svc.repair()
    assert svc.spec.hidden_by_default("bug", "Verified"), "fixture check: the member must drop"

    nodes = await svc.tree_view()
    assert _anchor_ids(nodes) == []
    assert {m.id for m in survivors} <= set(_rendered_ids(nodes))
    # …and with the member back in view the cycle is a cycle again.
    assert _anchor_ids(await svc.tree_view(include_closed=True)) == [
        min(ring, key=lambda m: m.sequence_id).id
    ]


async def test_an_explicitly_rooted_tree_marks_nothing(svc):
    """Rooting inside a cycle is the caller's own choice of root, not a fabrication, and it
    rendered the component correctly before this change. Nothing there is marked."""
    _below, ring, _unrelated = await _poisoned_squad(svc)
    nodes = await svc.tree_view(ring[3].id)
    assert _anchor_ids(nodes) == []
    assert {m.id for m in ring} <= set(_rendered_ids(nodes))


async def test_the_bare_tree_covers_the_list_at_equal_filters(svc):
    """Coverage, asserted on id sets rather than counts — a count matches by accident, and this
    fixture is small enough that it would. Scoped to the no-depth case: a depth bound
    legitimately makes the tree a subset of the list, which is existing, correct behaviour.

    ``list_items`` applies no visibility gate of its own (that lives at the CLI edge, where the
    equal-filters pairing is asserted end to end), so the tree it is measured against is the one
    holding every candidate.
    """
    await _poisoned_squad(svc)
    listed = {i.id for i in await svc.list_items()}
    rendered = set(_rendered_ids(await svc.tree_view(include_closed=True)))
    assert listed <= rendered, f"missing from the tree: {sorted(listed - rendered)}"
    # …and a depth bound may legitimately drop items: the invariant is the no-depth one.
    assert set(_rendered_ids(await svc.tree_view(include_closed=True, depth=0))) <= rendered


async def test_the_bare_tree_renders_every_item_a_targeted_tree_renders(svc):
    """Bare equals the union of the targeted trees, on existence. The two forms may differ in
    scope — which subtree you asked about — never in whether an item exists at all."""
    await _poisoned_squad(svc)
    bare = set(_rendered_ids(await svc.tree_view(include_closed=True)))
    for item in await svc.list_items():
        targeted = _rendered_ids(await svc.tree_view(item.id, include_closed=True))
        assert item.id in targeted, f"{item.id} is missing from its own targeted tree"
        assert item.id in bare, f"{item.id} renders when rooted at, but not from the bare tree"
