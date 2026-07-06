"""WorkflowSpec pydantic v2 value objects.

TOML string values are coerced into ``ItemType``/``Status`` at parse/load
time — an unknown name raises immediately.

The capability flags declared here (``is_meta``, ``subentity_kind``,
``severity_field``, ``parent_required``, ``ref_rules``, and ``StatusSpec.role``)
are additive and not yet consumed by the engine. They are encoded in
``default_workflow.toml``.
"""

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, model_validator

from squads._models._enums import ItemType

# ---------------------------------------------------------------------------
# Workflow dataclass — the thin shim over Lifecycle
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Workflow:
    """Thin shim: exposes the ``Workflow`` interface backed by ``Lifecycle``.

    Status fields are ``str``. Callers passing ``Status`` enum members
    continue to work because ``Status`` is a ``StrEnum`` — its members compare equal
    to their plain string values.
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

    Status fields are ``str`` — ``Status`` enum members are retained as the
    reserved-vocabulary source but are not used as the stored field type.  Since
    ``Status`` is a ``StrEnum`` its members compare equal to their string values, so
    callers passing ``Status.DONE`` or passing ``"Done"`` both work.
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


class ItemSpec(BaseModel):
    """Vocabulary for one ``ItemType``: prefix, folder, lifecycle, parents, aliases.

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

    # ------------------------------------------------------------------
    # Capability flags (additive; not yet consumed by engine)
    # ------------------------------------------------------------------

    is_meta: bool = False
    """True for the meta-types (role/skill/operator): outside WORK_TYPES, no work lifecycle,
    slug-keyed identity, retype-ineligible, self-author bypass for bootstrap."""

    subentity_kind: str | None = None
    """The kind of sub-entity this type hosts: ``"story"`` | ``"subtask"`` | ``"finding"``
    or ``None`` for types that have no sub-entities (epic/bug/decision/guide/meta-types)."""

    severity_field: bool = False
    """True when this type surfaces a severity badge (today: bug only)."""

    parent_required: str | None = None
    """The required parent type expressed as a string (e.g. ``"feature"`` for task).
    ``None`` means the type is unconstrained (any parent or none is valid)."""

    ref_rules: list[RefRule] = []
    """Declared ref-kind rules that drive parent_hint text and sq check enforcement
    (e.g. task → fixes/addresses; decision → supersedes)."""


class StatusSpec(BaseModel):
    """Terminal flag + optional sub-entity badge for one ``Status``."""

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


# Canonical priority order for well-known exception/side states.
# States that appear together in the side-state list are sorted by this priority
# (lower = earlier in the output), ensuring the output matches the established
# convention regardless of the order they happen to be discovered in BFS
# (e.g. Blocked before Cancelled in work-item lifecycles, WontFix first in bug).
# States not in this table retain their relative BFS-discovery order by sorting
# after all explicitly-ranked states via the fallback rank (len(_SIDE_PRIORITY)).
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

    # ------------------------------------------------------------------ convenience accessors

    @property
    def managed_types(self) -> frozenset[str]:
        return frozenset(self.items)

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

    def subentity_machine(self, kind: str) -> Lifecycle:
        return self.lifecycles[kind]

    def status_badge(self, status: str) -> str | None:
        spec = self.statuses.get(status)
        return spec.badge if spec else None

    # ------------------------------------------------------------------ capability-flag accessors

    def work_types(self) -> frozenset[str]:
        """Types that are units of work (not meta-types: role/skill/operator)."""
        return frozenset(t for t, ts in self.items.items() if not ts.is_meta)

    def item_is_meta(self, item_type: str) -> bool:
        """True for the meta-types: role, skill, operator."""
        return self.items[item_type].is_meta

    def item_has_severity(self, item_type: str) -> bool:
        """True for types that surface a severity field (today: bug only)."""
        return self.items[item_type].severity_field

    def item_subentity_kind(self, item_type: str) -> str | None:
        """The sub-entity kind this type hosts, or None."""
        return self.items[item_type].subentity_kind

    def item_parent_required(self, item_type: str) -> str | None:
        """The required parent type slug, or None (no constraint)."""
        return self.items[item_type].parent_required

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

    def subentity_workflow(self, kind: str) -> Workflow:
        """Return the ``Workflow`` shim for the given sub-entity kind."""
        return Workflow.from_machine(self.lifecycles[kind])

    def subentity_initial(self, kind: str) -> str:
        """Return the initial status for the given sub-entity kind."""
        return self.lifecycles[kind].initial

    def subentity_can_transition(self, kind: str, src: str, dst: str) -> bool:
        """Return True if the given transition is valid for the given sub-entity kind."""
        return self.lifecycles[kind].can_transition(src, dst)

    def parent_hint(self, child: str) -> str:
        """Human guidance for an invalid parent (used in error messages)."""
        parents = self.items[child].parents
        names = " or ".join(sorted(parents)) or "none"
        msg = f"a {child}'s parent must be of type {names}"
        ref_rule_kinds = {r.kind for r in self.item_ref_rules(child)}
        if "fixes" in ref_rule_kinds or "addresses" in ref_rule_kinds:
            msg += "; link a bug or review with `sq ref add <task> <id> --kind fixes|addresses`"
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

        # Reserved-vocab subset — spec must include ALL reserved ItemType members.
        # A custom spec may ADD new types but must never OMIT a reserved one.
        spec_types = set(self.items)
        reserved_types: set[str] = {t.value for t in ItemType}
        missing_types = reserved_types - spec_types
        if missing_types:
            errors.append(f"spec missing reserved ItemType members: {sorted(missing_types)}")

        # Reserved-vocab subset — spec must include the *structural floor* statuses.
        #
        # The floor is the subset of Status members that the engine references by name
        # (not just by lifecycle transitions), so a custom spec MUST always declare them:
        #
        #   • agent lifecycle (role/skill/operator): Draft, Active, Archived
        #   • sub-entity lifecycles (subtask/story): Todo, InProgress, Blocked, Done, Cancelled
        #   • finding lifecycle: Open, Fixed, Verified, WontFix
        #
        # Work-item-only statuses (Ready, InReview, Proposed, Accepted, Requested,
        # ChangesRequested, Approved, Rejected, Superseded, Deprecated, Published) are NOT in
        # the floor — a custom spec that omits them (e.g. no ADR/review/guide lifecycle) must
        # not be rejected.  The work-item vocabularies are enforced implicitly by the
        # lifecycle initial/transition statuses check above (they must be declared).
        spec_statuses = set(self.statuses)
        _RESERVED_FLOOR: frozenset[str] = frozenset(
            {
                # agent lifecycle
                "Draft",
                "Active",
                "Archived",
                # sub-entity (subtask/story)
                "Todo",
                "InProgress",
                "Blocked",
                "Done",
                "Cancelled",
                # finding lifecycle
                "Open",
                "Fixed",
                "Verified",
                "WontFix",
            }
        )
        missing_statuses = _RESERVED_FLOOR - spec_statuses
        if missing_statuses:
            errors.append(f"spec missing reserved Status members: {sorted(missing_statuses)}")

        if errors:
            from squads._errors import SquadsError

            raise SquadsError("Invalid workflow spec:\n" + "\n".join(f"  - {e}" for e in errors))

        return self
