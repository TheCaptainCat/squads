"""Forward reference edges (typed cross-links); backrefs are computed by inversion."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from squads import _actor as actor
from squads import _badges as badges
from squads import _clock as clock
from squads._errors import SquadsError
from squads._index._resolver import require_item
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
    """Immutable traversal parameters threaded through the BFS helpers. ``requested_kinds`` is only
    the caller's ``--kind`` filter (``None`` means every edge is seen, declared or not), never the
    declared set, which comes from ``spec.ref_kinds`` (see :func:`_edge_semantic`); conflating them
    would make an undeclared kind vanish silently.
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
    """Outgoing ref neighbours as (target_id, edge_kind, direction). ``edge_kind`` is the normalized
    dependency kind (:meth:`WorkflowSpec.canonical_dependency_ref_kind`) for either raw spelling,
    and ``direction`` is from the expanded item's side. A raw BLOCKER-direction edge becomes the
    canonical kind with ``direction="in"``; every other kind keeps its literal kind and ``"out"``.
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
    """Inbound ref neighbours as (source_id, edge_kind, direction), found by walking every item in
    the snapshot; ``direction`` is from the expanded item's side. A neighbour's DEPENDENT-direction
    edge gives the canonical kind with ``"in"``, its BLOCKER-direction edge the canonical kind with
    ``"out"``, and any other kind keeps its kind with ``"in"``.
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
        # Defensive guard: callers skip dangling refs before recursing, but a future caller must
        # not crash on one.
        return GraphNode(
            id=item_id,
            type="",
            status="",
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

    node = GraphNode(
        id=item.id,
        type=item.type,
        status=item.status,
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
        assignee=node.assignee,
        edge_kind=node.edge_kind,
        edge_semantic=node.edge_semantic,
        direction=node.direction,
        seen=node.seen,
        badges=node.badges,
        children=children,
    )


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
        """The pure half of a ref-add (no file I/O), shared with the bulk importer's pre-pass.
        Returns ``(src, base)``, *base* being *src* as loaded for the skew guard. ``kind=""``
        resolves to ``self.spec.default_ref_kind()``, and the edge is written bare
        (:func:`~squads._models._item.make_ref`) exactly when the kind is that default, keeping one
        on-disk encoding per edge.
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
        # The kind rides with the edge; re-adding updates it. Dedup by (prefix, seq) so a stored
        # ref of an old width is replaced across a repad, since file contents are never rewritten.
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
        await self._refuse_duplicated_ids(require_item(db, from_id))
        src, base = self._add_ref_model(db, from_id, to_id, kind=kind)
        await self._update_item_frontmatter(src, base)
        self.store.log(
            "ref",
            src.id,
            {"add": to_id, "kind": kind or default_kind},
        )
        return src

    async def rm_ref(self, from_id: str, to_id: str, *, kind: str | None = None) -> Item:
        """Remove a forward ref edge from *from_id* to *to_id*. ``kind=None`` drops every edge to
        *to_id*; an explicit ``kind`` removes only edges of that kind, the primitive
        :meth:`unlink_role` and the retirement gate's ``--unlink`` build on. Removing an edge the
        item lacks is refused.
        """
        async with self.store.transaction() as db:
            src = require_item(db, from_id)
            await self._refuse_duplicated_ids(src)
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

            kept = [r for r in src.refs if not _matches(r)]
            if len(kept) == len(src.refs):
                what = "ref" if kind is None else f"{kind} ref"
                raise SquadsError(f"{src.id} has no {what} to {to_id}")
            src.refs = kept
            src.updated_at = clock.now()
            src.modified_session, _ = actor.current_session()
            await self._update_item_frontmatter(src, base)
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
        await self.roster_projection.resync_role_skills(role.slug)
        return updated

    async def unlink_role(self, skill_id: str, role_id: str) -> Item:
        """Remove a skill's ``scopes`` edge to a role and resync that role's pointer and body; other
        kinds of edge between the two are left alone. Refused when the skill is not scoped to the
        role. A thin wrapper over the kind-aware :meth:`rm_ref` and the partial resync.
        """
        role = await self.get(role_id)
        if role.type != ROSTER_ROLE:
            raise SquadsError(f"{role_id} is a {role.type}; unlink-role targets a role")
        updated = await self.rm_ref(skill_id, role_id, kind=self.spec.preload_ref_kind())
        await self.roster_projection.resync_role_skills(role.slug)
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
        """Build an ego-centric BFS ref graph rooted at *root_id*, *depth* hops out (default 2), in
        *direction* ``"out"``, ``"in"`` or ``"both"``, with closed items only under
        *include_closed*; revisited nodes appear once with ``seen=True``. *kinds* ``None`` follows
        every edge, even an undeclared kind; an explicit set must be declared or
        :class:`~squads._errors.SquadsError` names the accepted set. Both dependency kinds collapse
        onto the canonical one with ``edge_semantic="dependency"``.
        """
        if direction not in ("out", "in", "both"):
            raise SquadsError(f"invalid direction {direction!r}; expected 'out', 'in', or 'both'")

        # kinds=None follows every edge, declared or not (sq graph may not omit an edge it can
        # see); an explicit set must be declared, as everywhere else.
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
        # The root is not pre-added to ctx.seen: _build_graph_node adds it when it emits the root,
        # so its own `seen` is False while a cycle back to it still terminates.

        return _build_graph_node(root_item.id, None, None, ctx, 0)

    async def blocked(self) -> list[tuple[Item, list[Item]]]:
        """Open items with at least one open blocker, paired with those blockers. Both dependency
        spellings are consumed identically, resolved through the declared ``dependency`` semantic
        (:meth:`WorkflowSpec.dependency_ref_kind`): ``A <blocker-kind> B`` blocks B and ``A
        <dependent-kind> B`` blocks A. Either may be undeclared, and an item blocked both ways
        appears once with the union of its blockers.
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
