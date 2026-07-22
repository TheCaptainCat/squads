"""WorkflowSpec pydantic v2 value objects.

The loaded spec is the sole vocabulary authority for both axes: TOML type keys AND status
keys stay plain ``str`` (no enum coercion, no closed set). The reserved surface is exactly
the three meta-types (``META_TYPES``) plus their agent-lifecycle statuses
(``_RESERVED_FLOOR`` — ``Draft``/``Active``/``Archived``); every other type or status is
ordinary spec vocabulary a project may drop, rename, or reorder.

The capability flags declared here (``category``, ``subentity_kind``, ``parent_required``,
``ref_rules``, ``StatusSpec.role``) are additive; ``SubentityKindSpec.completion`` is
consumed by the sub-entity/finding done-toggle (``_services/_subentities.py``). They are
encoded in ``default_workflow.toml``.

``Badge``/``Collection``/``Field`` are the badge-vocabulary schema: ``ItemSpec.fields`` /
``SubentityKindSpec.fields`` bind a type or sub-entity kind to a reusable ``Collection`` of
``Badge``s — "does type/kind X carry field Y" is a ``fields_for(X)`` lookup, replacing the old
closed-set ``Priority``/``Severity`` enums.
"""

import math
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

#: The three meta-types the engine binds by literal name — the irreducible
#: structural minimum: the roster, the backends (which write role/skill files), and the
#: agent lifecycle genuinely reference these by name. NOT a closed type vocabulary — every
#: other type (built-in or custom) is ordinary, droppable/renamable spec vocabulary.
META_ROLE = "role"
META_SKILL = "skill"
META_OPERATOR = "operator"
META_TYPES: frozenset[str] = frozenset({META_ROLE, META_SKILL, META_OPERATOR})

#: The agent-lifecycle statuses the engine binds by literal name — the same irreducible
#: minimum on the status axis as ``META_TYPES`` is on the type axis: a meta-type must be
#: creatable (``Draft``), activatable (``Active``), and archivable (``Archived``), which is
#: structural. Every other status — work-item, sub-entity, and finding alike — is ordinary
#: spec vocabulary bound by role in its state machine, never by name.
STATUS_DRAFT = "Draft"
STATUS_ACTIVE = "Active"
STATUS_ARCHIVED = "Archived"
_RESERVED_FLOOR: frozenset[str] = frozenset({STATUS_DRAFT, STATUS_ACTIVE, STATUS_ARCHIVED})

# ---------------------------------------------------------------------------
# Workflow dataclass — the thin shim over Lifecycle
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Workflow:
    """Thin shim: exposes the ``Workflow`` interface backed by ``Lifecycle``.

    Status fields are plain ``str`` — there is no enum backing them.
    """

    initial: str
    transitions: dict[str, tuple[str, ...]]

    @property
    def states(self) -> set[str]:
        seen: set[str] = {self.initial}
        for src, dsts in self.transitions.items():
            seen.add(src)
            seen.update(dsts)
        return seen

    def can_transition(self, src: str, dst: str) -> bool:
        return dst in self.transitions.get(src, ())

    @staticmethod
    def from_machine(m: Lifecycle) -> Workflow:
        """Build a ``Workflow`` shim from a ``Lifecycle`` (public factory)."""
        return Workflow(
            initial=m.initial,
            transitions={s: tuple(dsts) for s, dsts in m.transitions.items()},
        )


class Lifecycle(BaseModel):
    """A named lifecycle state machine: initial state + transition map.

    ``.states`` is derived (initial union all sources union all targets),
    mirroring ``Workflow.states``.

    Status fields are plain ``str`` — there is no enum backing them; the spec is the sole
    vocabulary authority (module docstring above).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    initial: str
    transitions: dict[str, list[str]]

    @property
    def states(self) -> frozenset[str]:
        seen: set[str] = {self.initial}
        for src, dsts in self.transitions.items():
            seen.add(src)
            seen.update(dsts)
        return frozenset(seen)

    def can_transition(self, src: str, dst: str) -> bool:
        return dst in self.transitions.get(src, [])


class RefRule(BaseModel):
    """A declared ref-kind rule for a type.

    Examples:
    - task → fixes / addresses (drives the parent_hint suffix and sq check)
    - decision → supersedes (drives the sq check ADR warning)

    Not yet consumed by the engine.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: str
    """The ref kind this rule applies to (e.g. ``"fixes"``, ``"supersedes"``)."""
    hint: str = ""
    """Human-readable hint injected into ``parent_hint`` / error messages (optional)."""


class Badge(BaseModel):
    """One atomic value in a collection: stored ``code`` + display ``label`` + presentation
    ``emoji``. Rendered verbatim — a field may relabel the collection, never a badge itself."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    label: str
    emoji: str | None = None


class Collection(BaseModel):
    """A reusable, named library of badges.

    Identified by its key in ``WorkflowSpec.collections`` — no self-stored code, mirroring
    ``ItemSpec``/``StatusSpec``/``Lifecycle`` (identity lives in the dict key, never
    duplicated onto the value). ``ordered`` drives sort + threshold filtering; ``default``
    is the collection's own fallback badge code, overridable per-field.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str
    ordered: bool = False
    default: str | None = None
    badges: list[Badge] = []

    @property
    def badge_codes(self) -> frozenset[str]:
        return frozenset(b.code for b in self.badges)


class Field(BaseModel):
    """A type's or sub-entity-kind's binding to a collection.

    ``code`` is the frontmatter key + CLI flag identity (list-item identity, like
    ``Badge.code``/``RefRule.kind``); ``label`` relabels the bound collection for this
    field's display only. ``required``/``default`` are per-field, not per-collection.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    label: str
    collection: str
    required: bool = False
    default: str | None = None


class SubentityKindSpec(BaseModel):
    """Per-sub-entity-kind declarations: machine binding + CLI/storage vocabulary + fields.

    Mirrors ``ItemSpec`` on the sub-entity axis — ``lifecycle`` is the explicit machine
    reference (retiring the former kind-name==lifecycle-name convention), ``plural``/
    ``local_prefix``/``placeholder`` are the CLI-facing vocabulary a custom kind needs to
    behave like a built-in one, and ``fields`` reuses the item-axis field mechanism, unforked.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    lifecycle: str
    """Explicit lifecycle-machine reference (mirrors ``ItemSpec.lifecycle``); the machine
    a sub-entity of this kind is driven by, looked up in ``WorkflowSpec.lifecycles``."""

    plural: str
    """CLI list verb and container-marker name (e.g. ``"stories"``, ``"subtasks"``)."""

    local_prefix: str
    """Local-id prefix for this kind (e.g. ``"US"``, ``"ST"``, ``"F"``)."""

    placeholder: str | None = None
    """Scaffold prose shown for a freshly-created block with no body yet. ``None`` falls
    back to a generic kind-derived placeholder (derivation not yet wired — a later task)."""

    maps_parent_story: bool = False
    """Capability flag: a sub-entity of this kind maps to one of its parent's stories
    (drives the ``--story`` option and the ``Story`` column). ``True`` only for the
    built-in ``subtask`` kind."""

    completion: str
    """The done-toggle target status inside this kind's own ``lifecycle`` — what
    ``subentity_completion(kind)`` resolves to instead of a hardcoded ``Done``/``Fixed``
    literal. Must name a reachable, non-initial state of that lifecycle (enforced at load
    by ``_check_completion_status``)."""

    fields: list[Field] = []


class ItemSpec(BaseModel):
    """Vocabulary for one item type: prefix, folder, lifecycle, parents, aliases.

    Capability flags are additive and default to the ``False``/``None`` values
    that represent the common case (non-meta work item with no special spine).
    They are not yet consumed by the engine.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    prefix: str
    folder: str
    lifecycle: str
    parents: list[str] = []
    aliases: list[str] = []

    order: float = math.inf
    """Explicit ascending registration/display order; the type-name string breaks ties.
    Drives the CLI's per-type command registration order (deterministic, not alphabetical
    and not on-disk TOML order). A ``float`` (not ``int``) so a type can be inserted between
    two adjacent explicitly-ordered types (e.g. ``25.5`` between ``20`` and ``30``) without
    renumbering anything. Omitted ⇒ ``+inf``, so an un-ordered type (e.g. a project-declared
    custom type that doesn't set this) sorts after every explicitly-ordered type, then
    alphabetically among themselves."""

    # ------------------------------------------------------------------
    # Capability flags (additive; not yet consumed by engine)
    # ------------------------------------------------------------------

    category: Literal["roster", "work", "records"] = "work"
    """The type's behavioural bundle, per the accepted category/validator decision: ``roster``
    (role/skill/operator — not a work type, no work lifecycle, slug-keyed identity,
    retype-ineligible, self-author bypass for bootstrap; locked off the override surface),
    ``work`` (burn-down items), or ``records`` (durable references). The ``Literal`` itself
    rejects any value outside the closed catalog at construction — the Plane-1
    category-catalog-membership check."""

    subentity_kind: str | None = None
    """The kind of sub-entity this type hosts: ``"story"`` | ``"subtask"`` | ``"finding"``
    or ``None`` for types that have no sub-entities (epic/bug/decision/guide/meta-types)."""

    parent_required: str | None = None
    """The required parent type expressed as a string (e.g. ``"feature"`` for task).
    ``None`` means the type is unconstrained (any parent or none is valid)."""

    ref_rules: list[RefRule] = []
    """Declared ref-kind rules that drive parent_hint text and sq check enforcement
    (e.g. task → fixes/addresses; decision → supersedes)."""

    fields: list[Field] = []
    """Badge-collection bindings this type carries (e.g. priority/severity) — "does this type
    carry field X" is ``X in {f.code for f in fields}``, exposed via ``fields_for()``."""

    extra_fields: list[str] = []
    """Generic (non-badge) ``extra`` metadata keys (``ExtraKey`` values) this type exposes via
    ``sq update --set`` — spec-declared identity so a renamed work type (e.g. guide->doc)
    keeps its settable fields instead of losing them to a hardcoded literal type name. The
    value kind (str/list/bool) per key is fixed in ``_models/_metadata.py``, not declared here."""


class StatusSpec(BaseModel):
    """Terminal flag + optional sub-entity badge for one status name."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    terminal: bool
    badge: str | None = None

    # ------------------------------------------------------------------
    # Semantic-status role marker (additive; not yet consumed)
    # ------------------------------------------------------------------

    role: str | None = None
    """Semantic-status role marker for engine rules that key on a specific status.
    Currently used to identify ``Superseded`` (``role="superseded"``).
    Future rules add a new role name here rather than a new flag column.
    Not yet consumed by the engine."""


# ---------------------------------------------------------------------------
# Validation helpers (extracted to keep _validate under complexity limits)
# ---------------------------------------------------------------------------


def _check_lifecycle_statuses(
    lifecycles: dict[str, Lifecycle],
    all_statuses: set[str],
    errors: list[str],
) -> None:
    """Check initial and transition src/dst are declared statuses."""
    for name, m in lifecycles.items():
        tag = f"lifecycle {name!r}"
        if m.initial not in all_statuses:
            errors.append(f"{tag}: initial {m.initial!r} not in status set")
        for src, dsts in m.transitions.items():
            if src not in all_statuses:
                errors.append(f"{tag}: transition source {src!r} not in status set")
            errors.extend(
                f"{tag}: transition target {dst!r} not in status set"
                for dst in dsts
                if dst not in all_statuses
            )


def _check_reachability(
    lifecycles: dict[str, Lifecycle],
    errors: list[str],
) -> None:
    """Every state in a lifecycle must be reachable from initial."""
    for name, m in lifecycles.items():
        reachable: set[str] = {m.initial}
        queue: list[str] = [m.initial]
        while queue:
            cur = queue.pop()
            for nxt in m.transitions.get(cur, []):
                if nxt not in reachable:
                    reachable.add(nxt)
                    queue.append(nxt)
        unreachable = m.states - reachable
        errors.extend(
            f"lifecycle {name!r}: state {s!r} unreachable from initial {m.initial!r}"
            for s in unreachable
        )


def _check_reachable_terminal(
    lifecycles: dict[str, Lifecycle],
    statuses: dict[str, StatusSpec],
    errors: list[str],
) -> None:
    """Every lifecycle must be able to reach at least one terminal state.

    BFS from ``initial`` over the transition graph; if none of the reachable
    states is marked ``terminal`` in the status spec, the machine can never
    close (breaking ``sq blocked``, the default closed-item filter, and inbox
    suppression for any item stuck on it).  Fails closed with the offending
    lifecycle name so ``sq workflow lint`` can point the author at the fix.
    """
    for name, m in lifecycles.items():
        reachable: set[str] = {m.initial}
        queue: list[str] = [m.initial]
        while queue:
            cur = queue.pop()
            for nxt in m.transitions.get(cur, []):
                if nxt not in reachable:
                    reachable.add(nxt)
                    queue.append(nxt)
        if not any(statuses.get(s, StatusSpec(terminal=False)).terminal for s in reachable):
            errors.append(
                f"lifecycle {name!r}: no terminal status reachable from initial "
                f"{m.initial!r} (reachable: {sorted(reachable)}) — items on this "
                f"lifecycle could never close; add a transition to a terminal status"
            )


def _check_completion_status(
    subentity_kinds: dict[str, SubentityKindSpec],
    lifecycles: dict[str, Lifecycle],
    errors: list[str],
) -> None:
    """Each declared sub-entity kind's ``completion`` must name a reachable, non-initial
    state of its own ``lifecycle`` — the done-toggle target ``subentity_completion(kind)``
    resolves to. An undeclared ``lifecycle`` is caught separately by
    ``_check_subentity_kinds``; skipped here to avoid a duplicate error.
    """
    for kind, ks in subentity_kinds.items():
        machine = lifecycles.get(ks.lifecycle)
        if machine is None:
            continue
        if ks.completion == machine.initial:
            errors.append(
                f"subentity kind {kind!r}: completion {ks.completion!r} is the initial "
                f"status of lifecycle {ks.lifecycle!r} — nothing is done at creation"
            )
        elif ks.completion not in machine.states:
            errors.append(
                f"subentity kind {kind!r}: completion {ks.completion!r} not a reachable "
                f"status of lifecycle {ks.lifecycle!r} (states: {sorted(machine.states)})"
            )


def _check_subentity_kinds(
    items: dict[str, ItemSpec],
    subentity_kinds: dict[str, SubentityKindSpec],
    all_lifecycle_names: set[str],
    errors: list[str],
) -> None:
    """ItemSpec.subentity_kind references a declared kind; SubentityKindSpec.lifecycle
    reference + plural/local_prefix non-empty & uniqueness."""
    referenced = sorted({ts.subentity_kind for ts in items.values() if ts.subentity_kind})
    errors.extend(
        f"item type references undeclared subentity kind {kind!r} (not in subentity_kinds)"
        for kind in referenced
        if kind not in subentity_kinds
    )

    seen_plurals: dict[str, str] = {}
    seen_prefixes: dict[str, str] = {}
    for kind, ks in subentity_kinds.items():
        if ks.lifecycle not in all_lifecycle_names:
            errors.append(
                f"subentity kind {kind!r}: lifecycle {ks.lifecycle!r} not declared in lifecycles"
            )

        if not ks.plural:
            errors.append(f"subentity kind {kind!r}: plural must be non-empty")
        elif ks.plural in seen_plurals:
            errors.append(
                f"duplicate subentity plural {ks.plural!r}: used by kinds "
                f"{seen_plurals[ks.plural]!r} and {kind!r}"
            )
        else:
            seen_plurals[ks.plural] = kind

        if not ks.local_prefix:
            errors.append(f"subentity kind {kind!r}: local_prefix must be non-empty")
        elif ks.local_prefix in seen_prefixes:
            errors.append(
                f"duplicate subentity local_prefix {ks.local_prefix!r}: used by kinds "
                f"{seen_prefixes[ks.local_prefix]!r} and {kind!r}"
            )
        else:
            seen_prefixes[ks.local_prefix] = kind


def _check_parent_cycles(
    items: dict[str, ItemSpec],
    errors: list[str],
) -> None:
    """Detect cycles in the type-parent graph.

    Walks ``items[t].parents`` using DFS with a colour-marking scheme:
    - WHITE (unvisited), GREY (on the current path), BLACK (fully explored).
    A back-edge (GREY → GREY) indicates a cycle.

    Reports each cycle once in a deterministic order (sorted entry points).
    """
    WHITE, GREY, BLACK = 0, 1, 2
    colour: dict[str, int] = {t: WHITE for t in items}
    path: list[str] = []
    reported: set[frozenset[str]] = set()

    def dfs(node: str) -> None:
        colour[node] = GREY
        path.append(node)
        for parent in items[node].parents:
            if parent not in colour:
                # Parent declared but not a known type — caught by _check_item_refs.
                continue
            if colour[parent] == GREY:
                # Back-edge: reconstruct cycle from path.
                cycle_start = path.index(parent)
                cycle_nodes = path[cycle_start:]
                key = frozenset(cycle_nodes)
                if key not in reported:
                    reported.add(key)
                    cycle_str = " → ".join([*cycle_nodes, parent])
                    errors.append(f"type-parent graph has a cycle: {cycle_str}")
            elif colour[parent] == WHITE:
                dfs(parent)
        path.pop()
        colour[node] = BLACK

    for t in sorted(items):
        if colour[t] == WHITE:
            dfs(t)


def _check_item_refs(
    items: dict[str, ItemSpec],
    all_lifecycle_names: set[str],
    all_types: set[str],
    errors: list[str],
) -> None:
    """ItemSpec lifecycle/parent references + prefix/folder/alias uniqueness."""
    seen_prefixes: dict[str, str] = {}
    seen_folders: dict[str, str] = {}
    seen_aliases: dict[str, str] = {}

    for t, ts in items.items():
        if ts.lifecycle not in all_lifecycle_names:
            errors.append(f"item {t!r}: lifecycle {ts.lifecycle!r} not declared in lifecycles")
        errors.extend(
            f"item {t!r}: parent type {p!r} not declared" for p in ts.parents if p not in all_types
        )
        if ts.prefix in seen_prefixes:
            errors.append(
                f"duplicate prefix {ts.prefix!r}: used by {seen_prefixes[ts.prefix]!r} and {t!r}"
            )
        seen_prefixes[ts.prefix] = t

        if ts.folder in seen_folders:
            errors.append(
                f"duplicate folder {ts.folder!r}: used by {seen_folders[ts.folder]!r} and {t!r}"
            )
        seen_folders[ts.folder] = t

        for alias in ts.aliases:
            if alias in seen_aliases:
                errors.append(
                    f"duplicate alias {alias!r}: used by {seen_aliases[alias]!r} and {t!r}"
                )
            seen_aliases[alias] = t


#: Field codes exempt from the reserved-key check below because this exact schema models
#: them by field code on purpose — the bundled ``priority``/``severity`` fields keep the
#: literal key their axis has always used (``Item.priority``/``Item.severity``/
#: ``SubEntity.severity`` are themselves the badge-code storage, not a shadow of it), so
#: frontmatter keeps round-tripping unchanged.
_FIELD_ELIGIBLE_ITEM_KEYS: frozenset[str] = frozenset({"priority", "severity"})
_FIELD_ELIGIBLE_SUBENTITY_KEYS: frozenset[str] = frozenset({"severity"})


def _reserved_item_keys() -> frozenset[str]:
    """Item frontmatter keys a field code may not shadow.

    Derived from ``Item``'s own model/computed fields (never hand-copied) minus ``path``
    (model-only, never written to frontmatter) and the field-eligible exemptions.

    ``prefix`` stays reserved even though it, too, is model-only/never written: it is a
    *tolerated* legacy frontmatter key on read (``Item.id`` always wins over it), so a live
    field coded ``prefix`` would silently shadow — be read and discarded — exactly the hazard
    this check exists to catch. Excluding it here, as ``path`` is, would defeat that.
    """
    from squads._models._item import Item

    keys = set(Item.model_fields) | set(Item.model_computed_fields)
    return frozenset(keys - {"path"} - _FIELD_ELIGIBLE_ITEM_KEYS)


def _reserved_subentity_keys() -> frozenset[str]:
    """Sub-entity frontmatter keys a field code may not shadow (mirrors ``_reserved_item_keys``)."""
    from squads._models._subentity import SubEntity

    keys = set(SubEntity.model_fields) | set(SubEntity.model_computed_fields)
    return frozenset(keys - _FIELD_ELIGIBLE_SUBENTITY_KEYS)


def _iter_field_owners(
    items: dict[str, ItemSpec],
    subentity_kinds: dict[str, SubentityKindSpec],
) -> Iterator[tuple[str, bool, list[Field]]]:
    """Yield ``(owner_name, is_item, fields)`` for every type/kind that declares fields."""
    for t, ts in items.items():
        if ts.fields:
            yield t, True, ts.fields
    for k, ks in subentity_kinds.items():
        if ks.fields:
            yield k, False, ks.fields


def _check_field_codes(
    items: dict[str, ItemSpec],
    subentity_kinds: dict[str, SubentityKindSpec],
    errors: list[str],
) -> None:
    """Field-code uniqueness per owner + reserved-frontmatter-key collision."""
    reserved_item = _reserved_item_keys()
    reserved_subentity = _reserved_subentity_keys()
    for owner, is_item, fields in _iter_field_owners(items, subentity_kinds):
        seen: set[str] = set()
        reserved = reserved_item if is_item else reserved_subentity
        for f in fields:
            if f.code in seen:
                errors.append(f"{owner!r}: duplicate field code {f.code!r}")
            seen.add(f.code)
            if f.code in reserved:
                errors.append(
                    f"{owner!r}: field code {f.code!r} shadows a reserved frontmatter key"
                )


def _check_field_collections(
    items: dict[str, ItemSpec],
    subentity_kinds: dict[str, SubentityKindSpec],
    collections: dict[str, Collection],
    errors: list[str],
) -> None:
    """Every field's collection resolves; every default badge code (field- or
    collection-level) names a badge in that collection; a required field with no
    resolvable default is rejected."""
    for code, coll in collections.items():
        if not coll.ordered:
            # Ordered-only for now. The flag stays in the schema (reserved for a future
            # unordered kind), but nothing downstream (sort/--min-<field>) reads it —
            # accepting ordered=false here would rank badges by declaration order
            # silently, a meaningless-but-quiet result. Fail closed instead.
            errors.append(f"collection {code!r}: unordered collections are not supported yet")
        if coll.default is not None and coll.default not in coll.badge_codes:
            errors.append(f"collection {code!r}: default {coll.default!r} not a declared badge")

    for owner, _is_item, fields in _iter_field_owners(items, subentity_kinds):
        for f in fields:
            coll = collections.get(f.collection)
            if coll is None:
                errors.append(
                    f"{owner!r} field {f.code!r}: collection {f.collection!r} not declared"
                )
                continue
            if f.default is not None and f.default not in coll.badge_codes:
                errors.append(
                    f"{owner!r} field {f.code!r}: default {f.default!r} not a badge in "
                    f"collection {f.collection!r}"
                )
            if f.required:
                resolved = f.default or coll.default
                if resolved is None or resolved not in coll.badge_codes:
                    errors.append(
                        f"{owner!r} field {f.code!r}: required with no resolvable default "
                        f"badge in collection {f.collection!r}"
                    )


# Canonical priority order for well-known exception/side states: states appearing together
# in the side-state list sort by this (lower = earlier), regardless of BFS discovery order
# (e.g. Blocked before Cancelled). States absent here keep BFS order via the fallback rank
# (len(_SIDE_PRIORITY)).
_SIDE_PRIORITY: dict[str, int] = {
    "WontFix": 0,
    "Blocked": 1,
    "Cancelled": 2,
    "Rejected": 3,
    "Deprecated": 4,
}


def linearize_lifecycle(machine: Lifecycle) -> str:
    """Derive a readable lifecycle string from an arbitrary transition graph.

    Algorithm:
    1. Build the **spine** by following the first unvisited transition from each state
       (greedy forward walk from ``machine.initial``), stopping when no new state is
       reachable.  This gives the "happy-path" chain ``A → B → C``.
    2. Collect **side states** — all states reachable from ``machine.initial`` that
       are not on the spine — in BFS discovery order.
    3. Sort side states into canonical order using :data:`_SIDE_PRIORITY`, so the
       output is independent of TOML transition-list ordering.  States not in the
       priority table retain their relative BFS order (sorted after the known states).
    4. Return ``"A → B → C"`` when there are no side states, or
       ``"A → B → C (+ D, E)"`` otherwise.

    Deterministic: given the same machine the output is always identical.

    Examples::

        linearize_lifecycle(guide_machine)   # "Draft → Published → Deprecated"
        linearize_lifecycle(adr_machine)     # "Proposed → Accepted → Superseded (+ ...)"
    """
    initial = machine.initial
    transitions = machine.transitions

    # Step 1: greedy spine — follow first unvisited outgoing transition.
    spine: list[str] = [initial]
    visited: set[str] = {initial}
    current = initial
    while True:
        next_state: str | None = None
        for candidate in transitions.get(current, []):
            if candidate not in visited:
                next_state = candidate
                break
        if next_state is None:
            break
        spine.append(next_state)
        visited.add(next_state)
        current = next_state

    # Step 2: BFS from initial to collect all reachable states in discovery order.
    bfs_order: list[str] = [initial]
    bfs_visited: set[str] = {initial}
    queue: list[str] = [initial]
    while queue:
        node = queue.pop(0)
        for nxt in transitions.get(node, []):
            if nxt not in bfs_visited:
                bfs_visited.add(nxt)
                bfs_order.append(nxt)
                queue.append(nxt)

    # Side states = reachable but not on the spine, sorted into canonical order.
    # Known states sort by their explicit priority; unknown states sort after them
    # in BFS-discovery order (secondary key = bfs position).
    spine_set: set[str] = set(spine)
    _unknown_rank = len(_SIDE_PRIORITY)
    side: list[str] = sorted(
        (s for s in bfs_order if s not in spine_set),
        key=lambda s: (_SIDE_PRIORITY.get(s, _unknown_rank), bfs_order.index(s)),
    )

    chain = " → ".join(spine)
    if side:
        return f"{chain} (+ {', '.join(side)})"
    return chain


def lifecycle_states_in_order(machine: Lifecycle) -> list[str]:
    """A deterministic listing of every state in ``machine``: BFS discovery order from
    ``initial`` (mirroring :func:`linearize_lifecycle`'s traversal), then any state left
    unreached (shouldn't normally happen) appended in sorted order.

    ``Lifecycle.states`` is a ``frozenset`` — its iteration order is hash-seed-dependent, so
    diagram-rendering callers (a Mermaid ``stateDiagram-v2``) need this instead to stay
    byte-stable across process runs.
    """
    order = [machine.initial]
    seen = {machine.initial}
    queue = [machine.initial]
    while queue:
        node = queue.pop(0)
        for nxt in machine.transitions.get(node, []):
            if nxt not in seen:
                seen.add(nxt)
                order.append(nxt)
                queue.append(nxt)
    order.extend(sorted(s for s in machine.states if s not in seen))
    return order


def lifecycle_edges(machine: Lifecycle) -> list[tuple[str, str]]:
    """Flattened ``(src, dst)`` transition edges for ``machine``, in the deterministic order
    given by :func:`lifecycle_states_in_order` — the basis for a Mermaid ``stateDiagram-v2``."""
    return [
        (src, dst)
        for src in lifecycle_states_in_order(machine)
        for dst in machine.transitions.get(src, [])
    ]


class WorkflowSpec(BaseModel):
    """The full loaded workflow specification.

    Built by ``load_workflow_spec()``. A module-level singleton is used via
    the free-function shims; equivalent methods are provided for callers that
    hold an explicit spec.

    ``extra="forbid"``: unknown TOML keys are rejected at construction time,
    matching the roles/playbook loaders.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    items: dict[str, ItemSpec]
    statuses: dict[str, StatusSpec]
    lifecycles: dict[str, Lifecycle]
    # Derived reverse indexes — built by the loader, not stored in TOML.
    prefix_to_type: dict[str, str]
    alias_to_type: dict[str, str]
    #: Reusable badge libraries, keyed by collection code — the vocabulary
    #: ``ItemSpec.fields``/``SubentityKindSpec.fields`` bind to (priority/severity are two
    #: bundled defaults, no longer special-cased enums).
    collections: dict[str, Collection] = {}
    #: Per-sub-entity-kind declarations (machine binding, CLI/storage vocabulary, and
    #: field bindings), keyed by kind name.
    subentity_kinds: dict[str, SubentityKindSpec] = {}

    # ------------------------------------------------------------------ convenience accessors

    def machine_for(self, item_type: str) -> Lifecycle:
        return self.lifecycles[self.items[item_type].lifecycle]

    def initial_status(self, item_type: str) -> str:
        return self.machine_for(item_type).initial

    def can_transition(self, item_type: str, src: str, dst: str) -> bool:
        return self.machine_for(item_type).can_transition(src, dst)

    def is_open(self, status: str) -> bool:
        return not self.statuses[status].terminal

    def parent_allowed(self, child: str, parent: str) -> bool:
        parents = self.items[child].parents
        return len(parents) == 0 or parent in parents

    def terminal_set(self) -> frozenset[str]:
        return frozenset(s for s, spec in self.statuses.items() if spec.terminal)

    def status_badge(self, status: str) -> str | None:
        spec = self.statuses.get(status)
        return spec.badge if spec else None

    def collection(self, code: str) -> Collection:
        """The reusable badge library named *code* (raises ``KeyError`` if undeclared)."""
        return self.collections[code]

    def fields_for(self, type_or_kind: str) -> list[Field]:
        """Declared fields for an item type OR a sub-entity kind (same lookup, either
        namespace — the two never collide in a valid spec)."""
        item = self.items.get(type_or_kind)
        if item is not None:
            return list(item.fields)
        kind_spec = self.subentity_kinds.get(type_or_kind)
        return list(kind_spec.fields) if kind_spec else []

    # ------------------------------------------------------------------ capability-flag accessors

    def work_types(self) -> frozenset[str]:
        """Non-roster types: work + records — every type whose category isn't roster."""
        return frozenset(t for t, ts in self.items.items() if ts.category != "roster")

    def item_is_roster(self, item_type: str) -> bool:
        """True when *item_type*'s category is roster (role, skill, operator)."""
        return self.items[item_type].category == "roster"

    def item_subentity_kind(self, item_type: str) -> str | None:
        """The sub-entity kind this type hosts, or None.

        Also returns None (rather than raising) when *item_type* isn't declared in this
        spec at all — a dropped/renamed type must cleanly lose its sub-entity check, not
        crash the caller.
        """
        ts = self.items.get(item_type)
        return ts.subentity_kind if ts else None

    def item_parent_required(self, item_type: str) -> str | None:
        """The required parent type slug, or None (no constraint)."""
        return self.items[item_type].parent_required

    def item_extra_fields(self, item_type: str) -> list[str]:
        """Declared generic ``extra``-metadata keys for this type (drives ``sq update --set``
        identity for a renamed/custom type, e.g. guide's ``tags``, review's ``target_ref``)."""
        ts = self.items.get(item_type)
        return list(ts.extra_fields) if ts else []

    def item_ref_rules(self, item_type: str) -> list[RefRule]:
        """Declared ref-kind rules for the type (e.g. fixes/addresses/supersedes)."""
        return list(self.items[item_type].ref_rules)

    def status_role(self, status: str) -> str | None:
        """Semantic role marker for this status (e.g. ``'superseded'``), or None."""
        spec = self.statuses.get(status)
        return spec.role if spec else None

    def workflow_for(self, item_type: str) -> Workflow:
        """Return the ``Workflow`` shim for the given item type."""
        return Workflow.from_machine(self.machine_for(item_type))

    def _subentity_machine(self, kind: str) -> Lifecycle:
        """The lifecycle machine bound to *kind* via ``SubentityKindSpec.lifecycle``."""
        return self.lifecycles[self.subentity_kinds[kind].lifecycle]

    def subentity_workflow(self, kind: str) -> Workflow:
        """Return the ``Workflow`` shim for the given sub-entity kind."""
        return Workflow.from_machine(self._subentity_machine(kind))

    def subentity_initial(self, kind: str) -> str:
        """Return the initial status for the given sub-entity kind."""
        return self._subentity_machine(kind).initial

    def subentity_can_transition(self, kind: str, src: str, dst: str) -> bool:
        """Return True if the given transition is valid for the given sub-entity kind."""
        return self._subentity_machine(kind).can_transition(src, dst)

    def subentity_completion(self, kind: str) -> str:
        """The sub-entity/finding kind's designated completion status.

        This is what the done-toggle resolves to instead of a hardcoded ``Done``/``Fixed``
        literal. An O(1) lookup — ``_check_completion_status`` guarantees at load time that
        a validated spec's ``completion`` names a reachable, non-initial status.
        """
        return self.subentity_kinds[kind].completion

    def subentity_plural(self, kind: str) -> str:
        """The kind's declared plural — the CLI list-verb name and container marker tag.

        Retires the static ``_SUBENTITY_PLURAL`` CLI table (kind -> plural was the last
        piece of hand-maintained sub-entity vocabulary).
        """
        return self.subentity_kinds[kind].plural

    def parent_hint(self, child: str) -> str:
        """Human guidance for an invalid parent (used in error messages).

        Appends the spec-declared ``RefRule.hint`` text(s) instead of re-detecting a
        literal ``fixes``/``addresses`` ref kind and emitting bundled "bug or review"
        prose — a renamed type or a custom ref rule gets its own declared hint verbatim.
        """
        parents = self.items[child].parents
        names = " or ".join(sorted(parents)) or "none"
        msg = f"a {child}'s parent must be of type {names}"
        hints = {r.hint for r in self.item_ref_rules(child) if r.hint}
        if hints:
            msg += "; " + "; ".join(sorted(hints))
        return msg

    # ------------------------------------------------------------------ validation

    @model_validator(mode="after")
    def _validate(self) -> WorkflowSpec:
        """Fail-closed validation."""
        all_statuses = set(self.statuses)
        all_lifecycle_names = set(self.lifecycles)
        all_types = set(self.items)
        errors: list[str] = []

        # Lifecycle initial/transition statuses exist.
        _check_lifecycle_statuses(self.lifecycles, all_statuses, errors)

        # Terminal statuses in the status set (always true by construction;
        # belt-and-braces check in case models are constructed programmatically).
        errors.extend(
            f"terminal status {s!r} not in status set"
            for s, spec in self.statuses.items()
            if spec.terminal and s not in all_statuses
        )

        # Reachability.
        _check_reachability(self.lifecycles, errors)

        # Every lifecycle must be able to reach a terminal status.
        _check_reachable_terminal(self.lifecycles, self.statuses, errors)

        # ItemSpec cross-refs + uniqueness.
        _check_item_refs(self.items, all_lifecycle_names, all_types, errors)

        # Parent-cycle detection in the type-parent graph.
        _check_parent_cycles(self.items, errors)

        # Field-code uniqueness + reserved-key collision (per item type / sub-entity kind).
        _check_field_codes(self.items, self.subentity_kinds, errors)

        # Field->collection referential integrity + default-badge resolution.
        _check_field_collections(self.items, self.subentity_kinds, self.collections, errors)

        # SubentityKindSpec.lifecycle reference + plural/local_prefix uniqueness.
        _check_subentity_kinds(self.items, self.subentity_kinds, all_lifecycle_names, errors)

        # Each declared sub-entity kind's completion names a reachable, non-initial status.
        _check_completion_status(self.subentity_kinds, self.lifecycles, errors)

        # Reserved-vocab floor — the spec must declare the three meta-types, each with
        # category = "roster". This is the ONLY type-axis floor: every other type
        # (built-in or custom) is ordinary spec vocabulary that may be omitted, renamed, or
        # re-prefixed. A missing meta-type OR one declared without category = "roster" fails
        # closed.
        spec_types = set(self.items)
        missing_meta = META_TYPES - spec_types
        if missing_meta:
            errors.append(f"spec missing required meta-types: {sorted(missing_meta)}")
        errors.extend(
            f"meta-type {t!r} must declare category = 'roster'"
            for t in sorted(META_TYPES & spec_types)
            if self.items[t].category != "roster"
        )

        # Reserved-vocab subset — spec must include the *structural floor* statuses: the
        # agent lifecycle (Draft/Active/Archived, module-level ``_RESERVED_FLOOR``), the only
        # statuses the engine references by literal name. Every other status is ordinary spec
        # vocabulary a custom spec may omit/rename/reorder; sub-entity/finding lifecycles bind
        # by machine role instead (see ``_check_completion_status``). A dropped status still
        # referenced by a declared lifecycle's initial/transitions is caught by the transition
        # check above, not by this floor.
        spec_statuses = set(self.statuses)
        missing_statuses = _RESERVED_FLOOR - spec_statuses
        if missing_statuses:
            errors.append(f"spec missing reserved Status members: {sorted(missing_statuses)}")

        if errors:
            from squads._errors import SquadsError

            raise SquadsError("Invalid workflow spec:\n" + "\n".join(f"  - {e}" for e in errors))

        return self
