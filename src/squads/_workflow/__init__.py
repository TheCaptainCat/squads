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
    """Whether *item_type* was a bundled built-in that *spec* (the active/merged spec) no
    longer declares.

    The merge engine has exactly one way to remove a key the bundled base declares:
    ``[selected]`` — deep-merge only ever adds or overwrites, never deletes on its own (see
    ``squads._specmerge``'s own docstring). So a name that WAS a bundled type and is absent
    from *spec* was, by construction, dropped via ``[selected]`` — never merely "undeclared".
    Every "unknown item type" refusal that can tell the two apart (a dropped built-in versus a
    name that was never bundled or declared at all — a genuine typo, or an as-yet-undeclared
    custom type) should use this to decide which message applies, and point a dropped type's
    refusal at the adopter's own ``selected.items`` line rather than asserting a plain
    "declare it or check for a typo" that is accurate for the other case but not this one.
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
