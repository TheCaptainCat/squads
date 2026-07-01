"""Single authoritative resolver for per-type vocabulary (prefix, folder).

Keeps ``_models`` spec-decoupled: callers hand the resolved values *to* the model;
the model never derives vocabulary itself.  The resolver lives in ``_models`` so
both model-layer code and service-layer code can import it without a cycle.

Reserved built-in vocabulary is declared once here — this is the EPIC-206
reserved-type invariant's single source of truth for prefix/folder.  The spec
(``WorkflowSpec``) mirrors these values and is the authority for custom types;
the built-in map is the authority for reserved types so that a bad override cannot
accidentally redefine a built-in prefix.

Design note (ADR-000266):
- ``prefix_for`` returns a prefix string.  It is intentionally *not* extended with
  a ``folder_for`` overload in this task — folder resolution already routes through
  ``SquadPaths.folder_for``/``squad_relative`` which consults the spec.  Do NOT
  fold folder resolution in here until a dedicated task decides it.
- FEAT-000212 may add a ``subentity_plural`` accessor to this module when the spec
  gains that vocabulary; do not pull it forward now.
"""

from typing import TYPE_CHECKING, Any, cast

from squads._errors import SquadsError

if TYPE_CHECKING:
    pass  # no runtime imports needed here; spec is typed as object below

# ---------------------------------------------------------------------------
# Reserved built-in vocabulary (EPIC-206 invariant)
# Mirrors ``default_workflow.toml`` exactly.  Must NOT be edited to add custom
# types — custom types go in ``.overrides/workflow.toml``.
# ---------------------------------------------------------------------------

#: Authoritative prefix per reserved built-in type.
#: This is the one map that drives the ``prefix_for`` resolver for reserved types.
RESERVED_PREFIX: dict[str, str] = {
    "epic": "EPIC",
    "feature": "FEAT",
    "task": "TASK",
    "bug": "BUG",
    "decision": "ADR",
    "review": "REV",
    "guide": "GUIDE",
    "role": "ROLE",
    "skill": "SKILL",
    "operator": "OP",
}

#: Authoritative folder per reserved built-in type (squad-folder-relative).
#: Mirrors ``default_workflow.toml``.
RESERVED_FOLDER: dict[str, str] = {
    "epic": "epics",
    "feature": "features",
    "task": "tasks",
    "bug": "bugs",
    "decision": "adrs",
    "review": "reviews",
    "guide": "guides",
    "role": "agents/roles",
    "skill": "agents/skills",
    "operator": "operators",
}

#: Reverse map — prefix string → reserved type string.
#: Used by ``type_for_id`` for the built-in prefix fast-path.
RESERVED_TYPE_BY_PREFIX: dict[str, str] = {v: k for k, v in RESERVED_PREFIX.items()}


def is_reserved(type_str: str) -> bool:
    """Return True when *type_str* is a reserved built-in type."""
    return type_str in RESERVED_PREFIX


def prefix_for(type_str: str, spec: object = None) -> str:
    """Return the canonical ID prefix for *type_str*.

    Resolution order:
    1. Reserved built-in type → ``RESERVED_PREFIX[type_str]`` (never overridable).
    2. Custom type with a spec supplied → ``spec.items[type_str].prefix``.
    3. Otherwise → raises :class:`~squads._errors.SquadsError`.

    ``spec`` is typed as ``object`` so this module stays spec-decoupled
    (no import of ``WorkflowSpec``).  The caller is responsible for passing the
    correct type; duck-typed access is used with explicit ``cast`` to satisfy
    pyright strict mode.

    Designed so FEAT-000212 can add a ``subentity_plural`` accessor beside this
    one without restructuring: just add ``subentity_plural_for(type_str, spec)``
    following the same pattern.
    """
    if type_str in RESERVED_PREFIX:
        return RESERVED_PREFIX[type_str]
    if spec is not None:
        try:
            item_map = cast("dict[str, Any]", getattr(spec, "items", {}))
            item_spec = item_map.get(type_str)
            if item_spec is not None:
                prefix = cast("str", getattr(item_spec, "prefix", ""))
                if prefix:
                    return prefix
        except AttributeError, TypeError:
            pass
    raise SquadsError(
        f"unknown item type {type_str!r}: not a reserved built-in and no spec supplied "
        "(or the spec does not declare this type). "
        "Declare a custom type in .overrides/workflow.toml or check for a typo."
    )
