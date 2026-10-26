"""Per-type status workflows and transition validation.

Workflow capabilities live as methods on ``WorkflowSpec``. This module holds the bundled-spec
accessor and the names the rest of the package imports from here.

There is no process-global mutable state here: per-invocation spec context is
owned by ``Service`` and threaded explicitly through call sites.
"""

from squads._workflow._lifecycle_order import linearize_lifecycle
from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import (
    CATEGORIES,
    ROSTER_OPERATOR,
    ROSTER_ROLE,
    ROSTER_SKILL,
    StatusSpec,
    WorkflowSpec,
)

# ---------------------------------------------------------------------------
# Immutable bundled spec — loaded once at import; never rebindable.
# ---------------------------------------------------------------------------

_BUNDLED_SPEC: WorkflowSpec = load_workflow_spec()


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


def dropped_via_selected(item_type: str, spec: WorkflowSpec) -> bool:
    """Whether *item_type* was a bundled built-in that *spec* (the active/merged spec) no longer
    declares. ``[selected]`` is the merge engine's only way to remove a bundled key (deep-merge
    never deletes), so a name that was a bundled type and is absent from *spec* was dropped via
    ``[selected]``, not merely undeclared. An "unknown item type" refusal uses this to point a
    dropped type at the adopter's own ``selected.items`` line instead of the "declare it or check
    for a typo" message that fits a never-bundled name.
    """
    return item_type not in spec.items and item_type in bundled_spec().items


__all__ = [
    "CATEGORIES",
    "ROSTER_OPERATOR",
    "ROSTER_ROLE",
    "ROSTER_SKILL",
    "StatusSpec",
    "WorkflowSpec",
    "bundled_spec",
    "dropped_via_selected",
    "linearize_lifecycle",
    "load_workflow_spec",
]
