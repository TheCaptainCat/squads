"""Forward reference edges (typed cross-links); backrefs are computed by inversion."""

from collections.abc import Callable
from dataclasses import dataclass, field

from squads import _actor as actor
from squads import _clock as clock
from squads._errors import SquadsError
from squads._index._resolver import item_file, require_item
from squads._itemfile import update_frontmatter
from squads._models._item import (
    DEFAULT_KIND,
    VALID_REF_KINDS,
    Item,
    effective_prefix,
    make_ref,
    ref_id_matches,
    split_ref,
)
from squads._paths import number_for_id
from squads._services._base import ServiceCore
from squads._services._results import GraphNode

# ---------------------------------------------------------------------------
# Graph traversal helpers
# ---------------------------------------------------------------------------

# The two raw kind strings that form the dependency pair (equivalent for traversal).
# Both normalize to edge_kind="depends-on" in GraphNode; direction disambiguates the end.
_DEP_KINDS: frozenset[str] = frozenset({"blocks", "depends-on"})


@dataclass
class _TraversalCtx:
    """Immutable traversal parameters threaded through recursive BFS helpers."""

    db_items: dict[int, Item]  # sequence_id → Item; pre-loaded snapshot
    depth: int
    kinds: frozenset[str]  # effective filter; frozenset of VALID_REF_KINDS
    direction: str  # "out" | "in" | "both"
    include_closed: bool
    is_open: Callable[[str], bool]  # spec.is_open bound at construction
    seen: set[str] = field(default_factory=lambda: set[str]())


def _item_by_id(ctx: _TraversalCtx, item_id: str) -> Item | None:
    """Look up an item by its formatted ID; tolerates dangling refs by returning None."""
    _, _, digits = item_id.rpartition("-")
    if not digits.isdigit():
        return None
    seq = int(digits)
    return ctx.db_items.get(seq)


def _out_neighbours(ctx: _TraversalCtx, item: Item) -> list[tuple[str, str, str]]:
    """Outgoing ref neighbours: (target_id, edge_kind, direction).

    ``edge_kind`` is always the normalized kind (``depends-on`` for both ``blocks`` and
    ``depends-on`` stored edges); ``direction`` is ``"out"`` or ``"in"`` from the
    **expanded item's** perspective.

    Raw ``blocks`` edges are normalized: ``item blocks target`` → ``edge_kind="depends-on"``,
    ``direction="in"`` (target is the dependent; it would point at item via ``depends-on``).
    All other kinds keep their literal kind and ``direction="out"``.
    """
    result: list[tuple[str, str, str]] = []
    for r in item.refs:
        raw_id, kind = split_ref(r)
        if kind not in ctx.kinds:
            continue
        # Normalize the dependency pair
        if kind == "blocks":
            result.append((raw_id, "depends-on", "in"))
        else:
            result.append((raw_id, kind, "out"))
    return result


def _in_neighbours(ctx: _TraversalCtx, item: Item) -> list[tuple[str, str, str]]:
    """Inbound ref neighbours: (source_id, edge_kind, direction).

    Walk ALL items in the snapshot and collect those whose refs point at ``item``.
    ``edge_kind`` is normalized; ``direction`` is from the **expanded item's** perspective
    (i.e. "in" means the neighbour item has an out-ref to expanded, "out" means the
    neighbour item has a ``blocks`` edge that expanded depends on).

    Raw ``depends-on`` stored on neighbour → neighbour → item via depends-on →
        edge_kind="depends-on", direction="in" (neighbour points at item; item required by it).
    Raw ``blocks`` stored on neighbour → neighbour blocks item → item depends on neighbour →
        edge_kind="depends-on", direction="out" (item would have a depends-on to neighbour).
    Other kinds: edge_kind=kind, direction="in".
    """
    target_prefix = effective_prefix(item.prefix)
    target_seq = item.sequence_id
    result: list[tuple[str, str, str]] = []
    for other in ctx.db_items.values():
        for r in other.refs:
            raw_id, kind = split_ref(r)
            if kind not in ctx.kinds:
                continue
            if not ref_id_matches(raw_id, target_prefix, target_seq):
                continue
            # Normalize the dependency pair
            if kind == "depends-on":
                # other depends-on item → item is the blocker → item "required by" other
                result.append((other.id, "depends-on", "in"))
            elif kind == "blocks":
                # other blocks item → item depends on other → item "depends on" other
                result.append((other.id, "depends-on", "out"))
            else:
                result.append((other.id, kind, "in"))
    return result


def _neighbours(ctx: _TraversalCtx, item: Item) -> list[tuple[str, str, str]]:
    """Merge out and in neighbours according to ``ctx.direction``, sorted by ID number."""
    pairs: list[tuple[str, str, str]] = []
    if ctx.direction in ("out", "both"):
        pairs.extend(_out_neighbours(ctx, item))
    if ctx.direction in ("in", "both"):
        pairs.extend(_in_neighbours(ctx, item))

    # De-duplicate: same (target_id, edge_kind, direction) may appear from both directions
    # when direction="both" and the relationship is encoded as blocks+depends-on on each end.
    # Use a set keyed by the canonical numeric id to deduplicate cross-width refs.
    seen_keys: set[tuple[int, str, str]] = set()
    deduped: list[tuple[str, str, str]] = []
    for tid, ek, d in pairs:
        _, _, digits = tid.rpartition("-")
        seq_key = int(digits) if digits.isdigit() else -1
        key = (seq_key, ek, d)
        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append((tid, ek, d))

    deduped.sort(key=lambda t: number_for_id(t[0]) if t[0].rsplit("-", 1)[-1].isdigit() else 0)
    return deduped


def _build_graph_node(
    item_id: str,
    edge_kind: str | None,
    direction: str | None,
    ctx: _TraversalCtx,
    current_depth: int,
) -> GraphNode:
    """Recursively build a GraphNode for *item_id* at *current_depth*.

    The root node is at depth 0 and is added to ``ctx.seen`` before any neighbours are
    expanded.  Subsequent nodes are added to ``ctx.seen`` as they are EMITTED (not when they
    are expanded), so a revisited node is emitted once with ``seen=True`` and never recursed.
    """
    item = _item_by_id(ctx, item_id)
    if item is None:
        # Defensive guard: callers already skip dangling refs before recursing
        # (_neighbours loop checks `nb_item is None: continue`, and the root is
        # require_item'd).  No path reaches here in practice, but the guard stays
        # so a future caller doesn't silently crash on a dangling ref.
        return GraphNode(
            id=item_id,
            type="",
            status="",
            priority=None,
            assignee=None,
            edge_kind=edge_kind,
            direction=direction,
            seen=True,
            children=[],
        )

    already_seen = item.id in ctx.seen
    ctx.seen.add(item.id)

    priority_val = item.priority
    node = GraphNode(
        id=item.id,
        type=item.type,
        status=item.status,
        priority=priority_val,
        assignee=item.assignee,
        edge_kind=edge_kind,
        direction=direction,
        seen=already_seen,
        children=[],
    )

    if already_seen or current_depth >= ctx.depth:
        return node

    children: list[GraphNode] = []
    for nb_id, nb_kind, nb_dir in _neighbours(ctx, item):
        nb_item = _item_by_id(ctx, nb_id)
        if nb_item is None:
            continue  # dangling ref — skip silently
        if not ctx.include_closed and not ctx.is_open(nb_item.status):
            continue  # closed item filtered out
        child = _build_graph_node(nb_id, nb_kind, nb_dir, ctx, current_depth + 1)
        children.append(child)

    # Rebuild as frozen dataclass with children (dataclass frozen=True disallows mutation)
    return GraphNode(
        id=node.id,
        type=node.type,
        status=node.status,
        priority=node.priority,
        assignee=node.assignee,
        edge_kind=node.edge_kind,
        direction=node.direction,
        seen=node.seen,
        children=children,
    )


# ---------------------------------------------------------------------------
# Graph export helpers (dot / mermaid)
# ---------------------------------------------------------------------------


def _collect_edges(root: GraphNode) -> tuple[set[str], set[tuple[str, str, str]]]:
    """Walk the GraphNode tree and collect unique node ids and edges.

    Since ``seen`` re-emits a node that already appeared higher in the tree, we
    de-duplicate by treating the tree as a directed graph: one node per ID, one
    edge per (from, to, kind) triple.

    Returns (node_ids, edges) where edges are (from_id, to_id, label).
    The ``label`` for dependency edges uses "depends on" / "required by" to match
    the display convention.
    """
    nodes: set[str] = set()
    edges: set[tuple[str, str, str]] = set()

    def _label(edge_kind: str, direction: str) -> str:
        if edge_kind == "depends-on":
            return "depends on" if direction == "out" else "required by"
        return edge_kind

    stack: list[tuple[GraphNode, str | None]] = [(root, None)]
    while stack:
        node, parent_id = stack.pop()
        nodes.add(node.id)
        if parent_id is not None and node.edge_kind is not None and node.direction is not None:
            label = _label(node.edge_kind, node.direction)
            edges.add((parent_id, node.id, label))
        # Only recurse into non-seen nodes (seen nodes have no children anyway)
        stack.extend((child, node.id) for child in node.children)

    return nodes, edges


def graph_to_dot(root: GraphNode) -> str:
    """Serialize a GraphNode tree to a Graphviz ``digraph`` string."""
    nodes, edges = _collect_edges(root)

    def _q(s: str) -> str:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

    lines = [
        "digraph {",
        *[f"    {_q(nid)};" for nid in sorted(nodes)],
        *[
            f"    {_q(from_id)} -> {_q(to_id)} [label={_q(label)}];"
            for from_id, to_id, label in sorted(edges)
        ],
        "}",
    ]
    return "\n".join(lines)


def graph_to_mermaid(root: GraphNode) -> str:
    """Serialize a GraphNode tree to a Mermaid ``flowchart LR`` string."""
    _, edges = _collect_edges(root)

    def _safe_id(nid: str) -> str:
        # Mermaid node IDs can't contain hyphens in all renderers; use underscores.
        return nid.replace("-", "_")

    lines = ["flowchart LR"]
    for from_id, to_id, label in sorted(edges):
        lines.append(f"    {_safe_id(from_id)} -->|{label}| {_safe_id(to_id)}")
    return "\n".join(lines)


class RefsMixin(ServiceCore):
    async def add_ref(self, from_id: str, to_id: str, *, kind: str = DEFAULT_KIND) -> Item:
        if from_id == to_id:
            raise SquadsError("an item cannot reference itself")
        if kind not in VALID_REF_KINDS:
            valid = ", ".join(sorted(VALID_REF_KINDS))
            raise SquadsError(f"unknown ref kind {kind!r}. Valid kinds: {valid}")
        async with self.store.transaction() as db:
            src = require_item(db, from_id)
            tgt = require_item(db, to_id)
            # The kind rides with the edge; re-adding an existing edge updates its kind.
            # Dedup by (prefix, seq) so old-width stored refs ("PREFIX-000007") are replaced
            # when re-adding across a repad boundary where to_id is "PREFIX-0000007" — file
            # contents are never rewritten, so widths diverge.
            tgt_prefix = effective_prefix(tgt.prefix)
            tgt_seq = tgt.sequence_id
            src.refs = [
                r for r in src.refs if not ref_id_matches(split_ref(r)[0], tgt_prefix, tgt_seq)
            ]
            src.refs.append(make_ref(to_id, kind))
            src.updated_at = clock.now()
            src.modified_session, _ = actor.current_session()
            await update_frontmatter(item_file(self.paths, src), src)
            self.store._log(  # pyright: ignore[reportPrivateUsage]
                "ref",
                src.id,
                {"add": to_id, "kind": kind},
            )
        return src

    async def rm_ref(self, from_id: str, to_id: str) -> Item:
        async with self.store.transaction() as db:
            src = require_item(db, from_id)
            # Determine (prefix, seq) from the caller's to_id — width-tolerant: the stored
            # ref may carry an old width, the to_id may carry the new width.
            head, _, digits = to_id.rpartition("-")
            if head and digits.isdigit():
                to_prefix = head.upper()
                to_seq = int(digits)
                src.refs = [
                    r for r in src.refs if not ref_id_matches(split_ref(r)[0], to_prefix, to_seq)
                ]
            else:
                # Bare number or malformed — fall back to literal string comparison.
                src.refs = [r for r in src.refs if split_ref(r)[0] != to_id]
            src.updated_at = clock.now()
            src.modified_session, _ = actor.current_session()
            await update_frontmatter(item_file(self.paths, src), src)
            self.store._log(  # pyright: ignore[reportPrivateUsage]
                "ref",
                src.id,
                {"remove": to_id},
            )
        return src

    async def refs_out(self, item_id: str) -> list[tuple[str, str]]:
        return [split_ref(r) for r in (await self.get(item_id)).refs]

    async def refs_in(self, item_id: str) -> list[tuple[str, str]]:
        """Backrefs computed by inverting forward edges (never stored).

        Comparison is by (prefix, seq) so old-width ref strings (``"PREFIX-000007"``) and
        new-width item IDs (``"PREFIX-0000007"``) match correctly after a ``sq migrate repad``
        (file contents are never rewritten, so refs keep their original width).
        """
        db = await self.store.load()
        target = require_item(db, item_id)
        target_prefix = effective_prefix(target.prefix)
        target_seq = target.sequence_id
        out: list[tuple[str, str]] = []
        for it in db.items.values():
            for r in it.refs:
                rid, kind = split_ref(r)
                if ref_id_matches(rid, target_prefix, target_seq):
                    out.append((it.id, kind))
        return sorted(out, key=lambda p: number_for_id(p[0]))

    async def graph(
        self,
        root_id: str,
        *,
        depth: int = 2,
        kinds: set[str] | None = None,
        direction: str = "both",
        include_closed: bool = False,
    ) -> GraphNode:
        """Build an ego-centric BFS ref graph rooted at *root_id*.

        Parameters
        ----------
        root_id:
            The formatted item ID to root the graph at (e.g. ``"PREFIX-000037"``).
        depth:
            How many hops to follow from the root (default 2; depth 0 = root only).
        kinds:
            A set of ref kinds to follow.  ``None`` means all :data:`VALID_REF_KINDS`.
            Unknown kinds raise :class:`~squads._errors.SquadsError`.
        direction:
            ``"out"`` (follow the item's own forward refs), ``"in"`` (follow backrefs),
            or ``"both"`` (merged, default).
        include_closed:
            Include items whose status is closed (done/cancelled/…).  Default ``False``.

        Returns
        -------
        GraphNode
            The root node with its ``children`` populated recursively up to *depth*.
            Revisited nodes are emitted once with ``seen=True`` and no children (cycle
            / BFS breadth termination).

        Dependency-edge normalization
        ------------------------------
        ``depends-on`` and ``blocks`` are two spellings of the same dependency.  Both
        are stored in ``edge_kind="depends-on"`` on the returned
        :class:`~squads._services._results.GraphNode`; ``direction`` disambiguates
        the end:

        - ``direction="out"`` → the expanded node depends on the child → display "depends on"
        - ``direction="in"`` → the child depends on the expanded node → display "required by"
        """
        if direction not in ("out", "in", "both"):
            raise SquadsError(f"invalid direction {direction!r}; expected 'out', 'in', or 'both'")

        effective_kinds: frozenset[str]
        if kinds is None:
            effective_kinds = frozenset(VALID_REF_KINDS)
        else:
            unknown = kinds - VALID_REF_KINDS
            if unknown:
                valid = ", ".join(sorted(VALID_REF_KINDS))
                raise SquadsError(
                    f"unknown ref kind(s): {', '.join(sorted(unknown))}. Valid kinds: {valid}"
                )
            effective_kinds = frozenset(kinds)

        db = await self.store.load()
        root_item = require_item(db, root_id)

        if not include_closed and not self.spec.is_open(root_item.status):
            # Root is closed and --all not set: return root-only (seen=False, no children)
            return GraphNode(
                id=root_item.id,
                type=root_item.type,
                status=root_item.status,
                priority=root_item.priority,
                assignee=root_item.assignee,
                edge_kind=None,
                direction=None,
                seen=False,
                children=[],
            )

        ctx = _TraversalCtx(
            db_items=db.items,
            depth=depth,
            kinds=effective_kinds,
            direction=direction,
            include_closed=include_closed,
            is_open=self.spec.is_open,
        )
        # The root node is NOT pre-added to ctx.seen here; _build_graph_node adds it
        # when it first emits the root, before recursing into children.  This ensures
        # the root's own ``seen`` flag is False (not a revisit) while still correctly
        # terminating any cycle that leads back to the root.

        return _build_graph_node(root_item.id, None, None, ctx, 0)

    async def blocked(self) -> list[tuple[Item, list[Item]]]:
        """Open items with ≥1 open blocker, paired with those blockers.

        Two equivalent spellings are supported:
        - ``A ref add B --kind blocks`` ("A blocks B"): B is blocked while A stays open.
          The edge lives on the *blocker* A; B is the target.
        - ``A ref add B --kind depends-on`` ("A depends-on B"): A is blocked while B stays open.
          The edge lives on the *dependent* A; B is the blocker.

        Both spellings are consumed identically. An item blocked through both edges is
        deduplicated — it appears once with the union of its open blockers.
        """
        db = await self.store.load()
        # keyed by the blocked item's id; value is a set of blocker ids (dedup)
        blockers_by_target: dict[str, set[str]] = {}
        for it in db.items.values():
            for r in it.refs:
                rid, kind = split_ref(r)
                if kind == "blocks":
                    # it blocks rid → rid is the blocked item, it is the blocker
                    blockers_by_target.setdefault(rid, set()).add(it.id)
                elif kind == "depends-on":
                    # it depends-on rid → it is the blocked item, rid is the blocker
                    blockers_by_target.setdefault(it.id, set()).add(rid)
        out: list[tuple[Item, list[Item]]] = []
        for tid, blocker_ids in blockers_by_target.items():
            target = db.get(tid)
            if target is None or not self.spec.is_open(target.status):
                continue
            open_blockers: list[Item] = []
            for bid in blocker_ids:
                b = db.get(bid)
                if b is not None and self.spec.is_open(b.status):
                    open_blockers.append(b)
            open_blockers.sort(key=lambda b: number_for_id(b.id))
            if open_blockers:
                out.append((target, open_blockers))
        return sorted(out, key=lambda p: number_for_id(p[0].id))
