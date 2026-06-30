"""Per-type status workflows and transition validation.

All workflow capabilities are now methods on ``WorkflowSpec`` (FEAT-000250 /
TASK-000251).  This module keeps a stable bundled-spec constant for the module-level
shims and the backward-compat public API (``WORKFLOWS``, ``TERMINAL``, etc.) that
the golden-lock test asserts.

The process-global mutable singleton (``_active_spec`` list, ``_terminal_ref`` cell,
in-place dict mutation) has been deleted (FEAT-000250).  All per-invocation spec
context is now owned by ``Service`` (TASK-000252) and threaded explicitly through
call sites.
"""

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
    Workflow,
    WorkflowSpec,
    linearize_lifecycle,
)

# Backward-compat aliases — existing callers that imported the old names continue to work.
StateMachine = Lifecycle
TypeSpec = ItemSpec

# ---------------------------------------------------------------------------
# Immutable bundled spec — loaded once at import; never rebindable.
# ---------------------------------------------------------------------------

_BUNDLED_SPEC: WorkflowSpec = load_workflow_spec()

# ---------------------------------------------------------------------------
# Module-level constants backed by the immutable bundled spec.
#
# These are read-only views over the bundled spec.  To use a different spec,
# construct a WorkflowSpec and pass it explicitly (e.g. self.spec in Service).
#
# WORKFLOWS / SUBENTITY_WORKFLOWS / ALLOWED_PARENTS / TERMINAL are kept for the
# golden-lock tests (test_workflow_spec.py) and any callers that imported them
# directly; they always reflect the bundled spec.
# ---------------------------------------------------------------------------

_SUBENTITY_KINDS: frozenset[str] = frozenset({"subtask", "story", "finding"})


def _make_workflows(spec: WorkflowSpec) -> dict[str, Workflow]:
    return {t: Workflow.from_machine(spec.machine_for(t)) for t in spec.items}


def _make_subentity_workflows(spec: WorkflowSpec) -> dict[str, Workflow]:
    return {
        kind: Workflow.from_machine(spec.lifecycles[kind])
        for kind in _SUBENTITY_KINDS
        if kind in spec.lifecycles
    }


def _make_allowed_parents(spec: WorkflowSpec) -> dict[str, set[str]]:
    return {
        t: set(ts.parents)
        for t, ts in spec.items.items()
        if ts.parents  # empty list = unconstrained — omit (matches old behavior)
    }


WORKFLOWS: dict[str, Workflow] = _make_workflows(_BUNDLED_SPEC)
SUBENTITY_WORKFLOWS: dict[str, Workflow] = _make_subentity_workflows(_BUNDLED_SPEC)
ALLOWED_PARENTS: dict[str, set[str]] = _make_allowed_parents(_BUNDLED_SPEC)
TERMINAL: frozenset[str] = _BUNDLED_SPEC.terminal_set()


# ---------------------------------------------------------------------------
# Bundled-spec accessor
# ---------------------------------------------------------------------------


def bundled_spec() -> WorkflowSpec:
    """Return the bundled default ``WorkflowSpec``.

    The bundled spec is loaded once at import and is immutable.  Use this to
    obtain the default spec without side effects (e.g. for constructing an
    ``IndexStore`` or ``Service`` with no override).
    """
    return _BUNDLED_SPEC


def active_spec() -> WorkflowSpec:
    """Return the bundled default ``WorkflowSpec``.

    The per-invocation spec context lives on ``Service.spec`` (TASK-000252);
    the CLI per-invocation handle lives in ``_common.get_active_spec()`` (TASK-000253).
    This function always returns the immutable bundled spec.
    """
    return _BUNDLED_SPEC


# ---------------------------------------------------------------------------
# Free functions — thin shims over the bundled spec.
#
# These delegate to the bundled spec.  Service call sites use self.spec.<method>
# (TASK-000252); CLI call sites use _common.get_active_spec() (TASK-000253).
# ---------------------------------------------------------------------------


def is_open(status: str) -> bool:
    return _BUNDLED_SPEC.is_open(status)


def parent_allowed(child: str, parent: str) -> bool:
    return _BUNDLED_SPEC.parent_allowed(child, parent)


def parent_hint(child: str) -> str:
    """Human guidance for an invalid parent (used in error messages)."""
    return _BUNDLED_SPEC.parent_hint(child)


def workflow_for(item_type: str) -> Workflow:
    return _BUNDLED_SPEC.workflow_for(item_type)


def initial_status(item_type: str) -> str:
    return _BUNDLED_SPEC.initial_status(item_type)


def can_transition(item_type: str, src: str, dst: str) -> bool:
    return _BUNDLED_SPEC.can_transition(item_type, src, dst)


def subentity_workflow(kind: str) -> Workflow:
    return _BUNDLED_SPEC.subentity_workflow(kind)


def subentity_initial(kind: str) -> str:
    return _BUNDLED_SPEC.subentity_initial(kind)


def subentity_can_transition(kind: str, src: str, dst: str) -> bool:
    return _BUNDLED_SPEC.subentity_can_transition(kind, src, dst)


# ---------------------------------------------------------------------------
# Capability-flag free functions
# ---------------------------------------------------------------------------


def work_types() -> frozenset[str]:
    """Non-meta types: the units of work."""
    return _BUNDLED_SPEC.work_types()


def item_is_meta(item_type: str) -> bool:
    """True for role/skill/operator — the meta (non-work) types."""
    return _BUNDLED_SPEC.item_is_meta(item_type)


def item_has_severity(item_type: str) -> bool:
    """True for types that surface a severity field (today: bug only)."""
    return _BUNDLED_SPEC.item_has_severity(item_type)


def item_subentity_kind(item_type: str) -> str | None:
    """The sub-entity kind this type hosts, or None."""
    return _BUNDLED_SPEC.item_subentity_kind(item_type)


def item_parent_required(item_type: str) -> str | None:
    """Required parent type slug for this item type, or None."""
    return _BUNDLED_SPEC.item_parent_required(item_type)


def item_ref_rules(item_type: str) -> list[RefRule]:
    """Declared ref-kind rules for the type."""
    return _BUNDLED_SPEC.item_ref_rules(item_type)


def status_role(status: str) -> str | None:
    """Semantic role marker for this status (e.g. ``'superseded'``), or None."""
    return _BUNDLED_SPEC.status_role(status)


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
    "active_spec",
    "bundled_spec",
    "can_transition",
    "initial_status",
    "is_open",
    "item_has_severity",
    "item_is_meta",
    "item_parent_required",
    "item_ref_rules",
    "item_subentity_kind",
    "linearize_lifecycle",
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
