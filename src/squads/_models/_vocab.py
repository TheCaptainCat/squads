"""Single authoritative resolver for per-type vocabulary (prefix, display labels).

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

``label_for`` is a second, independent resolver on the same module: a type's
human-readable display name, in one of four named forms (``singular`` / ``plural`` /
``singular_lower`` / ``plural_lower``). Unlike ``prefix_for``, an undeclared type or a missing
``spec`` is not an error here — a display label is always derivable from the bare type-name
string, so ``label_for`` degrades to the computed fallback instead of raising. The fallback
formula lives in exactly one place (``_fallback_label``); ``label_for`` is the only call site
consumers use.
"""

from typing import Any, Literal, cast

from squads._errors import SquadsError

type LabelForm = Literal["singular", "plural", "singular_lower", "plural_lower"]


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
        # Parenthesized (not PEP 758 bare-tuple) so `vulture` can still parse this file;
        # ruff's py314-target formatter would otherwise strip the parens back off.
        except (AttributeError, TypeError):  # fmt: skip
            pass
    raise SquadsError(
        f"unknown item type {type_str!r}: no spec supplied, or the spec does not "
        "declare this type. Declare it in .overrides/workflow.toml or check for a typo."
    )


def _fallback_label(type_str: str, form: LabelForm) -> str:
    """The single place the pin-else-derive fallback formula is computed.

    ``singular`` <- ``type.capitalize()``; ``singular_lower`` <- ``type.lower()``; the two
    plural forms naively append ``"s"`` to their singular counterpart.
    """
    singular = type_str.capitalize()
    if form == "singular":
        return singular
    singular_lower = type_str.lower()
    if form == "singular_lower":
        return singular_lower
    if form == "plural":
        return singular + "s"
    return singular_lower + "s"


def _pinned_label(type_str: str, form: LabelForm, spec: object) -> str | None:
    """The ``spec.items[type_str].labels.<form>`` lookup, duck-typed like ``prefix_for``.

    Returns ``None`` (never raises) for a missing spec, an undeclared type, an absent
    ``labels`` table, or an unset form — every one of those is an ordinary "fall back to the
    computed form" case, not an error (a display label is always derivable from the bare
    type-name string).
    """
    if spec is None:
        return None
    try:
        item_map = cast("dict[str, Any]", getattr(spec, "items", {}))
        item_spec = item_map.get(type_str)
        if item_spec is None:
            return None
        labels = getattr(item_spec, "labels", None)
        if labels is None:
            return None
        return cast("str | None", getattr(labels, form, None))
    # Parenthesized (not PEP 758 bare-tuple) so `vulture` can still parse this file;
    # ruff's py314-target formatter would otherwise strip the parens back off.
    except (AttributeError, TypeError):  # fmt: skip
        return None


def labels_for(type_str: str, spec: object = None) -> dict[str, str]:
    """All four resolved display-label forms for *type_str* (pin-else-derive per form)."""
    forms: tuple[LabelForm, ...] = ("singular", "plural", "singular_lower", "plural_lower")
    return {form: label_for(type_str, form, spec) for form in forms}


def label_for(type_str: str, form: LabelForm, spec: object = None) -> str:
    """Return *type_str*'s display label in the requested *form*.

    Resolution: the pinned ``spec.items[type_str].labels.<form>`` when present and non-empty,
    else the computed fallback for that form (see :func:`_fallback_label`). Unlike
    :func:`prefix_for`, a missing ``spec`` or an undeclared type is not an error — the fallback
    needs only *type_str* itself, so ``label_for`` always returns a usable string.

    ``spec`` is typed as ``object`` so this module stays spec-decoupled (no import of
    ``WorkflowSpec``); duck-typed access mirrors ``prefix_for``.
    """
    pinned = _pinned_label(type_str, form, spec)
    return pinned if pinned else _fallback_label(type_str, form)
