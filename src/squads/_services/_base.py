"""The shared service core: state, backend access, and the primitives every concern builds on.

Each concern lives in its own ``_services/_*.py`` mixin subclassing ``ServiceCore``; the public
``Service`` (in ``_service.py``) multiply-inherits them. ``ServiceCore`` defines what's used across
concerns (create/get/list, the backend, the role/skill lookups + roster projection) so the mixins
only ever call core methods + their own.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from squads import _actor as actor
from squads import _clock as clock
from squads import _discussion as discussion
from squads import _sections as sections
from squads._backends._base import AgentBackend, BackendContext, OperatorView, RoleView
from squads._backends._registry import get_backend
from squads._errors import ItemNotFoundError, SquadsError
from squads._index._resolver import item_file, require_item
from squads._index._store import IndexStore
from squads._interactions import (
    DEV,
    GREETING_SKILL,
    MEMORY_SKILL,
    SQUADS_SKILL,
    active_skill_slugs,
    allowed_create_types,
    custom_item_skill_commands,
    get_playbook_spec,
    in_lane_owner,
    is_dev_slug,
    is_lane_exempt,
    is_live_roster_entry,
    is_system_skill,
    item_skill_name,
    laned_types,
    skills_for_role,
)
from squads._interactions._models import ItemPlaybookSpec, PlaybookSpec
from squads._itemfile import (
    ensure_no_skew,
    read_item_text,
    write_new,
    write_text,
)
from squads._models import _markers as markers
from squads._models._extras import ExtraKey as X
from squads._models._index import SquadsDB
from squads._models._item import Item, effective_prefix, make_ref, ref_id_matches, split_ref
from squads._models._vocab import label_for, prefix_for
from squads._paths import SquadPaths, number_for_id
from squads._rendering._engine import render, set_active_squad_dir
from squads._roles._catalog import RoleDef
from squads._roles._resolver import (
    holds_default_designation,
    resolve_role,
    resolve_role_for_item,
)
from squads._services._results import CreateResult, TreeNode
from squads._services._validators import ValidatorEngine
from squads._util import slugify
from squads._workflow import (
    ROSTER_OPERATOR,
    ROSTER_ROLE,
    ROSTER_SKILL,
    bundled_spec,
    dropped_via_selected,
    linearize_lifecycle,
)
from squads._workflow._models import Field, WorkflowSpec


# Body-local sub-entities: kind <-> parent item type, and the kind's container marker.
#
# These are derived from the ACTIVE spec's per-type `subentity_kind` (forward edge, invariant
# #4) rather than a hand-maintained literal dict, and rather than the bundled default — a
# project-declared type/kind must be visible here too. Free functions (not module constants)
# because the active spec is per-service, not global; ServiceCore exposes them as instance
# properties below so mixins read `self.subentity_parent`/`self.subentity_kind`/
# `self.subentity_container` and non-mixin callers (e.g. retype) pass a spec explicitly.
def subentity_parent_map(spec: WorkflowSpec) -> dict[str, str]:
    """Sub-entity kind -> ONE hosting item type, inverted from the spec's declared
    ``ItemSpec.subentity_kind``.

    The type<->kind relation is 1:many (two item types may declare the same kind, e.g.
    a project-declared type mirroring ``task``'s ``subentity_kind="subtask"``) — this
    inversion collapses that to a single representative type per kind, so it is only a
    naming HINT (e.g. for a help string) and must never back an ownership/validation
    decision. Use ``spec.item_subentity_kind(item.type) == kind`` (forward, 1:1) for that.
    """
    return {ts.subentity_kind: t for t, ts in spec.items.items() if ts.subentity_kind}


def subentity_kind_map(spec: WorkflowSpec) -> dict[str, str]:
    """Item type -> sub-entity kind, read directly off the spec (genuinely 1:1 per type;
    NOT built by inverting :func:`subentity_parent_map`, which would drop every type that
    map's inversion collapsed away)."""
    return {t: ts.subentity_kind for t, ts in spec.items.items() if ts.subentity_kind}


def subentity_container_map(spec: WorkflowSpec) -> dict[str, str]:
    """Sub-entity kind -> container marker tag — simply the kind's declared ``plural``."""
    return {kind: ks.plural for kind, ks in spec.subentity_kinds.items()}


def ensure_subentity_container_text(spec: WorkflowSpec, item_type: str, text: str) -> str:
    """Append an empty sub-entity container block to *text* when *item_type* hosts a
    sub-entity kind and the block is not already present (idempotent — see
    :func:`squads._discussion.ensure_container`).

    The single primitive behind every path that can produce an item file for a
    sub-entity-hosting type: item creation (``_create_core`` below, so a type with no
    per-type template — or a renamed kind on one that has a stale hardcoded tag — still
    gets a working container) and retype (``_services._retype``, which appends this to an
    existing file after moving it to its new type). Tag and heading both come from the
    *active* spec (``subentity_plural``/``subentity_container_heading``), never from a
    template's own hardcoded literal.
    """
    kind = subentity_kind_map(spec).get(item_type)
    if kind is None:
        return text
    container_tag = spec.subentity_plural(kind)
    heading = spec.subentity_container_heading(kind)
    return discussion.ensure_container(text, heading, container_tag)


@dataclass(frozen=True)
class ItemFilter:
    """The shared list/tree filter spec.  One match predicate, used by both ``list_items``
    and ``tree_view`` so the two commands can never drift.

    All fields default to ``None`` (no constraint on that dimension).  ``matches()``
    applies every non-``None`` field as an AND condition.  ``is_empty()`` is True when no
    field is set — an empty filter matches every item.
    """

    item_type: str | None = None
    status: str | None = None
    parent: str | None = None
    label: str | None = None
    assignee: str | None = None
    #: Category filter (``roster``/``work``/``records``) — matches when the item's type
    #: declares this category. Needs ``spec`` to resolve (graceful no-match without it,
    #: mirroring ``badge_min``); the value itself is validated at the CLI edge against the
    #: fixed category catalog (``squads._workflow.CATEGORIES``), not here.
    category: str | None = None
    #: Exact badge-field filters, keyed by field CODE (e.g. ``priority``, or a project's own
    #: custom axis) — generic over ``fields_for()``, not a hand-written priority-only param.
    badges: tuple[tuple[str, str], ...] = ()
    #: Threshold badge-field filters (ordered collections only): (field code, minimum code).
    #: Resolving "at least as high as" needs the field's declared collection, so this variant
    #: is only usable when ``spec`` is set.
    badge_min: tuple[tuple[str, str], ...] = ()
    #: The active spec — needed only to resolve ``badge_min`` rank and ``category``;
    #: ``None`` disables both.
    spec: WorkflowSpec | None = None

    def matches(self, it: Item) -> bool:
        """Return True iff *it* satisfies every non-None dimension of this filter."""
        base = (
            (not self.item_type or it.type == self.item_type)
            and (not self.status or it.status == self.status)
            and (not self.parent or it.parent == self.parent)
            and (not self.label or self.label in it.labels)
            and (not self.assignee or it.assignee == self.assignee)
            and (not self.category or self._category_of(it) == self.category)
        )
        if not base:
            return False
        if any(it.badge_value(code) != want for code, want in self.badges):
            return False
        return all(self._meets_min(it, code, min_code) for code, min_code in self.badge_min)

    def _category_of(self, it: Item) -> str | None:
        """The declared category of *it*'s type, or ``None`` when unresolvable (no active
        spec, or the type is not declared in it) — a graceful non-match, never a crash."""
        if self.spec is None:
            return None
        ts = self.spec.items.get(it.type)
        return ts.category if ts else None

    def _meets_min(self, it: Item, code: str, min_code: str) -> bool:
        """True when *it*'s badge for *code* ranks at least as high as *min_code* (lower
        index = higher-ranked). Unresolvable (no spec, no field, no ordered collection, or
        an unrecognised code) is a graceful non-match, never a crash."""
        if self.spec is None:
            return False
        field = next((f for f in self.spec.fields_for(it.type) if f.code == code), None)
        coll = self.spec.collections.get(field.collection) if field else None
        if coll is None:
            return False
        order = [b.code for b in coll.badges]
        value = it.badge_value(code)
        return value in order and min_code in order and order.index(value) <= order.index(min_code)

    def is_empty(self) -> bool:
        """Return True when no filter dimension is set (matches all items)."""
        return not any(
            (
                self.item_type,
                self.status,
                self.parent,
                self.label,
                self.assignee,
                self.category,
                self.badges,
                self.badge_min,
            )
        )


def _compute_keep_set(
    match_set: set[str],
    id_map: dict[str, Item],
    seq_to_id: dict[int, str],
) -> set[str]:
    """Return match_set UNION all ancestors of each matched item.

    Walks parent links upward through the candidate set (width-tolerant via sequence
    numbers).  Items whose parent is not in the candidate set are treated as roots.

    Each walk carries its own visited set of sequence numbers, so a parent relation holding a
    cycle terminates instead of alternating between the same items forever.  Identity is the
    sequence number rather than the id string for the same width-tolerance reason the
    ``seq_to_id`` resolution above exists: a stored parent may carry a different zero-pad
    width than the item's own id, and comparing id strings would walk straight past the
    repeat.  The revisited ancestor is still added to the keep set before the walk stops, so a
    cyclic pair renders as the hierarchy someone actually wrote rather than half of it.
    """
    keep_set: set[str] = set(match_set)
    for mid in match_set:
        item = id_map.get(mid)
        seen: set[int] = set() if item is None else {item.sequence_id}
        while item is not None and item.parent is not None:
            p_seq = number_for_id(item.parent)
            canonical = seq_to_id.get(p_seq)
            if canonical is None or canonical not in id_map:
                break
            keep_set.add(canonical)
            if p_seq in seen:
                break
            seen.add(p_seq)
            item = id_map.get(canonical)
    return keep_set


def _walk_tree(
    it: Item,
    current_depth: int,
    *,
    keep_set: set[str],
    match_set: set[str],
    children_map: dict[str | None, list[Item]],
    depth: int | None,
    ancestors: frozenset[int] = frozenset(),
    anchor: bool = False,
) -> TreeNode | None:
    """Recursive downward walk that prunes to *keep_set* and bounds to *depth*.

    Returns ``None`` when the node should be dropped (not in keep set, already on the path
    from the root, or a path-only anchor with no surviving children).  ``depth`` is measured
    from the root (root = level 0); ``None`` means unbounded.

    *ancestors* is the set of sequence numbers already on the path from the root — the
    cycle guard.  A parent relation holding a cycle would otherwise recurse until
    ``RecursionError``: this is a second, independent cycle-unsafe walk from the upward one in
    :func:`_compute_keep_set`, not the same fault seen twice, and it is reachable through the
    public path whenever the tree is rooted inside the cycle.  Truncating (dropping the repeat)
    rather than rendering it again is what keeps an item from appearing twice on one path,
    which the renderer's indentation would present as a real, deeper node.

    Identity is the **sequence number**, not the id string, for the same width-tolerance reason
    :func:`_build_tree_children` resolves parents that way: a stored parent may carry a
    different zero-pad width than the item's own id.

    *anchor* is passed by the caller for a root the bare form invented to reveal a parent cycle
    (:func:`_cycle_anchor_ids`) and is carried onto that node alone — the recursion never
    propagates it, because the fabricated-root disclosure is about this node's standing in the
    forest, not about its descendants.
    """
    if it.id not in keep_set or it.sequence_id in ancestors:
        return None
    path_only = it.id not in match_set
    child_nodes: list[TreeNode] = []
    if depth is None or current_depth < depth:
        for child in sorted(children_map.get(it.id, []), key=lambda i: number_for_id(i.id)):
            child_node = _walk_tree(
                child,
                current_depth + 1,
                keep_set=keep_set,
                match_set=match_set,
                children_map=children_map,
                depth=depth,
                ancestors=ancestors | {it.sequence_id},
            )
            if child_node is not None:
                child_nodes.append(child_node)
    # Drop a path_only anchor with no surviving children (would be an empty branch)
    if path_only and not child_nodes:
        return None
    return TreeNode(item=it, path_only=path_only, children=child_nodes, anchor=anchor)


def _cycle_anchor_ids(listed: list[Item]) -> set[str]:
    """Return one anchor id per parent cycle in *listed*: the lowest sequence number on it.

    A bare tree roots at the forest of items with no resolvable parent *in view*.  Every member
    of a parent cycle has one — another member — so without an anchor the whole component, and
    everything hanging below it, is absent from the bare tree while ``list`` still returns it.
    This picks one member per cycle for the forest to root at; the descent from it already
    renders the component, truncated at the repeat.

    **The anchor comes from the items on the cycle**, never from "the lowest item not rendered
    yet".  The two rules agree on most corpora and differ where it hurts: an item hanging
    *below* the cycle with a lower sequence number satisfies the second rule, so it would anchor
    itself and then render a second time as a child when the descent reaches it through the
    cycle — one item at two places in one tree, which the indentation presents as two nodes.

    One anchor per cycle is sufficient rather than hopeful.  Each item has at most one
    resolvable parent, so the graph is functional: every upward walk either reaches an item with
    no resolvable parent (a root the forest already carries) or runs into exactly one cycle,
    cycles are disjoint, and nothing in a component sits *above* its cycle because a cycle
    member's parent is always another cycle member.  The descent from any single member
    therefore reaches the whole component, and no item is reachable from two anchors.

    Computed on the **candidate set the roots come from**, never on the whole index.  A cycle in
    the corpus is not necessarily a cycle in the view: filter one member out and the survivors
    are an ordinary chain whose top already has no resolvable parent, already becomes a root and
    already renders.  Detecting against the index would invent an anchor for a component that is
    not broken, or name one that is not in the view at all.

    Identity is the sequence number, not the id string, for the same width-tolerance reason
    :func:`_build_tree_children` resolves parents that way: a stored parent may carry a different
    zero-pad width than the item's own id, and comparing id strings walks straight past the
    repeat.
    """
    seq_to_id: dict[int, str] = {number_for_id(i.id): i.id for i in listed}
    parent_of: dict[int, int] = {}
    for it in listed:
        if not it.parent:
            continue
        parent_seq = number_for_id(it.parent)
        if parent_seq in seq_to_id:
            parent_of[number_for_id(it.id)] = parent_seq

    anchors: set[str] = set()
    settled: set[int] = set()  # every sequence whose upward walk has already been resolved
    for start in seq_to_id:
        if start in settled:
            continue
        position: dict[int, int] = {}  # sequence -> where it sits on the current walk
        walk: list[int] = []
        node: int | None = start
        while node is not None and node not in settled:
            if node in position:  # the walk closed on itself: everything from here is the cycle
                anchors.add(seq_to_id[min(walk[position[node] :])])
                break
            position[node] = len(walk)
            walk.append(node)
            node = parent_of.get(node)
        settled.update(walk)
    return anchors


def _build_tree_children(
    listed: list[Item],
) -> dict[str | None, list[Item]]:
    """Group items by their canonical parent ID (width-tolerant).

    ``item.parent`` may store an old zero-pad width after ``sq migrate repad`` while
    ``item.id`` uses the current width.  Resolving via sequence number makes the tree
    correct across a repad boundary.

    Used by ``tree_view`` and shared by any future caller that needs the same
    parent-resolution logic; keeps parent resolution in one place.
    """
    all_ids = {i.id for i in listed}
    seq_to_id: dict[int, str] = {number_for_id(i.id): i.id for i in listed}
    children: dict[str | None, list[Item]] = {}
    for it in listed:
        parent_canonical: str | None = None
        if it.parent:
            canonical = seq_to_id.get(number_for_id(it.parent))
            if canonical is not None and canonical in all_ids:
                parent_canonical = canonical
        children.setdefault(parent_canonical, []).append(it)
    return children


def reject_markers(text: str, what: str = "body") -> None:
    """Raise ``SquadsError`` when *text* contains a well-formed sq marker tag.

    All prose inputs that land inside marker-delimited regions must pass through this guard
    before any file write. The ``what`` label appears in the message (e.g. ``"body"``,
    ``"comment message"``, ``"title"``).

    **Every label gets the remediation guidance**, including the default ``"body"`` one. It
    used to get a terse variant, kept that way so existing callers and tests stayed unchanged —
    a test-compatibility argument, and the worse message was sitting on the busiest path:
    ``body`` is the default, so the item body, both sub-entity body writers and the shared
    section-edit core all took it.

    The guidance is what makes the refusal defensible rather than merely strict. Now that the
    tag class recognises mixed-case sub-entity region tags, the likeliest way to trip this
    guard is quoting one while *writing about* the marker system — and an author who does that
    reaches for backticks first, which do not help. Telling them what to write instead is the
    difference between a guard and an obstacle.
    """
    if not sections.find_markers(text):
        return
    raise SquadsError(
        f"{what} must not contain sq marker comments (<!-- sq:… -->). "
        "Write the tag without its HTML-comment wrapper (e.g. sq:body rather than "
        "the comment form) — backtick-wrapping does not neutralize a well-formed tag."
    )


#: How many leading lines of the body about to be discarded the refusal quotes back.  Enough to
#: recognise the content, short enough that the message stays readable in a terminal.
BODY_OVERWRITE_PREVIEW_LINES = 3


def reject_body_overwrite(target: str, current: str) -> None:
    """Raise ``SquadsError`` rather than let a plain ``body`` write discard authored prose.

    ``body`` replaces, and until this guard existed it replaced silently: one
    ``sq <type> <n> body -m "probe"`` against an occupied body destroyed the prose with a
    success line and no way to get it back short of git.

    The refusal — not a prompt — is the deliberate choice.  Agents are the primary caller here
    and cannot answer an interactive confirmation; a prompt would either hang/abort every
    non-interactive body write or immediately grow a skip flag that is passed reflexively.  A
    refusal is a clean, scriptable exit that costs nothing on the common path (a first write
    against an unwritten template scaffold never trips it) and, when it does fire, hands back
    the line count and the opening lines of what was at stake **before** anything is written.
    That also makes the default invocation its own dry run: "would this be permitted here?"
    is now answerable without performing the destruction.

    *target* is how the message names the thing being written — an item id on its own for an
    item body, the item id plus the block's local id for a sub-entity's; *current* is the body
    region content that would be discarded.
    """
    lines = current.splitlines()
    head = "\n".join(f"    {line}" for line in lines[:BODY_OVERWRITE_PREVIEW_LINES])
    rest = len(lines) - BODY_OVERWRITE_PREVIEW_LINES
    if rest > 0:
        head += f"\n    … ({rest} more line{'s' if rest != 1 else ''})"
    raise SquadsError(
        f"{target} already has a body ({len(lines)} line{'s' if len(lines) != 1 else ''}); "
        f"setting one would discard it:\n\n{head}\n\n"
        "Nothing was written. Add to it with `--append`, or pass `--force` to replace it."
    )


def _item_skill_role_sections(
    pb: ItemPlaybookSpec | None, roster: list[RoleView]
) -> list[dict[str, Any]]:
    """The ordered per-role section blocks ``agents/item_skill.md.j2`` renders for one item
    type — empty for a type the active playbook does not cover (the thin skill's "no role
    sections" degradation).

    Two filters, both roster-dependent, which is why a before/after diff of generated skill
    text only means anything with the roster held constant:

    - the shared ``developers`` section (the ``*dev`` sentinel guide) renders only when the
      roster carries at least one ``<tech>-dev`` role, so a squad with no developer yet does
      not carry guidance for an actor that cannot act;
    - a named role's guide renders only while that role is in the live roster.
    """
    if pb is None:
        return []
    by_slug = {r.slug: r for r in roster}
    has_dev = any(is_dev_slug(r.slug) for r in roster)
    out: list[dict[str, Any]] = []
    for guide in pb.roles:
        if guide.slug == DEV:
            if not has_dev:
                continue
            title = "developers"
        elif guide.slug in by_slug:
            r = by_slug[guide.slug]
            title = f"{r.full_name} (`{r.slug}`)"
        else:
            continue
        out.append(
            {
                "title": title,
                "enter": guide.enter,
                "do": guide.do,
                "handoff": guide.handoff,
                "watch": guide.watch,
            }
        )
    return out


class ServiceCore:
    def __init__(
        self,
        paths: SquadPaths,
        spec: WorkflowSpec | None = None,
        playbook: PlaybookSpec | None = None,
    ):
        self.paths = paths
        # Use the supplied spec, or fall back to the immutable bundled default.
        # open_service() always supplies the resolved (possibly overridden) spec;
        # sq init / sq adopt construct Service(sp) without an override spec, which
        # is fine because they operate on a fresh squad with no override file yet.
        self.spec: WorkflowSpec = spec if spec is not None else bundled_spec()
        # Same shape, one release later: open_service() resolves the merged playbook
        # (bundled base + .overrides/playbook.toml, coverage-checked against self.spec) and
        # threads it here; a caller with no playbook in hand gets the bundled singleton — the
        # same "fine because there's no override file yet" reasoning as the spec fallback above.
        self.playbook: PlaybookSpec = playbook if playbook is not None else get_playbook_spec()
        self.store = IndexStore(paths.index_path, paths.lock_path, spec=self.spec)
        # Activate the squad-aware template search path so render() picks up any project
        # overrides under <squad_dir>/.overrides/templates/ for this service's squad.
        set_active_squad_dir(paths.squad_dir)

    # ------------------------------------------------------------------ sub-entity vocabulary
    # Resolved from THIS service's active spec (self.spec), not the bundled default — a
    # project-declared type/kind is visible here with no code change.
    @property
    def subentity_parent(self) -> dict[str, str]:
        """Sub-entity kind -> hosting item type."""
        return subentity_parent_map(self.spec)

    @property
    def subentity_kind(self) -> dict[str, str]:
        """Item type -> sub-entity kind (inverse of ``subentity_parent``)."""
        return subentity_kind_map(self.spec)

    @property
    def subentity_container(self) -> dict[str, str]:
        """Sub-entity kind -> container marker tag."""
        return subentity_container_map(self.spec)

    def _template_for(self, item_type: str) -> str:
        """Return the Jinja2 template path for ``item_type``.

        Built-in types have a dedicated ``items/<type>.md.j2`` and are returned
        directly.  Custom types (no per-type template) fall back to the generic
        ``items/_default.md.j2`` so ``svc.create('incident', …)`` does not raise
        ``TemplateNotFound``.  The fallback is resolved via the Jinja2 environment's
        ``has_template`` check so user-supplied overrides in
        ``.overrides/templates/items/<type>.md.j2`` are still honoured.
        """
        if self.spec.item_is_roster(item_type):
            return f"agents/{item_type}.md.j2"
        per_type = f"items/{item_type}.md.j2"
        from squads._rendering._engine import has_template

        if has_template(per_type):
            return per_type
        return "items/_default.md.j2"

    def pristine_body(self, item: Item) -> str | None:
        """The ``:body`` region a freshly-created *item* of this type would carry — i.e. the
        template's unwritten placeholder scaffold (``## Description`` / ``_TODO: …_``), not the
        empty string.

        This is what tells "nobody has written this body yet" apart from "this body holds 66
        lines of someone's work", and it has to be *derived* rather than pattern-matched: the
        scaffold differs per type, interpolates (``items/_default.md.j2`` names the type,
        ``items/review.md.j2`` reads ``extra.target_ref``), and an adopter can replace it
        wholesale via ``.overrides/templates/items/<type>.md.j2``.  Re-rendering through the
        same squad-aware loader that produced the file is the only answer that stays true for
        all three.

        ``None`` when the scaffold cannot be reproduced (a template that no longer renders for
        this item).  Callers must read that as "assume authored" — refusing a first write is
        recoverable, discarding a real body is not.
        """
        from jinja2 import TemplateError

        try:
            rendered = render(
                self._template_for(item.type),
                item=item,
                description=item.description,
                extra=item.extra,
                spec=self.spec,
            )
        except TemplateError:
            return None
        return (sections.get_section(rendered, markers.BODY) or "").strip("\n")

    # ------------------------------------------------------------------ backend
    @property
    def _ctx(self) -> BackendContext:
        return BackendContext(paths=self.paths, spec=self.spec, playbook=self.playbook)

    def _backends(self) -> list[AgentBackend]:
        """Return one backend instance for each active (deduped) backend name.

        Empty ``active_backends`` returns an empty list (sq-only squad).
        """
        return [get_backend(name) for name in self.paths.config.active_backends]

    async def scaffold_backend(self) -> None:
        """Public entry for init(): create backend scaffolding for every active backend."""
        ctx = self._ctx
        for backend in self._backends():
            await backend.ensure_scaffold(ctx)

    # ------------------------------------------------------------------ create / read
    async def create(  # noqa: PLR0913 — a creation entrypoint with clear keyword-only fields
        self,
        item_type: str,
        title: str,
        *,
        description: str = "",
        parent: str | None = None,
        author: str | None = None,
        labels: list[str] | None = None,
        refs: list[str] | None = None,
        assignee: str | None = None,
        priority: str | None = None,
        extra: dict[str, Any] | None = None,
        status: str | None = None,
        slug: str | None = None,
        body: str | None = None,
        fields: dict[str, str] | None = None,
    ) -> CreateResult:
        """Create an item — opens its own transaction, then delegates to :meth:`_create_core`.

        The bulk-importer calls :meth:`_create_core` directly (its own single transaction is
        already open), so this wrapper stays a thin two-liner and the mutation logic lives in
        exactly one place.
        """
        async with self.store.transaction() as db:
            return await self._create_core(
                db,
                item_type,
                title,
                description=description,
                parent=parent,
                author=author,
                labels=labels,
                refs=refs,
                assignee=assignee,
                priority=priority,
                extra=extra,
                status=status,
                slug=slug,
                body=body,
                fields=fields,
            )

    def _default_role_slug(self, db: SquadsDB) -> str | None:
        """This squad's own ``is_default`` role slug, read from the live roster in *db*.

        The lane exemption belongs to whichever role this squad designates as its
        coordinator, not to a slug spelled in the engine — ``sq role <slug> set-default`` moves
        that designation, and the exemption has to move with it. Returns ``None`` when no live
        role holds it, which is what a squad that retired its coordinator gets — a legitimate
        state, not a gap to paper over; the caller falls back to the role catalog's own
        designation there (:func:`~squads._interactions.catalog_default_slug`).

        The designation goes through :func:`~squads._roles._resolver
        .holds_default_designation`, not a raw ``extra.is_default`` read: the stored key is an
        override on an answer the role catalog also gives, so a role designated by a project's
        own ``.overrides/roles.toml`` carries nothing in its ``extra`` and a raw read would hand
        the exemption to the bundled catalog's role instead of this squad's.
        """
        live = self.spec.live_statuses(ROSTER_ROLE)
        for it in db.items.values():
            if (
                it.type == ROSTER_ROLE
                and it.status in live
                and holds_default_designation(it, self.paths.squad_dir)
            ):
                return it.extra.get(X.SLUG, it.slug)
        return None

    def _create_model(  # noqa: PLR0913 — mirrors `create`'s own keyword surface
        self,
        db: SquadsDB,
        item_type: str,
        title: str,
        *,
        description: str = "",
        parent: str | None = None,
        author: str | None = None,
        labels: list[str] | None = None,
        refs: list[str] | None = None,
        assignee: str | None = None,
        priority: str | None = None,
        extra: dict[str, Any] | None = None,
        status: str | None = None,
        slug: str | None = None,
        body: str | None = None,
        fields: dict[str, str] | None = None,
        now: datetime | None = None,
    ) -> tuple[Item, str | None]:
        """The PURE half of create: every check, the id allocation, and the ``Item`` itself —
        no file I/O. Returns ``(item, lane_warning)``.

        Shared by :meth:`_create_core` (the interactive/apply path, which renders + writes the
        file around this) and the bulk importer's validate-first pre-pass (which calls this
        directly against a throwaway, never-persisted ``db`` copy to *simulate* a create —
        including the id allocation, invariant #2's "simulate only" contract — with the exact
        same checks the real path runs, rather than a parallel hand-duplicated validator).

        ``now`` lets the pre-pass supply the event's own forged ``at`` explicitly instead of
        reading the ambient clock — the apply path leaves it ``None`` and rides the ambient
        clock the per-event ``RequestContext`` rebind already set.

        ``fields`` is a generic badge-code map (e.g. ``{"priority": "high", "severity": "…"}``)
        applied via :meth:`~squads._models._item.Item.set_badge_value` after the dedicated
        ``priority`` kwarg — additive, so a code also present in ``fields`` simply wins.

        ``author`` has no default: attribution is only knowable at the call site, so a caller
        that omits it fails here rather than silently acquiring the squad's configured default
        role. Kept keyword-with-default (rather than a hard-required parameter) only because
        the wider test suite has hundreds of unrelated call sites that don't yet pass one —
        making it syntactically required would turn every one of those into a static (pyright)
        error instead of the same runtime one; every *production* caller (CLI, the roster
        mixin, the bulk importer) already supplies it explicitly.
        """
        item_type = str(item_type)  # coerce StrEnum members to plain str
        # Membership gate: every downstream lookup below (`item_is_roster`, `initial_status`,
        # `prefix_for`, …) indexes `self.spec.items[item_type]` unguarded, so a type absent
        # from the active spec — dropped via `[selected]`, or simply never declared — must be
        # refused right here rather than surfacing as a raw KeyError from whichever lookup
        # happens to run first. Mirrors the read path's existing "unknown item type" refusal —
        # and is also the CLI's own refusal for this case (`sq create <type>` keeps the type's
        # command registered and dispatches into it rather than hiding it from Click's own
        # unknown-command handling, precisely so this message is what the caller sees).
        if item_type not in self.spec.items:
            # `dropped_via_selected` is the shared "was this a bundled type the active spec no
            # longer declares" check (`_workflow/__init__.py`) — the same reasoning the loader's
            # deselection-provenance annotation already applies to floor violations, and the
            # read path's own refusal (`resolve_item_id_typed` in `_cli/_common.py`) uses too.
            if dropped_via_selected(item_type, self.spec):
                raise SquadsError(
                    f"unknown item type {item_type!r}: {item_type!r} was dropped from a "
                    "[selected] list (selected.items) in .overrides/workflow.toml, not left "
                    "undeclared — add it back to selected.items to restore it"
                )
            raise SquadsError(
                f"unknown item type {item_type!r}: no spec supplied, or the spec does not "
                "declare this type. Declare it in .overrides/workflow.toml or check for a typo."
            )
        slug = slug or slugify(title)
        if refs:
            # Validate every declared kind, then rewrite the set to the canonical wire form —
            # the same normalisation `add_ref`/the bulk importer's `_resolve_refs` already
            # apply: an edge whose kind is the declared default is always written bare, never
            # spelled out (the encoding invariant), so a caller-supplied "ID:<default-kind>"
            # never reaches the file or the index spelled. Both halves happen here, at the one
            # PURE seam every create path (CLI, direct `Service.create()`, and the bulk
            # importer's simulate/apply pair) shares — never re-derived per caller.
            default_kind = self.spec.default_ref_kind()
            normalised_refs: list[str] = []
            for ref_str in refs:
                rid, kind = split_ref(ref_str)
                # A bare/unspelled kind ("") is always valid — it names whichever declared
                # entry carries role="default", which is guaranteed to exist and be accepted.
                if kind and kind not in self.spec.ref_kinds:
                    valid = ", ".join(sorted(self.spec.ref_kinds))
                    raise SquadsError(f"unknown ref kind {kind!r}. Valid kinds: {valid}")
                normalised_refs.append(make_ref(rid, "" if kind == default_kind else kind))
            refs = normalised_refs
        if body is not None:
            reject_markers(body)
        effective_now = now if now is not None else clock.now()
        if parent:
            self._check_parent(db, item_type, parent)
        if not author:
            raise SquadsError("author is required: the actor's slug")
        self._check_author(db, item_type, author, slug)
        self._check_assignee(db, assignee)
        # Resolve the prefix from the spec before allocation so both the filename and
        # Item.id agree on the correct prefix.
        resolved_prefix = prefix_for(item_type, self.spec)
        # item_id is the padded filename stem (SquadsDB.allocate_id formats at db.padding);
        # deliberately NOT the same width as the displayed Item.id.
        item_id = db.allocate_id(item_type, prefix=resolved_prefix)
        filename = f"{item_id}-{slug}.md"
        squad_rel = self.paths.squad_relative(item_type, filename, spec=self.spec)
        sid, _psid = actor.current_session()
        # The dedicated `priority` kwarg is the same axis as `--set priority=<code>` — route
        # it through the identical declared-field gate rather than assigning it unconditionally
        # (a type whose `fields` doesn't declare `priority` must refuse it here too).
        checked_priority = (
            self._check_priority(item_type, priority) if priority is not None else None
        )
        item = Item(
            sequence_id=db.counter,
            type=str(item_type),
            prefix=resolved_prefix,
            title=title,
            slug=slug,
            status=str(status) if status is not None else self.spec.initial_status(item_type),
            description=description,
            parent=parent,
            author=author,
            assignee=assignee,
            priority=checked_priority,
            labels=labels or [],
            refs=refs or [],
            path=squad_rel,
            created_at=effective_now,
            updated_at=effective_now,
            created_session=sid,
            modified_session=sid,
            extra=extra or {},
        )
        for code, value in (fields or {}).items():
            field = self._badge_field(item_type, code)
            if field is None:
                raise SquadsError(f"{code!r} is not a declared field for {item_type}")
            item.set_badge_value(field.code, self._parse_badge_code(field, value))
        db.add(item)
        # Fail-closed on the new item's first error-level catalog violation (parent
        # type-eligibility, item status validity, …) — the same engine `sq check` reports.
        ValidatorEngine(spec=self.spec).gate(item, db)
        # Advisory lane check, keyed on the declared author slug. Exempt before lookup.
        # Service must NOT print — warning rides back in the result.
        # Only types some playbook guide declares an author for participate in the lane
        # domain; everything else (the roster types, and any type whose guidance names no
        # author) is never lane-checked. Resolved through the ACTIVE spec and playbook, so a
        # project-declared type with an override-declared authoring guide is laned like a
        # bundled one, and the exemption follows this squad's own default-role designation.
        lane_warning: str | None = None
        if (
            item_type in laned_types(self.playbook)
            and not is_lane_exempt(author, self._default_role_slug(db))
            and item_type not in allowed_create_types(author, self.spec, self.playbook)
        ):
            owners = in_lane_owner(item_type, self.playbook)
            owner_str = (
                ", ".join(f"'{s}'" for s in sorted(owners)) if owners else "no defined owner"
            )
            lane_warning = (
                f"advisory: '{author}' is not the in-lane author for '{item_type}' items"
                f" (expected: {owner_str})."
                " Lane checks are best-effort and advisory — proceeding."
            )
        return item, lane_warning

    async def _create_core(  # noqa: PLR0913 — mirrors `create`'s own keyword surface
        self,
        db: SquadsDB,
        item_type: str,
        title: str,
        *,
        description: str = "",
        parent: str | None = None,
        author: str | None = None,
        labels: list[str] | None = None,
        refs: list[str] | None = None,
        assignee: str | None = None,
        priority: str | None = None,
        extra: dict[str, Any] | None = None,
        status: str | None = None,
        slug: str | None = None,
        body: str | None = None,
        fields: dict[str, str] | None = None,
    ) -> CreateResult:
        """The create mutation core: takes an already-open transaction's ``db``, runs
        :meth:`_create_model`, then renders + writes the file and logs the reflog op.

        Shared by the interactive :meth:`create` (which opens its own transaction) and the
        bulk importer (which calls this directly inside its one open transaction — the
        store's file lock is not reentrant, so the importer cannot call :meth:`create` itself).
        """
        item, lane_warning = self._create_model(
            db,
            item_type,
            title,
            description=description,
            parent=parent,
            author=author,
            labels=labels,
            refs=refs,
            assignee=assignee,
            priority=priority,
            extra=extra,
            status=status,
            slug=slug,
            body=body,
            fields=fields,
        )
        item_type = item.type
        # ``agents/role.md.j2`` is both this item type's file scaffold and the definition
        # ``role_definition_text`` renders on read, so it reads ``role.<field>`` throughout and
        # Jinja's ``StrictUndefined`` makes a missing or partial ``role`` fail loudly rather
        # than degrade. The scaffold still has to render even though its body region is
        # emptied below — what survives it is the file's frame (the markers, the ``##
        # Discussion`` heading) — so a complete ``RoleDef`` is required here regardless.
        # ``activate_role``/``add_dev`` pass their resolved role's ``to_extra()``, but
        # ``create()`` is a lower-level, roster-type-agnostic entry point with no such
        # guarantee (there is no CLI verb for ``sq create role`` — the guard is CLI-only — but
        # the service layer itself does not refuse it), so ``from_extra_or_item`` falls back to
        # the item's own ``title``/``slug``/``description`` field by field wherever ``extra``
        # is silent. `None` for every other item type; an unreferenced context variable is
        # harmless to a template that never reads it.
        role_ctx = (
            RoleDef.from_extra_or_item(
                item.extra, title=item.title, slug=item.slug, description=item.description
            )
            if item_type == ROSTER_ROLE
            else None
        )
        rendered = render(
            self._template_for(item_type),
            item=item,
            description=item.description,
            extra=item.extra,
            spec=self.spec,
            role=role_ctx,
        )
        # Belt-and-suspenders: guarantee a working sub-entity container regardless of which
        # template rendered — a custom/renamed type falls back to `_default.md.j2` (no
        # container at all), and a bundled template whose sub-entity kind was renamed still
        # hardcodes its old container tag. Idempotent no-op when the template already emitted
        # the current kind's container correctly.
        rendered = ensure_subentity_container_text(self.spec, item_type, rendered)
        if item_type == ROSTER_ROLE:
            # A role's definition is rendered on every read (`role_definition_text`), from the
            # same template that produced the scaffold above, so the stored region would be a
            # second copy of a value the resolver already answers — and the only copy that can
            # go stale, since no write path refreshes it. The region is emptied rather than
            # removed: an absent one is a different fact about an item file, and the marker
            # pair is the shape every item file shares. An explicit `body` still wins below —
            # that is the caller stating a body, not this template producing one.
            rendered = sections.replace_section(rendered, markers.BODY, "")
        if body is not None:
            rendered = sections.replace_section(rendered, markers.BODY, body)
        squad_rel = item.path
        await write_new(self.paths.abspath(squad_rel), item, rendered)
        log_delta: dict[str, object] = {
            "title": item.title,
            "type": item_type,
            "status": item.status,
        }
        if lane_warning is not None:
            log_delta["lane_warning"] = {
                "advisory": True,
                "actor": item.author,
                "expected": sorted(in_lane_owner(item_type, self.playbook)),
                "type": item_type,
            }
        self.store.log(
            "create",
            item.id,
            log_delta,
        )
        return CreateResult(
            item=item, path=self.paths.abspath(squad_rel), lane_warning=lane_warning
        )

    async def get(self, item_id: str) -> Item:
        """Return *item_id*, always as a deep copy.

        Preserves a contract that already held before the read scope existed: every ``get()``
        used to come out of a freshly parsed db, so no two callers ever shared an object. With
        one snapshot now potentially served to many callers in the same invocation (see
        ``squads._index._store.read_scope``), the copy at this seam is what keeps that true —
        an in-place mutation of a returned item can never contaminate a later read of the same
        snapshot.
        """
        item = require_item(await self.store.load(), item_id)
        return item.model_copy(deep=True)

    async def _read_item_file(self, item: Item, path: Path) -> str:
        """Read *item*'s file at *path*, converting a missing file into a clean, actionable
        error — the item-read seam every show/body/discussion/comment path, and every
        mutating write seam that needs the on-disk text first, shares.

        An interrupted title-changing update or retype (see
        ``_services/_retype.py::apply_type_change``) can physically move the file before the
        index commits, leaving *path* (built from the index-loaded ``item``) stale. Delegates
        to :func:`~squads._itemfile.read_item_text`, which is unlike
        :func:`~squads._aio.read_text` in the one respect that matters here: it converts
        ``FileNotFoundError`` into a message naming the item and pointing at ``sq repair``,
        for callers that already want the content and have no fallback of their own to try —
        as opposed to the two callers that read it as a signal instead (the ``check`` confirm
        round's stale-path fallback, the bulk importer's pre-pass), which keep calling
        ``_aio.read_text`` directly and must never be routed through here.
        """
        return await read_item_text(path, item.id)

    async def list_items(
        self,
        *,
        item_type: str | None = None,
        status: str | None = None,
        parent: str | None = None,
        label: str | None = None,
        assignee: str | None = None,
        category: str | None = None,
        badges: dict[str, str] | None = None,
        badge_min: dict[str, str] | None = None,
    ) -> list[Item]:
        """List items matching every given filter dimension.

        ``category`` narrows to one of the fixed ``roster``/``work``/``records`` axis
        (validated at the CLI edge — unvalidated here, matching ``item_type``/``status``).
        ``badges``/``badge_min`` are keyed by badge field CODE (e.g. ``"priority"``, or a
        project's own custom axis) — generic over ``fields_for()``, not a dedicated param
        per axis. ``badge_min`` only matches ordered collections
        (see :meth:`ItemFilter._meets_min`).
        """
        f = ItemFilter(
            item_type=str(item_type) if item_type is not None else None,
            status=str(status) if status is not None else None,
            parent=parent,
            label=label,
            assignee=assignee,
            category=category,
            badges=tuple((badges or {}).items()),
            badge_min=tuple((badge_min or {}).items()),
            spec=self.spec,
        )
        out: list[Item] = []
        for it in (await self.store.load()).items.values():
            if not f.matches(it):
                continue
            out.append(it)
        return sorted(out, key=lambda i: number_for_id(i.id))

    async def tree_view(
        self,
        root_id: str | None = None,
        *,
        filter: ItemFilter | None = None,
        depth: int | None = None,
        include_closed: bool = False,
    ) -> list[TreeNode]:
        """Return the filtered, depth-bounded item hierarchy as a list of root ``TreeNode`` s.

        Algorithm:

        1. Load candidate set — all items; drop closed ones unless ``include_closed``.
        2. Build parent→children map and id→item map via ``_build_tree_children``.
        3. Determine roots: explicit ``root_id`` → that item; else the forest of items with no
           resolvable parent in view, plus one anchor per parent cycle (see
           ``_cycle_anchor_ids``) — every member of a cycle has a parent, so without an anchor
           the whole component would be absent from the bare tree at exit 0.
        4. Compute match set = items that satisfy ``filter`` (all items when filter is
           None/empty).
        5. Compute keep set = match set UNION all ancestors of each matched item.
           Ancestors not themselves in the match set are flagged ``path_only=True``.
        6. Single downward walk: include a node iff it is in the keep set; stop recursing
           when the next level would exceed ``depth`` (depth measured from each root = 0).
           Depth wins — a match deeper than the cut is not shown.
        7. Drop empty/orphaned roots (roots with no kept descendants and not themselves a
           match).
        """
        db = await self.store.load()
        all_items_list = list(db.items.values())

        # Step 1: candidate set — default visibility keyed on the status's role (settled +
        # hidden work/roster items drop out; an in-force record like Accepted/Published stays
        # visible; see WorkflowSpec.hidden_by_default).
        candidates: list[Item] = (
            all_items_list
            if include_closed
            else [i for i in all_items_list if not self.spec.hidden_by_default(i.type, i.status)]
        )

        # Step 2: build maps
        id_map: dict[str, Item] = {i.id: i for i in candidates}
        children_map: dict[str | None, list[Item]] = _build_tree_children(candidates)
        seq_to_id: dict[int, str] = {number_for_id(i.id): i.id for i in candidates}

        # Step 3: determine root(s)
        if root_id is not None:
            if root_id not in id_map:
                what = "item" if include_closed else "open item"
                raise SquadsError(
                    f"no {what} {root_id!r} to root the tree"
                    " (add --all to include closed items, or check it exists)"
                )
            root_items: list[Item] = [id_map[root_id]]
            # An explicitly rooted tree roots where the caller asked: nothing is fabricated
            # here, so nothing is marked. Rooting inside a cycle already rendered the component
            # correctly before this change and still does.
            anchor_ids: set[str] = set()
        else:
            # Widens "no resolvable parent in view" to "no resolvable acyclic path to a root",
            # on the same candidate graph the grouping resolved parents against.
            anchor_ids = _cycle_anchor_ids(candidates)
            forest = [*children_map.get(None, []), *(id_map[a] for a in anchor_ids)]
            root_items = sorted(forest, key=lambda i: number_for_id(i.id))

        # Step 4: compute match set (all candidates when filter is empty)
        effective_filter = filter if filter is not None else ItemFilter()
        match_set: set[str] = (
            {i.id for i in candidates}
            if effective_filter.is_empty()
            else {i.id for i in candidates if effective_filter.matches(i)}
        )

        # Step 5 + 6 + 7: compute keep set, walk down, prune and apply depth
        keep_set = _compute_keep_set(match_set, id_map, seq_to_id)
        result: list[TreeNode] = []
        for r in root_items:
            node = _walk_tree(
                r,
                0,
                keep_set=keep_set,
                match_set=match_set,
                children_map=children_map,
                depth=depth,
                anchor=r.id in anchor_ids,
            )
            if node is not None:
                result.append(node)
        return result

    def _check_parent(self, db: SquadsDB, child_type: str, parent_id: str) -> None:
        """Existence-only pre-check: a genuinely missing parent id is caught here, before the
        item enters the transaction, so it stays ``ItemNotFoundError`` (a distinct type/message
        from the engine's ``dangling parent`` report text). Parent-*type* eligibility is the
        catalog's ``parent_in``/``no_parent`` — enforced by the ``ValidatorEngine.gate()`` call
        every create/update/link site makes right after, not duplicated here.
        """
        del child_type
        if db.get(parent_id) is None:
            raise ItemNotFoundError(f"parent {parent_id!r} does not exist")

    def _is_participant(self, db: SquadsDB, slug: str) -> bool:
        """A slug that can author/be-assigned work: a registered role agent or a human operator.

        Skills are roster types but NOT participants — only role and operator are. This is
        deliberately **not** the catalog's ``agent_registered`` validator: that one is
        warn-level (report-only, matching today's ``sq check`` output) and, unlike this
        stricter create/update gate, treats any roster type — including a skill's slug — as
        registered. Retiring this in favour of the catalog would silently start accepting a
        skill as an author at create/update time; kept separate on purpose (flagged on the
        routing task's handoff).
        """
        return any(
            self.spec.item_is_roster(it.type)
            and it.type != ROSTER_SKILL
            and it.extra.get(X.SLUG) == slug
            for it in db.items.values()
        )

    def _check_author(self, db: SquadsDB, item_type: str, author: str, slug: str) -> None:
        # a roster type (role/skill/operator) definition may self-author (bootstrap)
        if self.spec.item_is_roster(item_type) and author == slug:
            return
        if not self._is_participant(db, author):
            raise SquadsError(
                f"author {author!r} is not a registered agent or operator — register it first"
            )

    def _check_assignee(self, db: SquadsDB, assignee: str | None) -> None:
        # an assignee is optional, but when set it must name a participant (a role or an operator)
        if assignee and not self._is_participant(db, assignee):
            raise SquadsError(
                f"assignee {assignee!r} is not a registered agent or operator — register it first"
            )

    def _badge_field(self, item_type: str, key: str) -> Field | None:
        """The declared field for *key* on *item_type*, generic over every axis (``--set
        <field>=<code>``): priority/severity/a project's own custom axis alike — not a
        hand-maintained allowlist of attribute-backed codes."""
        return next((f for f in self.spec.fields_for(item_type) if f.code == key), None)

    def _parse_badge_code(self, field: Field, raw: str) -> str:
        """Validate/normalize a ``--set <field>=<code>`` value against its bound collection."""
        coll = self.spec.collection(field.collection)
        code = raw.strip().lower()
        if code not in coll.badge_codes:
            choices = ", ".join(b.code for b in coll.badges)
            raise SquadsError(f"invalid {field.code} {raw!r} (one of: {choices})")
        return code

    def _check_priority(self, item_type: str, raw: str) -> str:
        """Gate the dedicated ``--priority`` kwarg through the same declared-field check as
        the generic ``--set priority=<code>`` door (:meth:`_badge_field`/:meth:`_parse_badge_code`)
        — a type that doesn't declare ``priority`` in its ``fields`` must refuse it here too,
        not just on the ``--set`` path. Two doors into the same axis, one gate."""
        field = self._badge_field(item_type, "priority")
        if field is None:
            valid = ", ".join(f.code for f in self.spec.fields_for(item_type)) or "(none)"
            raise SquadsError(
                f"'priority' is not a settable field on a {item_type}; valid: {valid}"
            )
        return self._parse_badge_code(field, raw)

    # ------------------------------------------------------------------ shared helpers
    async def _locked_section_edit(self, item_id: str, mutate: Callable[[str, Item], str]) -> Item:
        """Edit an item's prose under the index lock, atomically with the ``updated_at`` bump.

        Opens its own transaction, then delegates to :meth:`_section_edit_core` — the
        bulk importer calls that core directly (its own transaction is already open).
        """
        async with self.store.transaction() as db:
            return await self._section_edit_core(db, item_id, mutate)

    async def _section_edit_core(
        self, db: SquadsDB, item_id: str, mutate: Callable[[str, Item], str]
    ) -> Item:
        """The section-edit mutation core: takes an already-open transaction's ``db``.

        ``mutate(text, item)`` returns the new file text (sync callable — may raise to abort
        before any write). Shared by :meth:`_locked_section_edit` (body/comment/sub-body's
        common core) and the bulk importer.

        This is the second of the two write seams that rewrite an item's frontmatter from an
        index-derived ``Item`` (the other is :func:`~squads._itemfile.update_frontmatter`) —
        ``base`` is captured here, before ``mutate`` runs, and the on-disk text already read
        below is reused for the skew guard at no extra I/O cost.
        """
        it = require_item(db, item_id)
        base = it.model_copy(deep=True)
        path = item_file(self.paths, it)
        text = await self._read_item_file(it, path)
        ensure_no_skew(text, base, default_kind=self.spec.default_ref_kind())
        new_text = mutate(text, it)
        it.updated_at = clock.now()
        it.modified_session, _ = actor.current_session()
        await write_text(path, sections.replace_frontmatter(new_text, it.to_frontmatter_dict()))
        return it

    # ------------------------------------------------------------------ role / skill lookups
    async def roster_item(self, item_type: str, slug: str) -> Item | None:
        """Return the roster item of *item_type* (``ROSTER_ROLE``/``ROSTER_SKILL``/
        ``ROSTER_OPERATOR``) whose slug matches, or ``None``.

        A skill's slug falls back to its own :attr:`Item.slug` when ``extra.get(X.SLUG)`` is
        unset (``extra.get(X.SLUG, it.slug)``); role and operator lookups use no fallback
        (``extra.get(X.SLUG)``, so an item with no stored slug never matches). That per-type
        difference is real and preserved here rather than flattened by the shared loop.
        """
        for it in (await self.store.load()).items.values():
            if it.type != item_type:
                continue
            default = it.slug if item_type == ROSTER_SKILL else None
            if it.extra.get(X.SLUG, default) == slug:
                return it
        return None

    def role_definition_text(self, role: RoleDef) -> str:
        """Render *role*'s full definition — identity, mission, responsibilities, working
        agreements — at call time, resolved fresh from *role* rather than read from any stored
        copy.

        Renders the same template a role's stored body used to be written from
        (``agents/role.md.j2``), called here instead of at sync time. The caller supplies the
        already-resolved definition (``resolve_role_with_base`` — the same resolution a role's
        catalog card already computes) rather than this method resolving a second time on the
        same call. No file is read or written.
        """
        rendered = render("agents/role.md.j2", role=role)
        text = sections.get_section(rendered, markers.BODY)
        assert text is not None, "agents/role.md.j2 must keep its sq:body markers"
        return text.strip("\n")

    async def skill_definition_text(self, slug: str) -> str:
        """Render the definition of the **template-owned** skill named *slug* at call time,
        from the same templates a system skill's stored body used to be written from.

        Keyed on :func:`~squads._interactions.is_system_skill` and on nothing else. Neither the
        folder, the item type, nor the ``sq-`` prefix separates a template-owned skill from an
        authored one: they all sit in the skills folder, all carry the roster ``skill`` type,
        and the ``sq-`` prefix is not reserved to squads. A **custom** skill's body is authored
        storage and is read from the item instead (``read_body``); this method refuses that slug
        rather than inventing a render for it.

        Returns ``""`` for a system slug whose item type the active spec no longer declares —
        a dropped or renamed type has no definition to render, and no sync regenerates one.
        :func:`~squads._interactions.orphaned_skill_item_type` is what names that state for a
        caller's message.

        Lives on ``ServiceCore`` rather than in ``_interactions`` (the package that owns the
        playbook document, and so the symmetric home) because ``_rendering/_engine`` imports
        ``squads._interactions``: the rendering engine sits *above* that package and cannot be
        imported back from it. ``_services`` sits below ``_rendering`` and already calls
        ``render``. No backend takes part in either direction — a backend's skill pointer is
        rendered from a slug and a description alone.
        """
        if not is_system_skill(slug, self.spec):
            raise SquadsError(
                f"{slug!r} is not a template-owned skill; its body is authored content, "
                "read it from the item instead"
            )
        squad_dir = self.paths.config.squad_dir
        if slug == GREETING_SKILL:
            return render("agents/greeting_skill.md.j2", squad_dir=squad_dir).strip("\n")
        if slug == MEMORY_SKILL:
            return render("agents/memory_skill.md.j2", squad_dir=squad_dir).strip("\n")
        roster = await self.roster()
        if slug == SQUADS_SKILL:
            return render(
                "agents/squads_skill.md.j2",
                squad_dir=squad_dir,
                spec=self.spec,
                # roles=... so the included workflow.md.j2 cheatsheet's authoring bullets
                # (authoring_owner) filter by the LIVE roster, and so the example `--assignee`
                # names a slug this squad actually carries.
                roles=[
                    {"full_name": r.full_name, "title": r.title, "slug": r.slug} for r in roster
                ],
                # playbook=... so those same bullets resolve the create-lane through the ACTIVE
                # (merged) playbook: an override-declared authoring role is named here instead
                # of the type silently losing its authoring line.
                playbook=self.playbook,
            ).strip("\n")
        return self._item_skill_definition_text(slug, roster)

    def _item_skill_definition_text(self, slug: str, roster: list[RoleView]) -> str:
        """The per-type half of :meth:`skill_definition_text`: one ``sq-<type>`` definition,
        *rich* when the active merged playbook covers the type (full per-role
        Enter/Do/Hand-off/Watch-for sections) and *thin* when it does not (auto-derived
        lifecycle plus the standard command list, no role sections).

        The active merged playbook decides that split — not the bundled singleton — so an
        override's added or removed coverage is what moves a type between the two.

        A type the active spec no longer declares resolves to no type at all here and renders
        nothing, so a dropped or renamed type never produces a definition under its old name.
        """
        item_type = next(
            (
                t
                for t, ts in self.spec.items.items()
                if ts.category != "roster" and item_skill_name(t) == slug
            ),
            None,
        )
        if item_type is None:
            return ""
        pb = self.playbook.types.get(item_type)
        # Lifecycle + sub-entity kind derive from the active spec (not the playbook's frozen
        # prose), so an override on a covered built-in type stays correct.
        subentity_kind = self.spec.item_subentity_kind(item_type)
        return render(
            "agents/item_skill.md.j2",
            title=label_for(item_type, "singular", self.spec),
            type=item_type,
            overview=pb.overview if pb is not None else "",
            lifecycle=linearize_lifecycle(self.spec.machine_for(item_type)),
            commands=list(pb.commands) if pb is not None else custom_item_skill_commands(item_type),
            sections=_item_skill_role_sections(pb, roster),
            subentity_kind=subentity_kind,
            subentity_plural=self.spec.subentity_plural(subentity_kind) if subentity_kind else None,
        ).strip("\n")

    def _author_of(self, db: SquadsDB, slug: str) -> str:
        """Display (full) name for a participant slug, resolved against an already-loaded
        *db* — the pure core :meth:`author` wraps with its own fresh load.

        Reading from a caller-supplied ``db`` (rather than re-loading from disk) matters
        inside the bulk importer's one open transaction: an earlier event in the same run may
        have just created the role/operator this slug names, and that item is only visible in
        the in-memory ``db``, not yet on disk.

        A role participant's name comes from ``item.title`` — the uniform record's own copy of
        the resolved full name — never from ``extra.full_name`` nor a catalog resolution: this
        is a display name on a comment attribution, and resolving through the catalog here
        would be both wrong (an operator can rename a role's *display*, via ``sq role activate
        --name``, without that changing which catalog entry authored a past comment) and
        needlessly expensive for a lookup this cheap. An operator participant is untouched —
        it keeps reading ``extra.full_name``, its only home.
        """
        if slug == "operator":
            return "Operator"
        participant = next(
            (
                it
                for it in db.items.values()
                if it.type in (ROSTER_ROLE, ROSTER_OPERATOR) and it.extra.get(X.SLUG) == slug
            ),
            None,
        )
        if participant is not None:
            if participant.type == ROSTER_ROLE:
                return participant.title
            return participant.extra.get(X.FULL_NAME, slug)
        try:
            return resolve_role(slug, self.paths.squad_dir).full_name
        except SquadsError:
            return slug

    async def author(self, slug: str) -> str:
        """Display (full) name for a participant slug; falls back to the slug if unknown."""
        return self._author_of(await self.store.load(), slug)

    def _role_view(self, it: Item) -> RoleView:
        """Resolve *it* (a ROLE item) to the ``RoleView`` a backend compiles into the managed
        region — through the catalog (:func:`resolve_role_for_item`), never off ``extra``
        directly."""
        role = resolve_role_for_item(it, self.paths.squad_dir)
        return RoleView(
            slug=role.slug,
            full_name=role.full_name,
            title=role.title,
            is_default=role.is_default,
            mission=role.mission,
            responsibilities=role.responsibilities,
        )

    async def roster(self) -> list[RoleView]:
        """The roles this squad currently **offers** — ``item.status in
        spec.live_statuses("role")``. This is what ``write_managed`` compiles the host's
        config from and what skill-preload resolution (:meth:`_role_skills_map`) iterates;
        a retired role has no business in either. Use :meth:`roster_all` for a caller that
        needs every entry regardless of status (orphan detection, authorship display,
        registration checks, the roster's own views)."""
        live = self.spec.live_statuses(ROSTER_ROLE)
        return [
            self._role_view(it)
            for it in await self.list_items(item_type=ROSTER_ROLE)
            if it.status in live
        ]

    async def roster_all(self) -> list[RoleView]:
        """Every role entry regardless of status — the full-vocabulary counterpart to
        :meth:`roster`. See that method's docstring for which callers want which."""
        return [self._role_view(it) for it in await self.list_items(item_type=ROSTER_ROLE)]

    async def operators(self) -> list[OperatorView]:
        """The operators this squad currently **offers** — see :meth:`roster`'s docstring;
        same live/full split, mirrored for the operator type. Use :meth:`operators_all`
        for a full-vocabulary caller."""
        live = self.spec.live_statuses(ROSTER_OPERATOR)
        return [
            OperatorView(
                slug=it.extra.get(X.SLUG, it.slug),
                full_name=it.extra.get(X.FULL_NAME, it.title),
            )
            for it in await self.list_items(item_type=ROSTER_OPERATOR)
            if it.status in live
        ]

    async def operators_all(self) -> list[OperatorView]:
        """Every operator entry regardless of status — the full-vocabulary counterpart to
        :meth:`operators`."""
        return [
            OperatorView(
                slug=it.extra.get(X.SLUG, it.slug),
                full_name=it.extra.get(X.FULL_NAME, it.title),
            )
            for it in await self.list_items(item_type=ROSTER_OPERATOR)
        ]

    async def _skill_paths(self) -> dict[str, Path]:
        """Build a slug→absolute-body-path map for **live** SKILL items in the index.

        Backends receive this via BackendContext so they never need to load the
        index themselves (layering invariant: _backends must not import _index). Live-only
        because this only ever locates a managed skill's own file for ``write_managed`` (which
        gives a missing one its frontmatter-safe empty ``sq:body`` region and leaves an existing
        one alone) — a withdrawn skill has no generated entry to locate a file for.
        ``candidate_orphans`` needs the full skill-slug vocabulary instead and builds it
        directly rather than reusing this map (see that method).
        """
        skill_items = await self.list_items(item_type=ROSTER_SKILL)
        live = self.spec.live_statuses(ROSTER_SKILL)
        return {
            it.extra[X.SLUG]: self.paths.abspath(it.path)
            for it in skill_items
            if X.SLUG in it.extra and it.status in live
        }

    def _resolve_role_skills(self, slug: str, role: Item | None, db: SquadsDB) -> list[str]:
        """Pure (no I/O) core of the resolver: *db* and *role* are already loaded by the caller.

        Starts from ``interactions.skills_for_role(slug)`` (index-blind, always-on skills +
        the role's item-type skills), then unions in every custom skill carrying a forward
        edge to this role in the declared ``preload`` semantic (:meth:`WorkflowSpec
        .preload_ref_kind`) — found by inverting refs (``SquadsDB.backrefs``, kind-agnostic,
        so filtered here to that one declared kind) and mapping to slugs. Deduped, system-first
        then scoped skills in lexical order, so the result is stable and — with no preload
        edges anywhere — byte-identical to the pure function's own output.
        """
        system = skills_for_role(slug, self.spec, self.playbook)
        if role is None:
            return system
        role_prefix = effective_prefix(role.prefix)
        seen = set(system)
        scoped: set[str] = set()
        preload_kind = self.spec.preload_ref_kind()
        for candidate_id in db.backrefs(role.id):
            skill = db.get(candidate_id)
            if skill is None or skill.type != ROSTER_SKILL:
                continue
            for r in skill.refs:
                rid, kind = split_ref(r)
                if kind == preload_kind and ref_id_matches(rid, role_prefix, role.sequence_id):
                    scoped.add(skill.extra.get(X.SLUG, skill.slug))
                    break
        return [*system, *sorted(s for s in scoped if s not in seen)]

    async def resolved_skills_for_role(self, slug: str) -> list[str]:
        """A **live** role's full preload-skill set — standalone entry point (e.g. the
        link/unlink partial-sync hook), one index load. See :meth:`_resolve_role_skills` for
        the algorithm; bulk callers over every role should use :meth:`_role_skills_map`
        instead, which loads the index once for the whole roster rather than once per role.

        Live-only: a role that isn't on offer has no generated entry to preload skills
        into, so a slug naming a retired role resolves as if the role were absent — the pure
        system-membership fallback, never its scoped skills.
        """
        db = await self.store.load()
        live = self.spec.live_statuses(ROSTER_ROLE)
        role = next(
            (
                it
                for it in db.items.values()
                if it.type == ROSTER_ROLE and it.extra.get(X.SLUG) == slug and it.status in live
            ),
            None,
        )
        return self._resolve_role_skills(slug, role, db)

    async def _role_skills_map(self) -> dict[str, list[str]]:
        """Slug → resolved preload-skill list for every **live** role — the
        ``BackendContext.role_skills`` field.  Companion to :meth:`_skill_paths`: loads the
        index ONCE and resolves every live role's list from that single snapshot (mirrors
        ``_skill_paths``'s single-load shape), rather than re-parsing the index per role via
        :meth:`resolved_skills_for_role`. Live-only for the same reason as that method: a
        retired role's entry is never written, so its preload list is never consumed.
        """
        db = await self.store.load()
        live = self.spec.live_statuses(ROSTER_ROLE)
        return {
            it.extra[X.SLUG]: self._resolve_role_skills(it.extra[X.SLUG], it, db)
            for it in db.items.values()
            if it.type == ROSTER_ROLE and X.SLUG in it.extra and it.status in live
        }

    async def refresh_managed(self) -> list[str]:
        """(Re)write every active backend's roster/version-dependent files.

        Returns any WARN-only notices the writes surfaced (e.g. a pre-existing hand-written
        CLAUDE.md/AGENTS.md contradiction warning) — never gates the run, just bubbles up for
        the caller (``init``/``adopt``) to report.
        """
        skill_map = await self._skill_paths()
        role_skills = await self._role_skills_map()
        ctx = BackendContext(
            paths=self.paths,
            skill_paths=skill_map,
            role_skills=role_skills,
            spec=self.spec,
            playbook=self.playbook,
        )
        roster = await self.roster()
        ops = await self.operators()
        warnings: list[str] = []
        for backend in self._backends():
            artifacts = await backend.write_managed(ctx, roster, ops)
            warnings += [a.warning for a in artifacts if a.warning]
        return warnings

    async def candidate_orphans(self) -> list[str]:
        """WARN-only candidate-orphan pointer/skill files across every active backend —
        present on disk but managed by none of them. Never deletes anything; the caller
        only reports these for the adopter to reconcile by hand.

        Feeds backends the **full** roster vocabulary (:meth:`roster_all`) and the full
        known skill-slug set (every SKILL item regardless of status, not just
        :meth:`_skill_paths`'s live-only map) — an orphan means "a file this squad never
        managed", and a withdrawn entry's leftover file is this squad's own convergence
        debt, never a foreign file. Feeding the live-only projection here would relabel
        that debt as a stranger's file, loudest on exactly the squads that have retired
        an entry.

        The known-slug floor is :func:`active_skill_slugs` (the active spec's *current*
        vocabulary), not the allocation-order union
        (``bundled_skill_slugs() | custom_skill_slugs(spec)``) those two seeding helpers use —
        that union always covers every historically-bundled ``sq-<type>`` slug, so it would
        keep exempting a dropped/renamed type's stale skill from ever being flagged now that a
        workflow override can shadow a built-in type instead of only adding to it.
        """
        all_skills = await self.list_items(item_type=ROSTER_SKILL)
        skill_slugs = {
            it.extra[X.SLUG] for it in all_skills if X.SLUG in it.extra
        } | active_skill_slugs(self.spec)
        roster = await self.roster_all()
        ctx = self._ctx
        orphans: list[str] = []
        for backend in self._backends():
            orphans += await backend.candidate_orphans(ctx, roster, skill_slugs)
        return [
            f"candidate orphan (not managed by this squad, never auto-deleted): {p}"
            for p in orphans
        ]

    async def _resync_role_skills(self, slug: str) -> None:
        """Partial-sync hook: recompute and rewrite ONE role's backend pointer.

        The supported incremental path for the ``sq skill link-role``/``unlink-role`` verbs —
        mirrors the per-role pointer step a full :meth:`sync` runs, scoped to a single role;
        every other role's pointer is left byte-untouched. A full ``sq sync`` remains the
        authoritative recomputation for the whole roster — this is an optimization on top of
        it, never the only path.

        The resolved-skills list itself is never persisted anywhere: it is a computed
        projection, recovered on demand from the index the caller already loaded
        (:meth:`resolved_skills_for_role`), not a cache this hook refreshes. What this
        recomputes and writes is the *backend pointer* — the one materialised artifact that
        still carries the list, because a non-human agent host reads it as a file rather than
        running a command.

        The backend pointer is only regenerated when the role is **live** — scoping a
        skill to a retired role must not resurrect its withdrawn projection.
        """
        role = await self.roster_item(ROSTER_ROLE, slug)
        if role is None:
            return  # nothing to resync — caller already validated the role exists
        resolved = await self.resolved_skills_for_role(slug)
        if role.status in self.spec.live_statuses(ROSTER_ROLE):
            role_ctx = BackendContext(
                paths=self.paths,
                spec=self.spec,
                playbook=self.playbook,
                role_skills={slug: resolved},
            )
            role_def = resolve_role_for_item(role, self.paths.squad_dir)
            for backend in self._backends():
                await backend.generate_role_entry(role_ctx, role, role_def)

    async def _project_roster_item(self, item: Item, ctx: BackendContext) -> list[str]:
        """Materialise or withdraw *item*'s own per-entry backend artifact: an entry is
        materialised iff its status carries the ``live`` flag; every other status is
        withdrawn. The single place the materialise-or-withdraw predicate and the backend
        calls it drives are expressed — shared by the single-item transition path
        (:meth:`_project_roster_transition`) and ``sync``'s roster sweep
        (:meth:`MaintenanceMixin.sync`), so the two can no longer disagree on either the
        predicate or the context they hand the backend.

        The materialise-or-withdraw predicate itself is
        :func:`~squads._interactions.is_live_roster_entry` — shared verbatim with ``sq
        check``'s ``backend_reconciled`` rule and ``sync``'s own regeneration report
        (both in :mod:`squads._services`), so none of the three can drift onto a different
        notion of "live" than the others. For a ``SKILL`` item its second clause requires the
        slug to still name a type the active spec declares: a dropped or renamed built-in's
        stale ``sq-<type>`` skill is withdrawn right alongside a manually-retired one, with no
        separate mechanism — and re-materialises on its own the moment the type comes back,
        since this is a pure per-call derivation, never a stored flag. This is what keeps a
        drop's generated-skill residue from outliving the type it described.

        A no-op for an operator item (no per-entry file — only a row in a compiled region);
        the caller's own managed-region recompile is what represents it. *ctx* must already
        carry the resolved preload map (:meth:`_role_skills_map`) for a role item — this
        method never resolves it itself, so a caller processing many items resolves the map
        once and reuses this same *ctx* for all of them rather than once per item.

        Fans out over every active backend (:meth:`_backends`, already empty-safe: with
        ``active_backends = []`` there is nothing to project). Materialise calls
        ``generate_role_entry``/``generate_skill_entry``; withdraw calls the existing
        ``remove_artifacts`` (missing-tolerant and idempotent by its own contract, so
        withdrawing against a never-scaffolded backend is a clean no-op).

        Returns the WARN-only notices the per-entry writes surfaced (``Artifact.warning`` —
        e.g. a declared model the host's own frontmatter cannot express, dropped from the
        rendered pointer), for the caller to report alongside its own. Empty in the normal
        case. Never gates anything: this is the same "the write went through, but you should
        know what it did" channel :meth:`refresh_managed` already bubbles up for the compiled
        regions, extended to the per-entry files — without it, the only record of the drop is
        the absence of a line in a generated file.
        """
        if item.type not in (ROSTER_ROLE, ROSTER_SKILL):
            return []
        live = is_live_roster_entry(item, self.spec)
        role_def = (
            resolve_role_for_item(item, self.paths.squad_dir)
            if live and item.type == ROSTER_ROLE
            else None
        )
        warnings: list[str] = []
        for backend in self._backends():
            if live:
                if item.type == ROSTER_ROLE:
                    assert role_def is not None  # resolved above, live ROSTER_ROLE guaranteed it
                    artifact = await backend.generate_role_entry(ctx, item, role_def)
                else:
                    artifact = await backend.generate_skill_entry(ctx, item)
                if artifact.warning:
                    warnings.append(artifact.warning)
            else:
                await backend.remove_artifacts(ctx, item)
        return warnings

    async def _project_roster_transition(self, item: Item) -> list[str]:
        """Materialise or withdraw *item*'s backend projection after a single roster item's
        status transition commits — the projection write happens outside the transaction,
        same ordering the roster create verbs already use, since a generated file is
        regenerable cache rather than a markdown item.

        Resolves the whole roster's preload map in one index read
        (:meth:`_role_skills_map`) — even though only one entry is transitioning, the map
        is a single-load computation over every live role, never a per-role read — and hands
        it to :meth:`_project_roster_item` so a role's ``scopes``-derived skills survive a
        retire/reactivate round trip exactly as a first creation would.

        Every transition, in either direction, ends by recompiling the managed regions
        (:meth:`refresh_managed`): withdrawal changes generated *prose* beyond the roster
        table (the default-role line, the developer-gated per-item-type skill text), so the
        compiled regions must be rewritten every time, not only the entry's own file. This
        also covers an operator transition, which has no per-entry file at all and so skips
        straight to this region refresh.

        Returns the WARN-only notices both halves surfaced — the entry's own
        (:meth:`_project_roster_item`) followed by the region recompile's
        (:meth:`refresh_managed`) — so a caller that has somewhere to print them can, and one
        that has not is unchanged. The full ``sq sync`` sweep is the surface that always
        reports; a single transition is the incremental path onto the same files.
        """
        role_skills = await self._role_skills_map()
        ctx = BackendContext(
            paths=self.paths, spec=self.spec, playbook=self.playbook, role_skills=role_skills
        )
        warnings = await self._project_roster_item(item, ctx)
        return warnings + await self.refresh_managed()
