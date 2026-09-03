"""Forward reference edges (typed cross-links); backrefs are computed by inversion."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from squads import _actor as actor
from squads import _badges as badges
from squads import _clock as clock
from squads._errors import SquadsError
from squads._index._resolver import item_file, require_item
from squads._itemfile import update_frontmatter
from squads._models._extras import ExtraKey as X
from squads._models._index import SquadsDB
from squads._models._item import (
    Item,
    effective_prefix,
    make_ref,
    ref_id_matches,
    split_ref,
)
from squads._paths import number_for_id
from squads._services._base import ServiceCore
from squads._services._results import GraphNode
from squads._workflow import ROSTER_ROLE
from squads._workflow._models import WorkflowSpec

# ---------------------------------------------------------------------------
# Graph traversal helpers
# ---------------------------------------------------------------------------


@dataclass
class _TraversalCtx:
    """Immutable traversal parameters threaded through recursive BFS helpers.

    ``requested_kinds`` is the caller's explicit ``--kind`` filter and nothing else — it must
    never double as "the declared set", which is a *different* question answered by consulting
    ``spec.ref_kinds`` directly (see :func:`_edge_semantic`). Conflating the two makes an edge
    whose kind the merged spec does not declare indistinguishable, at the traversal site, from
    an edge the caller simply didn't ask for — both then vanish silently. ``None`` here means
    "no filter": every edge is seen, declared or not. A caller-supplied set means "seen only
    these kinds" (``graph()`` refuses an undeclared kind in that set up front, before a
    ``_TraversalCtx`` is even built).
    """

    db_items: dict[int, Item]  # sequence_id → Item; pre-loaded snapshot
    depth: int
    requested_kinds: frozenset[str] | None  # explicit --kind filter; None = no filter (see below)
    direction: str  # "out" | "in" | "both"
    include_closed: bool
    is_open: Callable[[str], bool]  # spec.is_open bound at construction
    spec: WorkflowSpec  # resolves each node's declared badge fields (GraphNode.badges)
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

    ``edge_kind`` is always the normalized kind — the declared dependency kind
    (:meth:`WorkflowSpec.canonical_dependency_ref_kind`) for either raw dependency spelling;
    ``direction`` is ``"out"`` or ``"in"`` from the **expanded item's** perspective.

    A raw edge stored as the declared BLOCKER-direction kind is normalized: ``item <blocker>
    target`` → ``edge_kind=<canonical>``, ``direction="in"`` (target is the dependent; it
    would point at item via the DEPENDENT-direction kind). Every other kind — including the
    DEPENDENT-direction kind itself — keeps its literal kind and ``direction="out"``.
    """
    blocker_kind = ctx.spec.dependency_ref_kind("blocker")
    canonical = ctx.spec.canonical_dependency_ref_kind()
    result: list[tuple[str, str, str]] = []
    for r in item.refs:
        raw_id, kind = split_ref(r)
        kind = kind or ctx.spec.default_ref_kind()  # bare wire form → the declared default
        # An explicit --kind filter gates which edges are SEEN at all; the merged spec not
        # declaring `kind` never does — an undeclared-kind edge still traverses.
        if ctx.requested_kinds is not None and kind not in ctx.requested_kinds:
            continue
        # Normalize the dependency pair
        if blocker_kind is not None and kind == blocker_kind:
            assert canonical is not None  # blocker_kind's own presence guarantees canonical
            result.append((raw_id, canonical, "in"))
        else:
            result.append((raw_id, kind, "out"))
    return result


def _in_neighbours(ctx: _TraversalCtx, item: Item) -> list[tuple[str, str, str]]:
    """Inbound ref neighbours: (source_id, edge_kind, direction).

    Walk ALL items in the snapshot and collect those whose refs point at ``item``.
    ``edge_kind`` is normalized; ``direction`` is from the **expanded item's** perspective
    (i.e. "in" means the neighbour item has an out-ref to expanded, "out" means the
    neighbour item has a BLOCKER-direction edge that expanded depends on).

    Raw DEPENDENT-direction kind stored on neighbour → neighbour → item →
        edge_kind=<canonical>, direction="in" (neighbour points at item; item required by it).
    Raw BLOCKER-direction kind stored on neighbour → neighbour blocks item → item depends on
        neighbour → edge_kind=<canonical>, direction="out" (item would depend on neighbour).
    Other kinds: edge_kind=kind, direction="in".
    """
    dependent_kind = ctx.spec.dependency_ref_kind("dependent")
    blocker_kind = ctx.spec.dependency_ref_kind("blocker")
    canonical = ctx.spec.canonical_dependency_ref_kind()
    target_prefix = effective_prefix(item.prefix)
    target_seq = item.sequence_id
    result: list[tuple[str, str, str]] = []
    for other in ctx.db_items.values():
        for r in other.refs:
            raw_id, kind = split_ref(r)
            kind = kind or ctx.spec.default_ref_kind()  # bare wire form → the declared default
            # See _out_neighbours: the --kind filter gates visibility, declared-ness never does.
            if ctx.requested_kinds is not None and kind not in ctx.requested_kinds:
                continue
            if not ref_id_matches(raw_id, target_prefix, target_seq):
                continue
            # Normalize the dependency pair
            if dependent_kind is not None and kind == dependent_kind:
                # other <dependent> item → item is the blocker → item "required by" other
                assert canonical is not None  # dependent_kind's presence guarantees canonical
                result.append((other.id, canonical, "in"))
            elif blocker_kind is not None and kind == blocker_kind:
                # other <blocker> item → item depends on other → item "depends on" other
                assert canonical is not None  # blocker_kind's own presence guarantees canonical
                result.append((other.id, canonical, "out"))
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


def _resolve_badges(spec: WorkflowSpec, item: Item) -> dict[str, str]:
    """Every declared badge field this item's type carries — the shared generic-badge-map
    shape (:func:`squads._badges.resolve_badges`), specialized to an ``Item``."""
    return badges.resolve_badges(spec, item.type, item.badge_value)


def _edge_semantic(spec: WorkflowSpec, edge_kind: str | None) -> str | None:
    """The declared semantic role of *edge_kind* — ``GraphNode.edge_semantic``.
    ``None`` for the root (``edge_kind is None``) and for a navigational kind
    (no declared ``role``); this is the field a consumer branches on, never ``edge_kind``
    itself."""
    if edge_kind is None:
        return None
    kind_spec = spec.ref_kinds.get(edge_kind)
    return kind_spec.role if kind_spec else None


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
            edge_semantic=_edge_semantic(ctx.spec, edge_kind),
            direction=direction,
            seen=True,
            badges={},
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
        edge_semantic=_edge_semantic(ctx.spec, edge_kind),
        direction=direction,
        seen=already_seen,
        badges=_resolve_badges(ctx.spec, item),
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
        edge_semantic=node.edge_semantic,
        direction=node.direction,
        seen=node.seen,
        badges=node.badges,
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

    def _label(edge_kind: str, edge_semantic: str | None, direction: str) -> str:
        if edge_semantic == "dependency":
            return "depends on" if direction == "out" else "required by"
        return edge_kind

    stack: list[tuple[GraphNode, str | None]] = [(root, None)]
    while stack:
        node, parent_id = stack.pop()
        nodes.add(node.id)
        if parent_id is not None and node.edge_kind is not None and node.direction is not None:
            label = _label(node.edge_kind, node.edge_semantic, node.direction)
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


def _mermaid_node_id(nid: str) -> str:
    """An item id as a Mermaid flowchart node identifier: every non-alphanumeric character
    escaped to ``_`` plus exactly four lowercase hex digits, alphanumeric runs left alone.

    Mermaid's node-id alphabet is effectively ``[A-Za-z0-9_]``, and an item id may contain
    anything a declared type prefix contains — a hyphen, an underscore, a symbol. This used to
    fold (``-`` → ``_``), and a fold is many-to-one: an adopter declaring two prefixes that
    differ only by hyphen versus underscore got one node standing for two distinct items, so the
    diagram was wrong before anyone read it. Escaping is injective, which is the whole point;
    the fixed four-digit width is what keeps it decodable, since a variable-width escape could
    not tell its own digits from the alphanumerics that follow.

    Deliberately the same scheme the VS Code client uses for the graphs it renders itself. The
    two ends are independent — neither decodes the other's output, and this function's result is
    display-only — so agreeing is a choice rather than a constraint; it is made because there is
    one correct injective encoding into that alphabet and no reason for the product to carry two
    spellings of it.

    The escaped form is never what a reader sees: :func:`graph_to_mermaid` declares each node
    with the real item id as its label, so a node still reads as the id it stands for and the
    escape stays an implementation detail of the identifier.

    Escapes **UTF-16 code units**, not code points, so a non-BMP character (an emoji prefix, say)
    becomes its two surrogates at four digits each rather than one five-digit escape that would
    break both the fixed width and the shared spelling.
    """
    units = nid.encode("utf-16-be")
    pairs = (int.from_bytes(units[i : i + 2], "big") for i in range(0, len(units), 2))
    return "".join(chr(u) if chr(u).isascii() and chr(u).isalnum() else f"_{u:04x}" for u in pairs)


def _mermaid_label(text: str) -> str:
    """*text* as a Mermaid quoted node label. ``"`` is the one character that could close the
    quoting early, so it goes out as an HTML entity (which Mermaid renders as the literal
    character) rather than being dropped or backslash-escaped, which Mermaid does not honour
    inside a quoted string."""
    return '"' + text.replace('"', "&quot;") + '"'


def graph_to_mermaid(root: GraphNode) -> str:
    """Serialize a GraphNode tree to a Mermaid ``flowchart LR`` string.

    Nodes are declared before the edges, each carrying its real item id as an explicit label:
    the identifier is escaped (see :func:`_mermaid_node_id`) and so is not readable on its own,
    and without a label Mermaid would draw the escaped form as the box text. Only nodes that an
    edge touches are declared, so the set of nodes drawn is exactly what it always was.
    """
    _, edges = _collect_edges(root)

    linked = sorted({end for from_id, to_id, _label in edges for end in (from_id, to_id)})
    lines = ["flowchart LR"]
    lines.extend(f"    {_mermaid_node_id(nid)}[{_mermaid_label(nid)}]" for nid in linked)
    lines.extend(
        f"    {_mermaid_node_id(from_id)} -->|{label}| {_mermaid_node_id(to_id)}"
        for from_id, to_id, label in sorted(edges)
    )
    return "\n".join(lines)


class RefsMixin(ServiceCore):
    async def add_ref(self, from_id: str, to_id: str, *, kind: str = "") -> Item:
        """Opens its own transaction, then delegates to :meth:`_add_ref_core` — the bulk
        importer calls that core directly (its own transaction is already open).

        ``kind=""`` (unspecified) resolves to the active spec's declared default kind — see
        :meth:`_add_ref_model`."""
        async with self.store.transaction() as db:
            return await self._add_ref_core(db, from_id, to_id, kind=kind)

    def _add_ref_model(
        self,
        db: SquadsDB,
        from_id: str,
        to_id: str,
        *,
        kind: str = "",
        now: datetime | None = None,
    ) -> tuple[Item, Item]:
        """The PURE half of a ref-add: no file I/O. Returns ``(src, base)`` — ``base`` is
        *src* as loaded, before this call's own delta, for the write seam's skew guard (see
        :func:`~squads._itemfile.ensure_no_skew`).

        Shared by :meth:`_add_ref_core` (the interactive/apply path) and the bulk importer's
        pre-pass, which calls this directly against a throwaway ``db`` copy with ``now=ev.at``.

        ``kind=""`` resolves to ``self.spec.default_ref_kind()``, validated the same as any
        explicit kind. The edge is written bare (:func:`~squads._models._item.make_ref`'s own
        ``""`` sentinel) exactly when the resolved kind is that declared default — never
        spelled out — so the corpus keeps one on-disk encoding per edge.
        """
        if from_id == to_id:
            raise SquadsError("an item cannot reference itself")
        default_kind = self.spec.default_ref_kind()
        resolved_kind = kind or default_kind
        if resolved_kind not in self.spec.ref_kinds:
            valid = ", ".join(sorted(self.spec.ref_kinds))
            raise SquadsError(f"unknown ref kind {resolved_kind!r}. Valid kinds: {valid}")
        src = require_item(db, from_id)
        tgt = require_item(db, to_id)
        base = src.model_copy(deep=True)
        # The kind rides with the edge; re-adding an existing edge updates its kind.
        # Dedup by (prefix, seq) so old-width stored refs ("PREFIX-000007") are replaced
        # when re-adding across a repad boundary where to_id is "PREFIX-0000007" — file
        # contents are never rewritten, so widths diverge.
        tgt_prefix = effective_prefix(tgt.prefix)
        tgt_seq = tgt.sequence_id
        src.refs = [r for r in src.refs if not ref_id_matches(split_ref(r)[0], tgt_prefix, tgt_seq)]
        wire_kind = "" if resolved_kind == default_kind else resolved_kind
        src.refs.append(make_ref(to_id, wire_kind))
        src.updated_at = now if now is not None else clock.now()
        src.modified_session, _ = actor.current_session()
        return src, base

    async def _add_ref_core(
        self, db: SquadsDB, from_id: str, to_id: str, *, kind: str = ""
    ) -> Item:
        """The ref-add mutation core: takes an already-open transaction's ``db``."""
        default_kind = self.spec.default_ref_kind()
        src, base = self._add_ref_model(db, from_id, to_id, kind=kind)
        await update_frontmatter(item_file(self.paths, src), src, base, default_kind=default_kind)
        self.store.log(
            "ref",
            src.id,
            {"add": to_id, "kind": kind or default_kind},
        )
        return src

    async def rm_ref(self, from_id: str, to_id: str, *, kind: str | None = None) -> Item:
        """Remove a forward ref edge from *from_id* to *to_id*.

        ``kind=None`` (default) keeps today's kind-agnostic behaviour: every edge to *to_id* is
        dropped regardless of its own kind. Passing an explicit ``kind`` narrows removal to only
        edges of that kind, leaving any other kind of edge between the two items untouched — the
        primitive :meth:`unlink_role` and the retirement gate's ``--unlink``
        (``_services/_retirement.py``) both build on, rather than each hand-rolling their own
        kind-filtered removal.
        """
        async with self.store.transaction() as db:
            src = require_item(db, from_id)
            base = src.model_copy(deep=True)
            # Determine (prefix, seq) from the caller's to_id — width-tolerant: the stored
            # ref may carry an old width, the to_id may carry the new width.
            head, _, digits = to_id.rpartition("-")
            if head and digits.isdigit():
                to_prefix = head.upper()
                to_seq = int(digits)

                def _matches(r: str) -> bool:
                    rid, rkind = split_ref(r)
                    return ref_id_matches(rid, to_prefix, to_seq) and (
                        kind is None or rkind == kind
                    )
            else:
                # Bare number or malformed — fall back to literal string comparison.
                def _matches(r: str) -> bool:
                    rid, rkind = split_ref(r)
                    return rid == to_id and (kind is None or rkind == kind)

            src.refs = [r for r in src.refs if not _matches(r)]
            src.updated_at = clock.now()
            src.modified_session, _ = actor.current_session()
            await update_frontmatter(
                item_file(self.paths, src), src, base, default_kind=self.spec.default_ref_kind()
            )
            payload: dict[str, object] = {"remove": to_id}
            if kind is not None:
                payload["kind"] = kind
            self.store.log("ref", src.id, payload)
        return src

    async def link_role(self, skill_id: str, role_id: str) -> Item:
        """Scope a skill to a role: write the ``role_id:scopes`` forward edge and immediately
        resync that role's pointer + body (the sanctioned path — a raw ``ref add … --kind
        scopes`` writes the same edge but skips the resync).

        Idempotent: linking a role that is already scoped just re-writes the same edge
        (``add_ref``'s own target dedup) and re-runs the (no-op) resync.
        """
        role = await self.get(role_id)
        if role.type != ROSTER_ROLE:
            raise SquadsError(f"{role_id} is a {role.type}; link-role targets a role")
        updated = await self.add_ref(skill_id, role_id, kind=self.spec.preload_ref_kind())
        await self._resync_role_skills(role.extra.get(X.SLUG, role.slug))
        return updated

    async def unlink_role(self, skill_id: str, role_id: str) -> Item:
        """Remove a skill's ``scopes`` edge to a role and immediately resync that role's
        pointer + body. Only the ``scopes`` edge to *role_id* is removed — any other kind of
        edge between the two items is left alone.

        Idempotent: unlinking a role that was never scoped is a clean no-op (the resync still
        runs, but recomputes the same already-current state).

        A thin wrapper over the kind-aware :meth:`rm_ref` plus the existing partial resync —
        its own observable behaviour (the target-type guard, the single-``scopes``-kind
        removal, the resync) is unchanged from before ``rm_ref`` gained a kind filter.
        """
        role = await self.get(role_id)
        if role.type != ROSTER_ROLE:
            raise SquadsError(f"{role_id} is a {role.type}; unlink-role targets a role")
        updated = await self.rm_ref(skill_id, role_id, kind=self.spec.preload_ref_kind())
        await self._resync_role_skills(role.extra.get(X.SLUG, role.slug))
        return updated

    async def refs_out(self, item_id: str) -> list[tuple[str, str]]:
        """Forward ``(target_id, kind)`` pairs — ``kind`` always spelled, resolving a bare
        wire form to the active spec's declared default."""
        default_kind = self.spec.default_ref_kind()
        return [
            (rid, kind or default_kind)
            for rid, kind in (split_ref(r) for r in (await self.get(item_id)).refs)
        ]

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
        default_kind = self.spec.default_ref_kind()
        out: list[tuple[str, str]] = []
        for it in db.items.values():
            for r in it.refs:
                rid, kind = split_ref(r)
                if ref_id_matches(rid, target_prefix, target_seq):
                    out.append((it.id, kind or default_kind))
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
            A set of ref kinds to follow.  ``None`` (default) means no filter at all — every
            edge traverses, including one whose kind the active spec does not declare (its
            node then reports ``edge_semantic=None``).  An explicit set is checked against
            the declared vocabulary first; a kind the active spec does not declare raises
            :class:`~squads._errors.SquadsError` naming the accepted set — there is no way to
            filter *to* an undeclared kind.
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
        The declared BLOCKER- and DEPENDENT-direction kinds are two spellings of the same
        dependency.  Both collapse onto one declared key —
        :meth:`~squads._workflow._models.WorkflowSpec.canonical_dependency_ref_kind` — on the
        returned :class:`~squads._services._results.GraphNode`'s ``edge_kind``, with
        ``edge_semantic="dependency"`` naming the role a consumer should actually branch on;
        ``direction`` disambiguates the end:

        - ``direction="out"`` → the expanded node depends on the child → display "depends on"
        - ``direction="in"`` → the child depends on the expanded node → display "required by"
        """
        if direction not in ("out", "in", "both"):
            raise SquadsError(f"invalid direction {direction!r}; expected 'out', 'in', or 'both'")

        # `kinds=None` (no --kind passed) means no filter at all — every edge is traversed,
        # declared or not: sq graph may not omit an edge it can see. An explicit
        # `kinds` set is still checked against the declared vocabulary and refused by name if
        # it names a kind the merged spec does not declare; there is no way to filter *to* an
        # undeclared kind, consistent with the refusal shape everywhere else.
        requested_kinds: frozenset[str] | None
        if kinds is None:
            requested_kinds = None
        else:
            declared_kinds = frozenset(self.spec.ref_kinds)
            unknown = kinds - declared_kinds
            if unknown:
                valid = ", ".join(sorted(declared_kinds))
                raise SquadsError(
                    f"unknown ref kind(s): {', '.join(sorted(unknown))}. Valid kinds: {valid}"
                )
            requested_kinds = frozenset(kinds)

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
                edge_semantic=None,
                direction=None,
                seen=False,
                badges=_resolve_badges(self.spec, root_item),
                children=[],
            )

        ctx = _TraversalCtx(
            db_items=db.items,
            depth=depth,
            requested_kinds=requested_kinds,
            direction=direction,
            include_closed=include_closed,
            is_open=self.spec.is_open,
            spec=self.spec,
        )
        # The root node is NOT pre-added to ctx.seen here; _build_graph_node adds it
        # when it first emits the root, before recursing into children.  This ensures
        # the root's own ``seen`` flag is False (not a revisit) while still correctly
        # terminating any cycle that leads back to the root.

        return _build_graph_node(root_item.id, None, None, ctx, 0)

    async def blocked(self) -> list[tuple[Item, list[Item]]]:
        """Open items with ≥1 open blocker, paired with those blockers.

        Two equivalent spellings are supported, resolved through the declared ``dependency``
        semantic rather than a literal kind name — see :meth:`WorkflowSpec.dependency_ref_kind`:
        - The BLOCKER-direction kind (``"A <blocker-kind> B"``): B is blocked while A stays
          open. The edge lives on the *blocker* A; B is the target.
        - The DEPENDENT-direction kind (``"A <dependent-kind> B"``): A is blocked while B stays
          open. The edge lives on the *dependent* A; B is the blocker.

        Either direction may be undeclared (zero is legal for the ``dependency`` capability),
        in which case that half contributes no edges. Both spellings are consumed identically.
        An item blocked through both edges is deduplicated — it appears once with the union of
        its open blockers.
        """
        db = await self.store.load()
        blocker_kind = self.spec.dependency_ref_kind("blocker")
        dependent_kind = self.spec.dependency_ref_kind("dependent")
        # keyed by the blocked item's id; value is a set of blocker ids (dedup)
        blockers_by_target: dict[str, set[str]] = {}
        for it in db.items.values():
            for r in it.refs:
                rid, kind = split_ref(r)
                if blocker_kind is not None and kind == blocker_kind:
                    # it <blocker-kind> rid → rid is the blocked item, it is the blocker
                    blockers_by_target.setdefault(rid, set()).add(it.id)
                elif dependent_kind is not None and kind == dependent_kind:
                    # it <dependent-kind> rid → it is the blocked item, rid is the blocker
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
