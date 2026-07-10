"""``svc.graph`` (ego-centric BFS ref traversal): depth bound, the depends-on/blocks
edge-authorship normalization (the one genuinely tricky piece — both raw ref-kind
spellings of "dependency" must render with the same edge_kind/direction regardless of
which side authored the ref), a symmetric kind keeping its own name, kind/direction
filters, cycle termination via a seen-marker, and closed-item hiding.
"""

import pytest

from squads._errors import SquadsError

pytestmark = pytest.mark.anyio


async def _chain(svc):
    """A depends-on B (edge on A); B blocks C (edge on B, so C depends on B)."""
    a = (await svc.create("feature", "A")).item
    b = (await svc.create("task", "B")).item
    c = (await svc.create("bug", "C")).item
    await svc.add_ref(a.id, b.id, kind="depends-on")
    await svc.add_ref(b.id, c.id, kind="blocks")
    return a.id, b.id, c.id


async def test_depth_zero_returns_the_root_with_no_children(svc):
    a_id, _, _ = await _chain(svc)
    root = await svc.graph(a_id, depth=0)
    assert root.id == a_id
    assert root.children == []
    assert root.seen is False


async def test_depth_one_expands_only_immediate_neighbours(svc):
    a_id, b_id, c_id = await _chain(svc)
    root = await svc.graph(a_id, depth=1, direction="both")
    child_ids = {c.id for c in root.children}
    assert b_id in child_ids
    assert c_id not in child_ids  # two hops away
    assert next(c for c in root.children if c.id == b_id).children == []


async def test_depth_two_reaches_two_hops_away(svc):
    a_id, b_id, c_id = await _chain(svc)
    root = await svc.graph(a_id, depth=2, direction="out")
    b_node = next(ch for ch in root.children if ch.id == b_id)
    assert c_id in {ch.id for ch in b_node.children}


async def test_a_depends_on_b_authored_on_a_normalizes_to_depends_on_direction_out(svc):
    a = (await svc.create("feature", "A")).item
    b = (await svc.create("task", "B")).item
    await svc.add_ref(a.id, b.id, kind="depends-on")
    root = await svc.graph(a.id, depth=1, direction="out")
    (child,) = root.children
    assert child.id == b.id
    assert child.edge_kind == "depends-on"
    assert child.direction == "out"


async def test_c_blocks_d_authored_on_c_normalizes_to_depends_on_direction_in(svc):
    """Raw 'blocks' must never appear as edge_kind — it always normalizes to depends-on."""
    c = (await svc.create("task", "C")).item
    d = (await svc.create("bug", "D")).item
    await svc.add_ref(c.id, d.id, kind="blocks")
    root = await svc.graph(c.id, depth=1, direction="out")
    (child,) = root.children
    assert child.id == d.id
    assert child.edge_kind == "depends-on"
    assert child.direction == "in"
    assert child.edge_kind != "blocks"


async def test_mixed_edge_authorship_renders_the_same_normalized_direction(svc):
    """A depends-on B (authored on A) and C blocks D (authored on C) must produce the same
    edge_kind/direction pair for their respective dependent/blocker ends — not two literal
    kinds depending on which side happened to author the ref."""
    a = (await svc.create("feature", "A")).item
    b = (await svc.create("task", "B")).item
    c = (await svc.create("task", "C")).item
    d = (await svc.create("bug", "D")).item
    await svc.add_ref(a.id, b.id, kind="depends-on")
    await svc.add_ref(c.id, d.id, kind="blocks")

    root_a = await svc.graph(a.id, depth=1, direction="out")
    b_child = next(ch for ch in root_a.children if ch.id == b.id)
    root_c = await svc.graph(c.id, depth=1, direction="out")
    d_child = next(ch for ch in root_c.children if ch.id == d.id)

    assert b_child.edge_kind == d_child.edge_kind == "depends-on"
    assert b_child.direction == "out"  # A (dependent) -> B
    assert d_child.direction == "in"  # C (blocker) -> D (the dependent)
    kinds = {ch.edge_kind for ch in root_a.children} | {ch.edge_kind for ch in root_c.children}
    assert "blocks" not in kinds


async def test_dependent_and_blocker_backref_sides_both_normalize_correctly(svc):
    """Rooted at the dependent side of a 'blocks' edge and the blocker side of a
    'depends-on' edge, the reverse-direction traversal still normalizes consistently."""
    c = (await svc.create("task", "C")).item
    d = (await svc.create("bug", "D")).item
    await svc.add_ref(c.id, d.id, kind="blocks")  # C blocks D
    root_d = await svc.graph(d.id, depth=1, direction="in")
    c_child = next(ch for ch in root_d.children if ch.id == c.id)
    assert c_child.edge_kind == "depends-on"
    assert c_child.direction == "out"  # D depends on C

    a = (await svc.create("feature", "A")).item
    b = (await svc.create("task", "B")).item
    await svc.add_ref(a.id, b.id, kind="depends-on")  # A depends-on B
    root_b = await svc.graph(b.id, depth=1, direction="in")
    a_child = next(ch for ch in root_b.children if ch.id == a.id)
    assert a_child.edge_kind == "depends-on"
    assert a_child.direction == "in"  # B is required by A


async def test_a_symmetric_ref_kind_shows_its_own_name_as_the_edge_label(svc):
    a = (await svc.create("feature", "A")).item
    b = (await svc.create("task", "B")).item
    await svc.add_ref(a.id, b.id, kind="related")
    root = await svc.graph(a.id, depth=1, direction="both")
    b_child = next(ch for ch in root.children if ch.id == b.id)
    assert b_child.edge_kind == "related"


async def test_kind_filter_includes_only_the_requested_kinds(svc):
    a = (await svc.create("feature", "A")).item
    b = (await svc.create("task", "B")).item
    c = (await svc.create("bug", "C")).item
    await svc.add_ref(a.id, b.id, kind="depends-on")
    await svc.add_ref(a.id, c.id, kind="related")
    root = await svc.graph(a.id, depth=1, kinds={"related"}, direction="out")
    child_ids = {ch.id for ch in root.children}
    assert c.id in child_ids
    assert b.id not in child_ids


async def test_an_unknown_kind_raises_squads_error(svc):
    a = (await svc.create("feature", "A")).item
    with pytest.raises(SquadsError, match="unknown ref kind"):
        await svc.graph(a.id, kinds={"nonexistent-kind"})


async def test_direction_out_follows_only_forward_refs(svc):
    a = (await svc.create("feature", "A")).item
    b = (await svc.create("task", "B")).item
    c = (await svc.create("bug", "C")).item
    await svc.add_ref(a.id, b.id, kind="related")
    await svc.add_ref(c.id, a.id, kind="related")
    root = await svc.graph(a.id, depth=1, direction="out")
    child_ids = {ch.id for ch in root.children}
    assert b.id in child_ids
    assert c.id not in child_ids


async def test_direction_in_follows_only_backrefs(svc):
    a = (await svc.create("feature", "A")).item
    b = (await svc.create("task", "B")).item
    c = (await svc.create("bug", "C")).item
    await svc.add_ref(a.id, b.id, kind="related")
    await svc.add_ref(c.id, a.id, kind="related")
    root = await svc.graph(a.id, depth=1, direction="in")
    child_ids = {ch.id for ch in root.children}
    assert c.id in child_ids
    assert b.id not in child_ids


async def test_direction_both_merges_forward_refs_and_backrefs(svc):
    a = (await svc.create("feature", "A")).item
    b = (await svc.create("task", "B")).item
    c = (await svc.create("bug", "C")).item
    await svc.add_ref(a.id, b.id, kind="related")
    await svc.add_ref(c.id, a.id, kind="related")
    root = await svc.graph(a.id, depth=1, direction="both")
    child_ids = {ch.id for ch in root.children}
    assert {b.id, c.id} <= child_ids


async def test_a_cycle_terminates_via_a_seen_marker_not_infinite_recursion(svc):
    a = (await svc.create("feature", "A")).item
    b = (await svc.create("task", "B")).item
    await svc.add_ref(a.id, b.id, kind="related")
    await svc.add_ref(b.id, a.id, kind="related")  # A -> B -> A
    root = await svc.graph(a.id, depth=5, direction="out")
    b_child = next(ch for ch in root.children if ch.id == b.id)
    a_revisit = next(ch for ch in b_child.children if ch.id == a.id)
    assert a_revisit.seen is True
    assert a_revisit.children == []  # not recursed into a second time


async def test_closed_items_are_hidden_by_default_and_revealed_by_include_closed(svc):
    a = (await svc.create("feature", "A")).item
    b = (await svc.create("task", "B")).item
    await svc.set_status(b.id, "InProgress")
    await svc.set_status(b.id, "Done")
    await svc.add_ref(a.id, b.id, kind="related")

    hidden = await svc.graph(a.id, depth=1)
    assert b.id not in {ch.id for ch in hidden.children}

    revealed = await svc.graph(a.id, depth=1, include_closed=True)
    assert b.id in {ch.id for ch in revealed.children}
