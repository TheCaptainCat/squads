"""Single authoritative resolver for per-type vocabulary (prefix).

Keeps ``_models`` spec-decoupled: callers hand the resolved values *to* the model;
the model never derives vocabulary itself.  The resolver lives in ``_models`` so
both model-layer code and service-layer code can import it without a cycle.

The loaded workflow spec is the SOLE vocabulary authority — there is no
reserved built-in prefix/folder map any more.  ``prefix_for`` is a thin spec lookup;
an unknown type (or a call with no spec at all) is an ordinary "unknown item type"
error, never a silent ``type.upper()`` guess.

Design note:
- ``prefix_for`` returns a prefix string.  It is intentionally *not* extended with
  a ``folder_for`` overload here — folder resolution already routes through
  ``SquadPaths.folder_for``/``squad_relative`` which consults the spec. Do NOT
  fold folder resolution in here without a dedicated design decision.
- A future ``subentity_plural`` accessor could be added to this module when the
  spec gains that vocabulary; do not pull it forward now.
"""

from typing import Any, cast

from squads._errors import SquadsError


def prefix_for(type_str: str, spec: object = None) -> str:
    """Return the canonical ID prefix for *type_str*.

    Resolution: ``spec.items[type_str].prefix`` — the loaded spec is the only
    vocabulary source, for every type (built-in or custom). Raises
    :class:`~squads._errors.SquadsError` when no spec is supplied, or the spec
    does not declare *type_str*; never falls back to a ``type.upper()`` guess.

    ``spec`` is typed as ``object`` so this module stays spec-decoupled
    (no import of ``WorkflowSpec``).  The caller is responsible for passing the
    correct type; duck-typed access is used with explicit ``cast`` to satisfy
    pyright strict mode.

    Designed so a ``subentity_plural`` accessor can be added beside this one
    without restructuring: just add ``subentity_plural_for(type_str, spec)``
    following the same pattern.
    """
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
        f"unknown item type {type_str!r}: no spec supplied, or the spec does not "
        "declare this type. Declare it in .overrides/workflow.toml or check for a typo."
    )
