"""WorkflowSpec pydantic v2 value objects (ADR-000214 §1).

Enum-typed fields stay enum-typed: TOML string values are coerced into
``ItemType``/``Status`` at parse/load time — an unknown name raises immediately.
"""

from pydantic import BaseModel, ConfigDict, model_validator

from squads._models._enums import ItemType, Status


class Lifecycle(BaseModel):
    """A named lifecycle state machine: initial state + transition map.

    ``.states`` is derived (initial union all sources union all targets),
    mirroring ``Workflow.states`` today.
    """

    model_config = ConfigDict(frozen=True)

    initial: Status
    transitions: dict[Status, list[Status]]

    @property
    def states(self) -> frozenset[Status]:
        seen: set[Status] = {self.initial}
        for src, dsts in self.transitions.items():
            seen.add(src)
            seen.update(dsts)
        return frozenset(seen)

    def can_transition(self, src: Status, dst: Status) -> bool:
        return dst in self.transitions.get(src, [])


class ItemSpec(BaseModel):
    """Vocabulary for one ``ItemType``: prefix, folder, lifecycle, parents, aliases."""

    model_config = ConfigDict(frozen=True)

    prefix: str
    folder: str
    lifecycle: str
    parents: list[ItemType] = []
    aliases: list[str] = []


class StatusSpec(BaseModel):
    """Terminal flag + optional sub-entity badge for one ``Status``."""

    model_config = ConfigDict(frozen=True)

    terminal: bool
    badge: str | None = None


# ---------------------------------------------------------------------------
# Validation helpers (extracted to keep _validate under complexity limits)
# ---------------------------------------------------------------------------

_SUBENTITY_KINDS: frozenset[str] = frozenset({"subtask", "story", "finding"})


def _check_lifecycle_statuses(
    lifecycles: dict[str, Lifecycle],
    all_statuses: set[Status],
    errors: list[str],
) -> None:
    """§5-1 + §5-2: check initial and transition src/dst are declared statuses."""
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
    """§5-4: every state in a lifecycle must be reachable from initial."""
    for name, m in lifecycles.items():
        reachable: set[Status] = {m.initial}
        queue = [m.initial]
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


def _check_item_refs(
    items: dict[ItemType, ItemSpec],
    all_lifecycle_names: set[str],
    all_types: set[ItemType],
    errors: list[str],
) -> None:
    """§5-5: ItemSpec lifecycle/parent references + prefix/folder/alias uniqueness."""
    seen_prefixes: dict[str, ItemType] = {}
    seen_folders: dict[str, ItemType] = {}
    seen_aliases: dict[str, ItemType] = {}

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


class WorkflowSpec(BaseModel):
    """The full loaded workflow specification (ADR-000214 §1).

    Built by ``load_workflow_spec()``; in F1 a module-level singleton is used
    everywhere via the free-function shims.  Equivalent methods are provided
    for surfaces that will later receive the spec explicitly (F3+).
    """

    model_config = ConfigDict(frozen=True)

    items: dict[ItemType, ItemSpec]
    statuses: dict[Status, StatusSpec]
    lifecycles: dict[str, Lifecycle]
    # Derived reverse indexes — built by the loader, not stored in TOML.
    prefix_to_type: dict[str, ItemType]
    alias_to_type: dict[str, ItemType]

    # ------------------------------------------------------------------ convenience accessors

    @property
    def managed_types(self) -> frozenset[ItemType]:
        return frozenset(self.items)

    def machine_for(self, item_type: ItemType) -> Lifecycle:
        return self.lifecycles[self.items[item_type].lifecycle]

    def initial_status(self, item_type: ItemType) -> Status:
        return self.machine_for(item_type).initial

    def can_transition(self, item_type: ItemType, src: Status, dst: Status) -> bool:
        return self.machine_for(item_type).can_transition(src, dst)

    def is_open(self, status: Status) -> bool:
        return not self.statuses[status].terminal

    def parent_allowed(self, child: ItemType, parent: ItemType) -> bool:
        parents = self.items[child].parents
        return len(parents) == 0 or parent in parents

    def terminal_set(self) -> frozenset[Status]:
        return frozenset(s for s, spec in self.statuses.items() if spec.terminal)

    def subentity_machine(self, kind: str) -> Lifecycle:
        return self.lifecycles[kind]

    def status_badge(self, status: Status) -> str | None:
        spec = self.statuses.get(status)
        return spec.badge if spec else None

    # ------------------------------------------------------------------ validation

    @model_validator(mode="after")
    def _validate(self) -> WorkflowSpec:
        """Fail-closed validation (ADR-000214 §5)."""
        all_statuses = set(self.statuses)
        all_lifecycle_names = set(self.lifecycles)
        all_types = set(self.items)
        errors: list[str] = []

        # §5-1 + §5-2: lifecycle initial/transition statuses exist.
        _check_lifecycle_statuses(self.lifecycles, all_statuses, errors)

        # §5-3: terminal statuses in the status set (always true by construction;
        # belt-and-braces check in case models are constructed programmatically).
        errors.extend(
            f"terminal status {s!r} not in status set"
            for s, spec in self.statuses.items()
            if spec.terminal and s not in all_statuses
        )

        # §5-4: reachability.
        _check_reachability(self.lifecycles, errors)

        # §5-5: ItemSpec cross-refs + uniqueness.
        _check_item_refs(self.items, all_lifecycle_names, all_types, errors)

        # §5-6a: enums-intact — spec item set must equal set(ItemType).
        spec_types = set(self.items)
        enum_types = set(ItemType)
        if spec_types != enum_types:
            missing = enum_types - spec_types
            extra = spec_types - enum_types
            if missing:
                errors.append(f"spec missing ItemType members: {sorted(str(m) for m in missing)}")
            if extra:
                errors.append(
                    f"spec introduces unknown ItemType members: {sorted(str(e) for e in extra)}"
                )

        # §5-6b: enums-intact — spec status set must equal set(Status).
        spec_statuses = set(self.statuses)
        enum_statuses = set(Status)
        if spec_statuses != enum_statuses:
            missing_s = enum_statuses - spec_statuses
            extra_s = spec_statuses - enum_statuses
            if missing_s:
                errors.append(f"spec missing Status members: {sorted(str(s) for s in missing_s)}")
            if extra_s:
                errors.append(
                    f"spec introduces unknown Status members: {sorted(str(s) for s in extra_s)}"
                )

        if errors:
            from squads._errors import SquadsError

            raise SquadsError(
                "Invalid bundled workflow spec:\n" + "\n".join(f"  - {e}" for e in errors)
            )

        return self
