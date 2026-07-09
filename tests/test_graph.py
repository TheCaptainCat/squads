"""Tests for ``sq graph``: service traversal + CLI edge (TASK-000182 / FEAT-000037).

Coverage:
- Service: BFS depth bound; kind filter; direction filter (out/in/both);
  depends-on/blocks mixed-authorship normalization (the same dependency arrow regardless
  of which side authored the edge); cycle termination with seen=True; closed items
  hidden vs --all.
- CLI smoke: ``sq graph <id>`` renders; bare-number resolution; ``--json`` shape golden;
  ``--format dot``; ``--format mermaid``; ``--kind``; ``--direction``; ``--depth 0``; ``--all``.
"""

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from squads._cli import app
from squads._services._refs import graph_to_dot, graph_to_mermaid
from squads._services._results import GraphNode

pytestmark = pytest.mark.anyio

GOLDENS_DIR = Path(__file__).parent / "goldens"
_UPDATE = os.getenv("UPDATE_GOLDENS") == "1"


# ---------------------------------------------------------------------------
# Golden helper (same pattern as test_golden_json.py)
# ---------------------------------------------------------------------------


def _check_golden(name: str, actual_data: object) -> None:
    path = GOLDENS_DIR / f"{name}.json"
    if _UPDATE:
        GOLDENS_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(actual_data, indent=2) + "\n", encoding="utf-8")
        return
    assert path.exists(), (
        f"Golden file missing: {path}\n"
        f"Run UPDATE_GOLDENS=1 uv run pytest tests/test_graph.py to generate it."
    )
    expected = json.loads(path.read_text(encoding="utf-8"))
    assert actual_data == expected, (
        f"Golden mismatch for {name!r}.\n"
        f"Regenerate with: UPDATE_GOLDENS=1 uv run pytest tests/test_graph.py -v"
    )


# ---------------------------------------------------------------------------
# Service-layer fixtures
# ---------------------------------------------------------------------------


async def _make_chain(svc, frozen_time):
    """A → depends-on → B → blocks → C.

    A depends on B (edge on A), B blocks C (C depends on B — edge on B).
    IDs: FEAT-000002 (A), TASK-000003 (B), BUG-000004 (C).
    Returns (A.id, B.id, C.id).
    """
    a = (await svc.create("feature", "A")).item
    b = (await svc.create("task", "B")).item
    c = (await svc.create("bug", "C")).item
    await svc.add_ref(a.id, b.id, kind="depends-on")  # A depends-on B
    await svc.add_ref(b.id, c.id, kind="blocks")  # B blocks C  (C depends on B)
    return a.id, b.id, c.id


# ---------------------------------------------------------------------------
# Service tests: BFS depth bound
# ---------------------------------------------------------------------------


async def test_graph_depth_zero_returns_root_only(svc):
    """depth=0 returns the root with no children."""
    a_id, _, __ = await _make_chain(svc, None)
    root = await svc.graph(a_id, depth=0)
    assert root.id == a_id
    assert root.children == []
    assert root.edge_kind is None
    assert root.seen is False


async def test_graph_depth_one_returns_one_hop(svc):
    """depth=1 expands only the immediate neighbours of the root."""
    a_id, b_id, c_id = await _make_chain(svc, None)
    # From A: out-ref B; in: nothing. Direction=both.
    root = await svc.graph(a_id, depth=1, direction="both")
    child_ids = {c.id for c in root.children}
    assert b_id in child_ids
    assert c_id not in child_ids  # two hops away from A
    # B's children should be empty at depth=1
    b_node = next(c for c in root.children if c.id == b_id)
    assert b_node.children == []


async def test_graph_depth_two_reaches_two_hops(svc):
    """depth=2 (default) reaches nodes two hops away."""
    a_id, b_id, c_id = await _make_chain(svc, None)
    root = await svc.graph(a_id, depth=2, direction="out")
    # A → B → (B blocks C, so C is reached via in-direction from B — but we're direction=out)
    # A out-ref: B (depends-on)
    # B out-ref: C (blocks) — included because direction=out on the ctx; we expand B's out-refs
    b_node = next((ch for ch in root.children if ch.id == b_id), None)
    assert b_node is not None
    # C is reachable from B as an out-ref (B blocks C)
    c_ids_under_b = {ch.id for ch in b_node.children}
    assert c_id in c_ids_under_b


# ---------------------------------------------------------------------------
# Service tests: depends-on / blocks normalization (THE CRITICAL REQUIREMENT)
# ---------------------------------------------------------------------------


async def test_depends_on_edge_authored_on_dependent_normalizes_to_depends_on_out(svc):
    """A depends-on B (edge authored on A): child B has edge_kind='depends-on', direction='out'.

    This means the expanding node A depends on child B.
    Display label: 'depends on'.
    """
    a = (await svc.create("feature", "A")).item
    b = (await svc.create("task", "B")).item
    await svc.add_ref(a.id, b.id, kind="depends-on")

    root = await svc.graph(a.id, depth=1, direction="out")
    assert len(root.children) == 1
    child = root.children[0]
    assert child.id == b.id
    assert child.edge_kind == "depends-on"
    assert child.direction == "out"


async def test_blocks_edge_authored_on_blocker_normalizes_to_depends_on_in(svc):
    """C blocks D (authored on C): child D has edge_kind='depends-on', direction='in'.

    D depends on C = C is required by D.  Raw 'blocks' must not appear as edge_kind.
    """
    c = (await svc.create("task", "C")).item
    d = (await svc.create("bug", "D")).item
    await svc.add_ref(c.id, d.id, kind="blocks")  # C blocks D

    root = await svc.graph(c.id, depth=1, direction="out")
    assert len(root.children) == 1
    child = root.children[0]
    assert child.id == d.id
    # Normalization: raw 'blocks' becomes 'depends-on' + direction='in'
    assert child.edge_kind == "depends-on"
    assert child.direction == "in"
    # The raw kind string 'blocks' must never appear as edge_kind
    assert child.edge_kind != "blocks"


async def test_mixed_authorship_renders_same_direction(svc):
    """A depends-on B (authored on A) and C blocks D (authored on C) must render with
    the same edge_kind/direction pair for the DEPENDENT end and for the BLOCKER end.

    This is the key mixed-authorship fixture the acceptance criteria require.
    Verified: both the 'depends-on' and 'blocks' spellings produce the same
    normalized labels, not two distinct literal kinds.
    """
    a = (await svc.create("feature", "A")).item
    b = (await svc.create("task", "B")).item
    c = (await svc.create("task", "C")).item
    d = (await svc.create("bug", "D")).item

    await svc.add_ref(a.id, b.id, kind="depends-on")  # A depends-on B: edge on A
    await svc.add_ref(c.id, d.id, kind="blocks")  # C blocks D: edge on C

    # From A (the dependent): child B has edge_kind='depends-on', direction='out'
    root_a = await svc.graph(a.id, depth=1, direction="out")
    b_child = next(ch for ch in root_a.children if ch.id == b.id)

    # From C (the blocker): child D has edge_kind='depends-on', direction='in'
    root_c = await svc.graph(c.id, depth=1, direction="out")
    d_child = next(ch for ch in root_c.children if ch.id == d.id)

    # Both MUST normalize to depends-on (not 'blocks')
    assert b_child.edge_kind == "depends-on", "depends-on edge must stay 'depends-on'"
    assert d_child.edge_kind == "depends-on", "blocks edge must normalize to 'depends-on'"

    # The DEPENDENT end (A→B and D→C via backref) shows direction='out'
    assert b_child.direction == "out"

    # The BLOCKER end (C blocks D, so D is the dependent = direction='in' from C's view)
    assert d_child.direction == "in"

    # Raw kind 'blocks' must not appear anywhere
    a_kinds = {ch.edge_kind for ch in root_a.children}
    c_kinds = {ch.edge_kind for ch in root_c.children}
    assert "blocks" not in a_kinds | c_kinds, "raw 'blocks' must never appear as edge_kind"


async def test_blocks_backref_from_dependent_side(svc):
    """C blocks D (edge on C). Rooted at D, C appears as direction='out' (D depends on C).

    From D's in-direction: child C has edge_kind='depends-on', direction='out'.
    """
    c = (await svc.create("task", "C")).item
    d = (await svc.create("bug", "D")).item
    await svc.add_ref(c.id, d.id, kind="blocks")  # C blocks D

    # From D (the dependent): C should appear as 'depends on' (D depends on C)
    root_d = await svc.graph(d.id, depth=1, direction="in")
    # C has an out-ref to D via blocks; from D's in-direction, C is found
    c_child = next((ch for ch in root_d.children if ch.id == c.id), None)
    assert c_child is not None
    assert c_child.edge_kind == "depends-on"
    assert c_child.direction == "out"  # D depends on C → 'depends on'


async def test_depends_on_backref_from_blocker_side(svc):
    """A depends-on B (edge on A). Rooted at B, A appears as direction='in' (B required by A).

    From B's in-direction: child A has edge_kind='depends-on', direction='in'.
    """
    a = (await svc.create("feature", "A")).item
    b = (await svc.create("task", "B")).item
    await svc.add_ref(a.id, b.id, kind="depends-on")  # A depends-on B

    root_b = await svc.graph(b.id, depth=1, direction="in")
    a_child = next((ch for ch in root_b.children if ch.id == a.id), None)
    assert a_child is not None
    assert a_child.edge_kind == "depends-on"
    assert a_child.direction == "in"  # B required by A → 'required by'


# ---------------------------------------------------------------------------
# Service tests: symmetric kinds show kind name
# ---------------------------------------------------------------------------


async def test_symmetric_kind_shows_kind_name_as_edge_kind(svc):
    """A 'related' edge stores edge_kind='related' (not 'depends-on', not 'in'/'out' raw)."""
    a = (await svc.create("feature", "A")).item
    b = (await svc.create("task", "B")).item
    await svc.add_ref(a.id, b.id, kind="related")

    root = await svc.graph(a.id, depth=1, direction="both")
    b_child = next(ch for ch in root.children if ch.id == b.id)
    assert b_child.edge_kind == "related"
    # Direction records traversal direction, not a raw "in"/"out" label
    assert b_child.direction in ("out", "in")


# ---------------------------------------------------------------------------
# Service tests: kind filter
# ---------------------------------------------------------------------------


async def test_kind_filter_includes_only_requested_kinds(svc):
    """--kind filters to only the specified ref kinds."""
    a = (await svc.create("feature", "A")).item
    b = (await svc.create("task", "B")).item
    c = (await svc.create("bug", "C")).item
    await svc.add_ref(a.id, b.id, kind="depends-on")
    await svc.add_ref(a.id, c.id, kind="related")

    # Only follow 'related'; B should not appear
    root = await svc.graph(a.id, depth=1, kinds={"related"}, direction="out")
    child_ids = {ch.id for ch in root.children}
    assert c.id in child_ids
    assert b.id not in child_ids


async def test_unknown_kind_raises_squads_error(svc):
    """Passing an unrecognized kind raises SquadsError."""
    from squads._errors import SquadsError

    a = (await svc.create("feature", "A")).item
    with pytest.raises(SquadsError, match="unknown ref kind"):
        await svc.graph(a.id, kinds={"nonexistent-kind"})


# ---------------------------------------------------------------------------
# Service tests: direction filter
# ---------------------------------------------------------------------------


async def test_direction_out_follows_only_forward_refs(svc):
    """direction='out' follows only the item's own forward refs, not backrefs."""
    a = (await svc.create("feature", "A")).item
    b = (await svc.create("task", "B")).item
    c = (await svc.create("bug", "C")).item
    await svc.add_ref(a.id, b.id, kind="related")  # A → B (A has out-ref)
    await svc.add_ref(c.id, a.id, kind="related")  # C → A (C has out-ref to A; A gets backref)

    root = await svc.graph(a.id, depth=1, direction="out")
    child_ids = {ch.id for ch in root.children}
    assert b.id in child_ids  # A's own out-ref
    assert c.id not in child_ids  # backref — excluded with direction=out


async def test_direction_in_follows_only_backrefs(svc):
    """direction='in' follows only backrefs (items that point at the root)."""
    a = (await svc.create("feature", "A")).item
    b = (await svc.create("task", "B")).item
    c = (await svc.create("bug", "C")).item
    await svc.add_ref(a.id, b.id, kind="related")  # A → B (A has out-ref)
    await svc.add_ref(c.id, a.id, kind="related")  # C → A (C points at A)

    root = await svc.graph(a.id, depth=1, direction="in")
    child_ids = {ch.id for ch in root.children}
    assert c.id in child_ids  # C points at A → backref
    assert b.id not in child_ids  # A points at B → out-ref, excluded with direction=in


async def test_direction_both_merges_out_and_in(svc):
    """direction='both' includes both forward refs and backrefs."""
    a = (await svc.create("feature", "A")).item
    b = (await svc.create("task", "B")).item
    c = (await svc.create("bug", "C")).item
    await svc.add_ref(a.id, b.id, kind="related")
    await svc.add_ref(c.id, a.id, kind="related")

    root = await svc.graph(a.id, depth=1, direction="both")
    child_ids = {ch.id for ch in root.children}
    assert b.id in child_ids
    assert c.id in child_ids


# ---------------------------------------------------------------------------
# Service tests: cycle handling
# ---------------------------------------------------------------------------


async def test_cycle_terminates_with_seen_marker(svc):
    """A cycle (A → B → A) terminates: the revisited node is emitted once with seen=True."""
    a = (await svc.create("feature", "A")).item
    b = (await svc.create("task", "B")).item
    await svc.add_ref(a.id, b.id, kind="related")
    await svc.add_ref(b.id, a.id, kind="related")  # Creates cycle A → B → A

    root = await svc.graph(a.id, depth=5, direction="out")
    # B should be a child of root (A)
    b_child = next((ch for ch in root.children if ch.id == b.id), None)
    assert b_child is not None
    # B's children would include A, but A was already seen
    a_revisited = next((ch for ch in b_child.children if ch.id == a.id), None)
    assert a_revisited is not None
    assert a_revisited.seen is True
    assert a_revisited.children == []  # not recursed into


# ---------------------------------------------------------------------------
# Service tests: closed items
# ---------------------------------------------------------------------------


async def test_closed_items_hidden_by_default(svc):
    """Closed items (Done/Cancelled) are not traversed unless include_closed=True."""
    a = (await svc.create("feature", "A")).item
    b = (await svc.create("task", "B")).item
    await svc.set_status(b.id, "InProgress")
    await svc.set_status(b.id, "Done")
    await svc.add_ref(a.id, b.id, kind="related")

    root = await svc.graph(a.id, depth=1)
    child_ids = {ch.id for ch in root.children}
    assert b.id not in child_ids  # B is Done → hidden


async def test_include_closed_reveals_closed_items(svc):
    """include_closed=True includes closed items."""
    a = (await svc.create("feature", "A")).item
    b = (await svc.create("task", "B")).item
    await svc.set_status(b.id, "InProgress")
    await svc.set_status(b.id, "Done")
    await svc.add_ref(a.id, b.id, kind="related")

    root = await svc.graph(a.id, depth=1, include_closed=True)
    child_ids = {ch.id for ch in root.children}
    assert b.id in child_ids


# ---------------------------------------------------------------------------
# Dot / mermaid export helpers
# ---------------------------------------------------------------------------


def test_graph_to_dot_produces_valid_digraph():
    """graph_to_dot emits a valid digraph with quoted IDs and [label=...] edges."""
    root = GraphNode(
        id="FEAT-000002",
        type="feature",
        status="Draft",
        priority=None,
        assignee=None,
        edge_kind=None,
        direction=None,
        seen=False,
        children=[
            GraphNode(
                id="TASK-000003",
                type="task",
                status="Ready",
                priority=None,
                assignee=None,
                edge_kind="depends-on",
                direction="out",
                seen=False,
                children=[],
            )
        ],
    )
    dot = graph_to_dot(root)
    assert dot.startswith("digraph {")
    assert dot.endswith("}")
    assert '"FEAT-000002"' in dot
    assert '"TASK-000003"' in dot
    assert '[label="depends on"]' in dot
    # Raw kind string must not appear as label in dot output
    assert '"depends-on"' not in dot.split("[label=")[1] if "[label=" in dot else True


def test_graph_to_dot_required_by_label():
    """graph_to_dot uses 'required by' for direction='in' dependency edges."""
    root = GraphNode(
        id="TASK-000003",
        type="task",
        status="Ready",
        priority=None,
        assignee=None,
        edge_kind=None,
        direction=None,
        seen=False,
        children=[
            GraphNode(
                id="FEAT-000002",
                type="feature",
                status="Draft",
                priority=None,
                assignee=None,
                edge_kind="depends-on",
                direction="in",
                seen=False,
                children=[],
            )
        ],
    )
    dot = graph_to_dot(root)
    assert '[label="required by"]' in dot


def test_graph_to_mermaid_produces_flowchart():
    """graph_to_mermaid emits a flowchart LR with -->|label| edges."""
    root = GraphNode(
        id="FEAT-000002",
        type="feature",
        status="Draft",
        priority=None,
        assignee=None,
        edge_kind=None,
        direction=None,
        seen=False,
        children=[
            GraphNode(
                id="TASK-000003",
                type="task",
                status="Ready",
                priority=None,
                assignee=None,
                edge_kind="related",
                direction="out",
                seen=False,
                children=[],
            )
        ],
    )
    mermaid = graph_to_mermaid(root)
    assert mermaid.startswith("flowchart LR")
    assert "FEAT_000002" in mermaid  # hyphens replaced with underscores
    assert "TASK_000003" in mermaid
    assert "-->|related|" in mermaid


def test_graph_to_dot_deduplicates_seen_nodes():
    """dot export collapses the tree's seen re-emissions into a single node per ID."""
    # Build a tree where TASK-000003 appears once normally and once as 'seen'
    root = GraphNode(
        id="FEAT-000002",
        type="feature",
        status="Draft",
        priority=None,
        assignee=None,
        edge_kind=None,
        direction=None,
        seen=False,
        children=[
            GraphNode(
                id="TASK-000003",
                type="task",
                status="Ready",
                priority=None,
                assignee=None,
                edge_kind="related",
                direction="out",
                seen=False,
                children=[
                    GraphNode(
                        id="FEAT-000002",
                        type="feature",
                        status="Draft",
                        priority=None,
                        assignee=None,
                        edge_kind="related",
                        direction="in",
                        seen=True,  # cycle back to root
                        children=[],
                    )
                ],
            )
        ],
    )
    dot = graph_to_dot(root)
    # FEAT-000002 appears as exactly one node declaration
    assert dot.count('"FEAT-000002";') == 1


# ---------------------------------------------------------------------------
# CLI smoke tests
# ---------------------------------------------------------------------------


@pytest.fixture
def graph_squad(tmp_path, monkeypatch, frozen_time):
    """A seeded squad for CLI graph tests.

    Items:
      ROLE-000001  manager
      FEAT-000002  Feature A
      TASK-000003  Task B  (parent=FEAT-000002; depends-on FEAT-000002)
      BUG-000004   Bug C   (related to TASK-000003 via backref)

    TASK-000003 has: ref FEAT-000002 --kind depends-on
    BUG-000004 has:  ref TASK-000003 --kind related
    """
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    def inv(args: list[str]) -> None:
        r = runner.invoke(app, args)
        assert r.exit_code == 0, f"setup {args!r} failed (exit {r.exit_code}):\n{r.output}"

    inv(["init", "--no-seed-skills", "--roles", "minimal"])
    inv(["create", "feature", "Feature A", "--author", "manager"])
    inv(["create", "task", "Task B", "--author", "manager", "--parent", "FEAT-000002"])
    inv(["create", "bug", "Bug C", "--author", "manager"])
    inv(["task", "3", "ref", "add", "FEAT-000002", "--kind", "depends-on"])
    inv(["bug", "4", "ref", "add", "TASK-000003", "--kind", "related"])

    return runner


def test_cli_graph_renders_tree(graph_squad):
    """sq graph FEAT-000002 renders without error and includes the item ID."""
    r = graph_squad.invoke(app, ["graph", "FEAT-000002"])
    assert r.exit_code == 0, r.output
    assert "FEAT-2" in r.output


def test_cli_graph_bare_number_resolves(graph_squad):
    """sq graph 2 resolves bare number to FEAT-000002."""
    r = graph_squad.invoke(app, ["graph", "2"])
    assert r.exit_code == 0, r.output
    assert "FEAT-2" in r.output


def test_cli_graph_depth_zero(graph_squad):
    """sq graph FEAT-000002 --depth 0 shows only the root."""
    r = graph_squad.invoke(app, ["graph", "FEAT-000002", "--depth", "0"])
    assert r.exit_code == 0, r.output
    assert "FEAT-2" in r.output
    # At depth 0, TASK-000003 should NOT appear
    assert "TASK-3" not in r.output


def test_cli_graph_direction_out(graph_squad):
    """sq graph TASK-000003 --direction out follows only forward refs."""
    r = graph_squad.invoke(app, ["graph", "TASK-000003", "--direction", "out", "--depth", "1"])
    assert r.exit_code == 0, r.output
    # TASK-000003 depends-on FEAT-000002 (out-ref) → should appear
    assert "FEAT-2" in r.output


def test_cli_graph_kind_filter(graph_squad):
    """sq graph TASK-000003 --kind related shows only related edges."""
    r = graph_squad.invoke(app, ["graph", "TASK-000003", "--kind", "related", "--depth", "1"])
    assert r.exit_code == 0, r.output
    # BUG-000004 is related to TASK-000003 (backref); depends-on FEAT-000002 should not show
    # With --kind related and depth=1, only related edges are followed
    assert "BUG-4" in r.output
    # FEAT-000002 is reached via depends-on, which is filtered out
    assert "FEAT-2" not in r.output


def test_cli_graph_dependency_labels_no_raw_kinds(graph_squad):
    """Branch labels must not contain raw 'depends-on' or 'blocks' strings."""
    r = graph_squad.invoke(app, ["graph", "TASK-000003", "--depth", "2"])
    assert r.exit_code == 0, r.output
    # The raw kind strings must never appear as branch labels in the tree
    # (they may appear in the ID like "FEAT-000003" but not as standalone label words)
    lines = r.output.splitlines()
    for line in lines:
        # Skip the root line (no edge label on root)
        if "FEAT-2" in line or "TASK-3" in line or "BUG-4" in line:
            # The label text is in parentheses like "(depends on)" or "(required by)"
            if "(depends-on)" in line:
                pytest.fail(f"Raw 'depends-on' appeared as label in: {line!r}")
            if "(blocks)" in line:
                pytest.fail(f"Raw 'blocks' appeared as label in: {line!r}")


def test_cli_graph_json_shape(graph_squad):
    """sq graph FEAT-000002 --json --depth 1 emits a valid, ANSI-free JSON root object."""
    args = ["graph", "FEAT-000002", "--json", "--depth", "1", "--direction", "in"]
    r = graph_squad.invoke(app, args)
    assert r.exit_code == 0, r.output
    # Regression for BUG-000183: --json must be ANSI-free unconditionally (print_json_clean).
    assert "\x1b[" not in r.output, (
        "sq graph --json emitted ANSI escape codes — output must be unconditionally color-free"
    )
    data = json.loads(r.output)
    assert isinstance(data, dict)
    # Root shape
    assert data["id"] == "FEAT-2"
    assert data["type"] == "feature"
    assert "status" in data
    assert data["edge_kind"] is None
    assert data["direction"] is None
    assert data["seen"] is False
    assert isinstance(data["children"], list)
    # TASK-000003 depends-on FEAT-000002, so from FEAT's in-direction: TASK is a child
    task_child = next((c for c in data["children"] if c["id"] == "TASK-3"), None)
    assert task_child is not None
    assert task_child["edge_kind"] == "depends-on"
    assert task_child["direction"] == "in"  # TASK depends on FEAT → FEAT required by TASK


def test_cli_graph_json_golden(graph_squad):
    """sq graph FEAT-000002 --json --depth 1 --direction in: golden-test the exact shape."""
    args = ["graph", "FEAT-000002", "--json", "--depth", "1", "--direction", "in"]
    r = graph_squad.invoke(app, args)
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    _check_golden("graph_feat_json", data)


def test_cli_graph_format_dot(graph_squad):
    """sq graph FEAT-000002 --format dot emits a valid digraph."""
    args = ["graph", "FEAT-000002", "--format", "dot", "--depth", "1", "--direction", "in"]
    r = graph_squad.invoke(app, args)
    assert r.exit_code == 0, r.output
    output = r.output
    assert "digraph {" in output
    assert '"FEAT-2"' in output
    assert "}" in output
    _check_golden("graph_feat_dot", output.strip())


def test_cli_graph_format_mermaid(graph_squad):
    """sq graph FEAT-000002 --format mermaid emits a flowchart LR."""
    args = ["graph", "FEAT-000002", "--format", "mermaid", "--depth", "1", "--direction", "in"]
    r = graph_squad.invoke(app, args)
    assert r.exit_code == 0, r.output
    assert "flowchart LR" in r.output
    assert "FEAT_2" in r.output


def test_cli_graph_priority_badge_renders(tmp_path, monkeypatch, frozen_time):
    """sq graph renders correctly when root and/or child carries a non-None priority.

    GraphNode.priority is a plain badge-code string (e.g. "high"); the generic badge_render()
    renderer takes that string directly (no enum wrapping — the Priority enum is gone).
    """
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    def inv(args: list[str]) -> None:
        r = runner.invoke(app, args)
        assert r.exit_code == 0, f"setup {args!r} failed:\n{r.output}"

    inv(["init", "--no-seed-skills", "--roles", "minimal"])
    inv(["create", "feature", "Root Feature", "--author", "manager", "--priority", "high"])
    inv(["create", "task", "Priority Task", "--author", "manager", "--priority", "urgent"])
    inv(["task", "3", "ref", "add", "FEAT-000002", "--kind", "depends-on"])

    # Root (FEAT-000002) has priority=high; child (TASK-000003) has priority=urgent.
    # Without the fix, this crashed with AttributeError on both _attach_graph_node and
    # the root rendering line.
    r = runner.invoke(app, ["graph", "FEAT-000002", "--depth", "1", "--direction", "in"])
    assert r.exit_code == 0, f"sq graph crashed with priority-bearing nodes:\n{r.output}"
    assert "FEAT-2" in r.output
    assert "TASK-3" in r.output
    # Badge text for both priorities must appear in the rendered tree
    assert "high" in r.output
    assert "urgent" in r.output


def test_cli_graph_all_includes_closed(tmp_path, monkeypatch, frozen_time):
    """sq graph --all includes closed items; without --all they are hidden."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    def inv(args: list[str]) -> None:
        r = runner.invoke(app, args)
        assert r.exit_code == 0, f"setup {args!r} failed:\n{r.output}"

    inv(["init", "--no-seed-skills", "--roles", "minimal"])
    inv(["create", "feature", "Root", "--author", "manager"])
    inv(["create", "task", "Done task", "--author", "manager"])
    inv(["task", "3", "status", "InProgress"])
    inv(["task", "3", "status", "Done"])
    inv(["feature", "2", "ref", "add", "TASK-000003", "--kind", "related"])

    # Without --all
    r_no_all = runner.invoke(app, ["graph", "FEAT-000002", "--depth", "1"])
    assert r_no_all.exit_code == 0
    assert "TASK-3" not in r_no_all.output

    # With --all
    r_all = runner.invoke(app, ["graph", "FEAT-000002", "--depth", "1", "--all"])
    assert r_all.exit_code == 0
    assert "TASK-3" in r_all.output
