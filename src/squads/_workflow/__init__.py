"""Per-type status workflows and transition validation.

Public API is identical to the old ``_workflow.py`` module — all import sites
work unchanged.  Internals are now backed by the loaded ``WorkflowSpec``
singleton (ADR-000214 F1).
"""

from dataclasses import dataclass

from squads._models._enums import ItemType, Status
from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import (
    ItemSpec,
    Lifecycle,
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
    """Thin shim: exposes the old ``Workflow`` interface backed by ``Lifecycle``."""

    initial: Status
    transitions: dict[Status, tuple[Status, ...]]

    @property
    def states(self) -> set[Status]:
        seen: set[Status] = {self.initial}
        for src, dsts in self.transitions.items():
            seen.add(src)
            seen.update(dsts)
        return seen

    def can_transition(self, src: Status, dst: Status) -> bool:
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

WORKFLOWS: dict[ItemType, Workflow] = {
    t: Workflow._from_machine(_DEFAULT_SPEC.machine_for(t))  # pyright: ignore[reportPrivateUsage]
    for t in ItemType
}

_SUBENTITY_KINDS: frozenset[str] = frozenset({"subtask", "story", "finding"})

SUBENTITY_WORKFLOWS: dict[str, Workflow] = {
    kind: Workflow._from_machine(_DEFAULT_SPEC.lifecycles[kind])  # pyright: ignore[reportPrivateUsage]
    for kind in _SUBENTITY_KINDS
}

TERMINAL: frozenset[Status] = _DEFAULT_SPEC.terminal_set()

ALLOWED_PARENTS: dict[ItemType, set[ItemType]] = {
    t: set(ts.parents)
    for t, ts in _DEFAULT_SPEC.items.items()
    if ts.parents  # empty list = unconstrained — omit from the map (matches old behavior)
}

# ---------------------------------------------------------------------------
# Free functions — thin shims over the singleton
# ---------------------------------------------------------------------------


def is_open(status: Status) -> bool:
    return _DEFAULT_SPEC.is_open(status)


def parent_allowed(child: ItemType, parent: ItemType) -> bool:
    return _DEFAULT_SPEC.parent_allowed(child, parent)


def parent_hint(child: ItemType) -> str:
    """Human guidance for an invalid parent (used in error messages).

    The ``if child is ItemType.TASK`` branch is left as-is in F1 (ADR §3:
    behavior-preserving; reifying it as spec vocabulary is F2).
    """
    allowed = ALLOWED_PARENTS.get(child, set())
    names = " or ".join(sorted(t.value for t in allowed)) or "none"
    msg = f"a {child.value}'s parent must be of type {names}"
    if child is ItemType.TASK:
        msg += "; link a bug or review with `sq ref add <task> <id> --kind fixes|addresses`"
    return msg


def workflow_for(item_type: ItemType) -> Workflow:
    return WORKFLOWS[item_type]


def initial_status(item_type: ItemType) -> Status:
    return WORKFLOWS[item_type].initial


def can_transition(item_type: ItemType, src: Status, dst: Status) -> bool:
    return WORKFLOWS[item_type].can_transition(src, dst)


def subentity_workflow(kind: str) -> Workflow:
    return SUBENTITY_WORKFLOWS[kind]


def subentity_initial(kind: str) -> Status:
    return SUBENTITY_WORKFLOWS[kind].initial


def subentity_can_transition(kind: str, src: Status, dst: Status) -> bool:
    return SUBENTITY_WORKFLOWS[kind].can_transition(src, dst)


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
    "StateMachine",
    "StatusSpec",
    "TypeSpec",
    "Workflow",
    "WorkflowSpec",
    "can_transition",
    "initial_status",
    "is_open",
    "load_workflow_spec",
    "parent_allowed",
    "parent_hint",
    "subentity_can_transition",
    "subentity_initial",
    "subentity_workflow",
    "workflow_for",
]
