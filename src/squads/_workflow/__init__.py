"""Per-type status workflows and transition validation.

Public API is identical to the old ``_workflow.py`` module — all import sites
work unchanged.  Internals are now backed by the loaded ``WorkflowSpec``
singleton (ADR-000214 F1).
"""

from dataclasses import dataclass

from squads._models._enums import (  # noqa: F401 — re-exported for callers
    ItemType,  # pyright: ignore[reportUnusedImport]
    Status,  # pyright: ignore[reportUnusedImport]
)
from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import (
    ItemSpec,
    Lifecycle,
    RefRule,
    StatusSpec,
    WorkflowSpec,
)

# Backward-compat aliases — existing callers that imported the old names continue to work.
StateMachine = Lifecycle
TypeSpec = ItemSpec

# ---------------------------------------------------------------------------
# Module-level singleton (loaded once on first import of this package).
# ---------------------------------------------------------------------------

_DEFAULT_SPEC: WorkflowSpec = load_workflow_spec()

# ---------------------------------------------------------------------------
# Backward-compat ``Workflow`` dataclass — existing code uses Workflow objects
# returned by ``workflow_for()`` and ``WORKFLOWS[t]``.  We keep the dataclass
# interface; instances now delegate to the loaded Lifecycle.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Workflow:
    """Thin shim: exposes the old ``Workflow`` interface backed by ``Lifecycle``.

    Status fields are ``str`` (TASK-000235).  Callers passing ``Status`` enum members
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
    def _from_machine(m: Lifecycle) -> Workflow:
        return Workflow(
            initial=m.initial,
            transitions={s: tuple(dsts) for s, dsts in m.transitions.items()},
        )


# ---------------------------------------------------------------------------
# Public constants — backed by the singleton
# ---------------------------------------------------------------------------

WORKFLOWS: dict[str, Workflow] = {
    t: Workflow._from_machine(_DEFAULT_SPEC.machine_for(t))  # pyright: ignore[reportPrivateUsage]
    for t in _DEFAULT_SPEC.items
}

_SUBENTITY_KINDS: frozenset[str] = frozenset({"subtask", "story", "finding"})

SUBENTITY_WORKFLOWS: dict[str, Workflow] = {
    kind: Workflow._from_machine(_DEFAULT_SPEC.lifecycles[kind])  # pyright: ignore[reportPrivateUsage]
    for kind in _SUBENTITY_KINDS
}

TERMINAL: frozenset[str] = _DEFAULT_SPEC.terminal_set()

ALLOWED_PARENTS: dict[str, set[str]] = {
    t: set(ts.parents)
    for t, ts in _DEFAULT_SPEC.items.items()
    if ts.parents  # empty list = unconstrained — omit from the map (matches old behavior)
}

# ---------------------------------------------------------------------------
# Free functions — thin shims over the singleton
# ---------------------------------------------------------------------------


def is_open(status: str) -> bool:
    return _DEFAULT_SPEC.is_open(status)


def parent_allowed(child: str, parent: str) -> bool:
    return _DEFAULT_SPEC.parent_allowed(child, parent)


def parent_hint(child: str) -> str:
    """Human guidance for an invalid parent (used in error messages)."""
    allowed = ALLOWED_PARENTS.get(child, set())
    names = " or ".join(sorted(allowed)) or "none"
    msg = f"a {child}'s parent must be of type {names}"
    # Append a hint about linking bugs/reviews for types that declare fixes/addresses ref rules.
    ref_rule_kinds = {r.kind for r in _DEFAULT_SPEC.item_ref_rules(child)}
    if "fixes" in ref_rule_kinds or "addresses" in ref_rule_kinds:
        msg += "; link a bug or review with `sq ref add <task> <id> --kind fixes|addresses`"
    return msg


def workflow_for(item_type: str) -> Workflow:
    return WORKFLOWS[item_type]


def initial_status(item_type: str) -> str:
    return WORKFLOWS[item_type].initial


def can_transition(item_type: str, src: str, dst: str) -> bool:
    return WORKFLOWS[item_type].can_transition(src, dst)


def subentity_workflow(kind: str) -> Workflow:
    return SUBENTITY_WORKFLOWS[kind]


def subentity_initial(kind: str) -> str:
    return SUBENTITY_WORKFLOWS[kind].initial


def subentity_can_transition(kind: str, src: str, dst: str) -> bool:
    return SUBENTITY_WORKFLOWS[kind].can_transition(src, dst)


# ---------------------------------------------------------------------------
# Capability-flag free functions (ADR-000232 §2 / TASK-000234)
# ---------------------------------------------------------------------------


def work_types() -> frozenset[str]:
    """Non-meta types: the units of work."""
    return _DEFAULT_SPEC.work_types()


def item_is_meta(item_type: str) -> bool:
    """True for role/skill/operator — the meta (non-work) types."""
    return _DEFAULT_SPEC.item_is_meta(item_type)


def item_has_severity(item_type: str) -> bool:
    """True for types that surface a severity field (today: bug only)."""
    return _DEFAULT_SPEC.item_has_severity(item_type)


def item_subentity_kind(item_type: str) -> str | None:
    """The sub-entity kind this type hosts, or None."""
    return _DEFAULT_SPEC.item_subentity_kind(item_type)


def item_parent_required(item_type: str) -> str | None:
    """Required parent type slug for this item type, or None."""
    return _DEFAULT_SPEC.item_parent_required(item_type)


def item_ref_rules(item_type: str) -> list[RefRule]:
    """Declared ref-kind rules for the type."""
    return _DEFAULT_SPEC.item_ref_rules(item_type)


def status_role(status: str) -> str | None:
    """Semantic role marker for this status (e.g. ``'superseded'``), or None."""
    return _DEFAULT_SPEC.status_role(status)


# ---------------------------------------------------------------------------
# Re-export the spec models for callers that want the explicit-spec surface
# ---------------------------------------------------------------------------

__all__ = [
    "ALLOWED_PARENTS",
    "SUBENTITY_WORKFLOWS",
    "TERMINAL",
    "WORKFLOWS",
    "ItemSpec",
    "Lifecycle",
    "RefRule",
    "StateMachine",
    "StatusSpec",
    "TypeSpec",
    "Workflow",
    "WorkflowSpec",
    "can_transition",
    "initial_status",
    "is_open",
    "item_has_severity",
    "item_is_meta",
    "item_parent_required",
    "item_ref_rules",
    "item_subentity_kind",
    "load_workflow_spec",
    "parent_allowed",
    "parent_hint",
    "status_role",
    "subentity_can_transition",
    "subentity_initial",
    "subentity_workflow",
    "work_types",
    "workflow_for",
]
