"""``svc.graph`` (ego-centric BFS ref traversal): depth bound, the depends-on/blocks
edge-authorship normalization (the one genuinely tricky piece — both raw ref-kind
spellings of "dependency" must render with the same edge_kind/direction regardless of
which side authored the ref), a symmetric kind keeping its own name, kind/direction
filters, cycle termination via a seen-marker, and closed-item hiding.

Also covers the undeclared-kind traversal: an edge whose kind the merged spec does not
declare must still traverse (never silently dropped) unless the caller passed an explicit
``--kind`` filter that excludes it — the two questions "was this kind requested?" and "is
this kind declared?" used to collapse onto one gate at the traversal site whenever no
``--kind`` was passed, which is what dropped the edge silently. See
``test_ref_kinds_are_declared_spec_vocabulary.py`` for the vocabulary-refusal surfaces this
does NOT touch (an explicit ``--kind`` naming an undeclared kind is still refused up front).
"""

import pytest

from _helpers import create_item
from squads._errors import SquadsError
from squads._sections import join_frontmatter, split_frontmatter

pytestmark = pytest.mark.anyio


def _plant_undeclared_ref(svc, item, target_id: str, kind: str) -> None:
    """Hand-append an edge spelled with *kind* directly onto *item*'s on-disk frontmatter,
    bypassing every validating writer (``add_ref``/``create`` both refuse an undeclared kind
    by name). This is one arrival shape for a kind the merged spec does not declare — no
    legacy fold involved: an import, a git merge, a hand edit, or an edge
    authored before a ``[selected]`` deselect dropped its kind. Callers must run
    ``svc.repair()`` afterward so the index (what ``svc.graph`` actually reads) picks up the
    hand-written file.
    """
    path = svc.paths.abspath(item.path)
    fm, body = split_frontmatter(path.read_text(encoding="utf-8"))
    fm["refs"] = [*fm.get("refs", []), f"{target_id}:{kind}"]
    path.write_text(join_frontmatter(fm, body), encoding="utf-8")


async def _chain(svc):
    """A depends-on B (edge on A); B blocks C (edge on B, so C depends on B)."""
    a = (await create_item(svc, "feature", "A")).item
    b = (await create_item(svc, "task", "B")).item
    c = (await create_item(svc, "bug", "C")).item
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
    a = (await create_item(svc, "feature", "A")).item
    b = (await create_item(svc, "task", "B")).item
    await svc.add_ref(a.id, b.id, kind="depends-on")
    root = await svc.graph(a.id, depth=1, direction="out")
    (child,) = root.children
    assert child.id == b.id
    assert child.edge_kind == "depends-on"
    assert child.direction == "out"


async def test_c_blocks_d_authored_on_c_normalizes_to_depends_on_direction_in(svc):
    """Raw 'blocks' must never appear as edge_kind — it always normalizes to depends-on."""
    c = (await create_item(svc, "task", "C")).item
    d = (await create_item(svc, "bug", "D")).item
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
    a = (await create_item(svc, "feature", "A")).item
    b = (await create_item(svc, "task", "B")).item
    c = (await create_item(svc, "task", "C")).item
    d = (await create_item(svc, "bug", "D")).item
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
    c = (await create_item(svc, "task", "C")).item
    d = (await create_item(svc, "bug", "D")).item
    await svc.add_ref(c.id, d.id, kind="blocks")  # C blocks D
    root_d = await svc.graph(d.id, depth=1, direction="in")
    c_child = next(ch for ch in root_d.children if ch.id == c.id)
    assert c_child.edge_kind == "depends-on"
    assert c_child.direction == "out"  # D depends on C

    a = (await create_item(svc, "feature", "A")).item
    b = (await create_item(svc, "task", "B")).item
    await svc.add_ref(a.id, b.id, kind="depends-on")  # A depends-on B
    root_b = await svc.graph(b.id, depth=1, direction="in")
    a_child = next(ch for ch in root_b.children if ch.id == a.id)
    assert a_child.edge_kind == "depends-on"
    assert a_child.direction == "in"  # B is required by A


async def test_a_symmetric_ref_kind_shows_its_own_name_as_the_edge_label(svc):
    a = (await create_item(svc, "feature", "A")).item
    b = (await create_item(svc, "task", "B")).item
    await svc.add_ref(a.id, b.id, kind="related")
    root = await svc.graph(a.id, depth=1, direction="both")
    b_child = next(ch for ch in root.children if ch.id == b.id)
    assert b_child.edge_kind == "related"


async def test_kind_filter_includes_only_the_requested_kinds(svc):
    a = (await create_item(svc, "feature", "A")).item
    b = (await create_item(svc, "task", "B")).item
    c = (await create_item(svc, "bug", "C")).item
    await svc.add_ref(a.id, b.id, kind="depends-on")
    await svc.add_ref(a.id, c.id, kind="related")
    root = await svc.graph(a.id, depth=1, kinds={"related"}, direction="out")
    child_ids = {ch.id for ch in root.children}
    assert c.id in child_ids
    assert b.id not in child_ids


async def test_an_unknown_kind_raises_squads_error(svc):
    a = (await create_item(svc, "feature", "A")).item
    with pytest.raises(SquadsError, match="unknown ref kind"):
        await svc.graph(a.id, kinds={"nonexistent-kind"})


async def test_direction_out_follows_only_forward_refs(svc):
    a = (await create_item(svc, "feature", "A")).item
    b = (await create_item(svc, "task", "B")).item
    c = (await create_item(svc, "bug", "C")).item
    await svc.add_ref(a.id, b.id, kind="related")
    await svc.add_ref(c.id, a.id, kind="related")
    root = await svc.graph(a.id, depth=1, direction="out")
    child_ids = {ch.id for ch in root.children}
    assert b.id in child_ids
    assert c.id not in child_ids


async def test_direction_in_follows_only_backrefs(svc):
    a = (await create_item(svc, "feature", "A")).item
    b = (await create_item(svc, "task", "B")).item
    c = (await create_item(svc, "bug", "C")).item
    await svc.add_ref(a.id, b.id, kind="related")
    await svc.add_ref(c.id, a.id, kind="related")
    root = await svc.graph(a.id, depth=1, direction="in")
    child_ids = {ch.id for ch in root.children}
    assert c.id in child_ids
    assert b.id not in child_ids


async def test_direction_both_merges_forward_refs_and_backrefs(svc):
    a = (await create_item(svc, "feature", "A")).item
    b = (await create_item(svc, "task", "B")).item
    c = (await create_item(svc, "bug", "C")).item
    await svc.add_ref(a.id, b.id, kind="related")
    await svc.add_ref(c.id, a.id, kind="related")
    root = await svc.graph(a.id, depth=1, direction="both")
    child_ids = {ch.id for ch in root.children}
    assert {b.id, c.id} <= child_ids


async def test_a_cycle_terminates_via_a_seen_marker_not_infinite_recursion(svc):
    a = (await create_item(svc, "feature", "A")).item
    b = (await create_item(svc, "task", "B")).item
    await svc.add_ref(a.id, b.id, kind="related")
    await svc.add_ref(b.id, a.id, kind="related")  # A -> B -> A
    root = await svc.graph(a.id, depth=5, direction="out")
    b_child = next(ch for ch in root.children if ch.id == b.id)
    a_revisit = next(ch for ch in b_child.children if ch.id == a.id)
    assert a_revisit.seen is True
    assert a_revisit.children == []  # not recursed into a second time


async def test_closed_items_are_hidden_by_default_and_revealed_by_include_closed(svc):
    a = (await create_item(svc, "feature", "A")).item
    b = (await create_item(svc, "task", "B")).item
    await svc.set_status(b.id, "InProgress")
    await svc.set_status(b.id, "Done")
    await svc.add_ref(a.id, b.id, kind="related")

    hidden = await svc.graph(a.id, depth=1)
    assert b.id not in {ch.id for ch in hidden.children}

    revealed = await svc.graph(a.id, depth=1, include_closed=True)
    assert b.id in {ch.id for ch in revealed.children}


# ─── undeclared-kind edges: traverse instead of vanishing ──────────────────────


async def test_an_undeclared_kind_edge_traverses_with_a_null_semantic_in_both_directions(svc):
    """The core of the defect: previously this edge simply wasn't there. Both directions,
    because ``_out_neighbours`` and ``_in_neighbours`` each had their own copy of the drop."""
    a = (await create_item(svc, "task", "A")).item
    b = (await create_item(svc, "task", "B")).item
    _plant_undeclared_ref(svc, a, b.id, "banana")
    await svc.repair()

    out_root = await svc.graph(a.id, depth=1, direction="out")
    (child,) = out_root.children
    assert child.id == b.id
    assert child.edge_kind == "banana"  # the stored spelling, unchanged
    assert child.edge_semantic is None  # no declared semantic — never grounds to drop it

    in_root = await svc.graph(b.id, depth=1, direction="in")
    (back_child,) = in_root.children
    assert back_child.id == a.id
    assert back_child.edge_kind == "banana"
    assert back_child.edge_semantic is None


async def test_kind_filter_still_gates_exactly_the_requested_kinds_declared_or_not(svc):
    """The other half of the trap: separating the drop from the filter must not touch the
    filter's own behaviour. Unfiltered sees everything (declared and undeclared alike);
    filtering to one declared kind excludes every other edge, declared or not."""
    a = (await create_item(svc, "task", "A")).item
    via_related = (await create_item(svc, "task", "via related")).item
    via_depends_on = (await create_item(svc, "task", "via depends-on")).item
    via_undeclared = (await create_item(svc, "task", "via undeclared")).item
    await svc.add_ref(a.id, via_related.id, kind="related")
    await svc.add_ref(a.id, via_depends_on.id, kind="depends-on")
    _plant_undeclared_ref(svc, await svc.get(a.id), via_undeclared.id, "banana")
    await svc.repair()

    unfiltered = await svc.graph(a.id, depth=1, direction="out")
    assert {ch.id for ch in unfiltered.children} == {
        via_related.id,
        via_depends_on.id,
        via_undeclared.id,
    }

    filtered = await svc.graph(a.id, depth=1, direction="out", kinds={"related"})
    assert {ch.id for ch in filtered.children} == {via_related.id}


async def test_undeclared_kind_edge_agrees_across_refs_and_check_after_a_default_kind_rename(
    tmp_path,
):
    """The four-surfaces regression this defect actually was: ``refs --in``/``--all`` listed
    the edge, ``sq check`` warned on it, and ``sq graph`` alone deleted it with no signal.
    Built across a default-kind rename: a pre-rename edge spelled with
    the old default kind is undeclared afterward (planted directly — no legacy fold needed to
    reach it), and a natively bare edge under the new default targets the same item. Both must
    appear identically in refs_out/refs_in/graph/check."""
    from squads import __version__
    from squads._rendering._engine import invalidate_squad_dir
    from squads._services._service import Service, init
    from squads._services._validators import ValidatorContext, _ref_kind_valid

    result = await init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    svc = Service(result.paths)
    target = (await create_item(svc, "task", "target")).item
    stale = (await create_item(svc, "task", "stale spelling")).item
    native = (await create_item(svc, "task", "native default")).item

    # Rename the default kind away from "related" (drops it from the declared vocabulary).
    override_dir = result.paths.squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n"
        '[selected]\nref_kinds = ["blocks", "depends-on", "implements", "fixes", "addresses", '
        '"supersedes", "duplicates", "scopes", "targets", "primary"]\n\n'
        '[ref_kinds.primary]\nlabel = "Primary"\nrole = "default"\n',
        encoding="utf-8",
    )
    invalidate_squad_dir(result.paths.squad_dir)
    from squads._workflow import load_workflow_spec

    svc = Service(result.paths, spec=load_workflow_spec(squad_dir=result.paths.squad_dir))
    assert "related" not in svc.spec.ref_kinds
    assert svc.spec.default_ref_kind() == "primary"

    # The stale edge: spelled with the now-undeclared old default. No legacy fold needed —
    # a hand-written spelled ref reaches the exact same state.
    _plant_undeclared_ref(svc, stale, target.id, "related")
    # The native edge: written after the rename, bare, resolving to the new default.
    await svc.add_ref(native.id, target.id)
    await svc.repair()

    refs_in = await svc.refs_in(target.id)
    assert (stale.id, "related") in refs_in
    assert (native.id, "primary") in refs_in

    refs_out_stale = await svc.refs_out(stale.id)
    assert (target.id, "related") in refs_out_stale
    refs_out_native = await svc.refs_out(native.id)
    assert (target.id, "primary") in refs_out_native

    graph_root = await svc.graph(target.id, depth=1, direction="in")
    by_id = {ch.id: ch for ch in graph_root.children}
    assert set(by_id) == {stale.id, native.id}
    assert by_id[stale.id].edge_kind == "related"
    assert by_id[stale.id].edge_semantic is None  # undeclared — no declared semantic to report

    stale_item = await svc.get(stale.id)
    issues = _ref_kind_valid(ValidatorContext(item=stale_item, spec=svc.spec))
    assert any("related" in i.message for i in issues)
    native_item = await svc.get(native.id)
    assert _ref_kind_valid(ValidatorContext(item=native_item, spec=svc.spec)) == []
