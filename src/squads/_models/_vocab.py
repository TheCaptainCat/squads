"""Single authoritative resolver for per-type vocabulary (prefix, display labels), kept in
``_models`` so model-layer and service-layer code import it without a cycle while the model never
derives vocabulary itself. The loaded workflow spec is the sole authority: ``prefix_for`` is a thin
spec lookup, and an unknown type or missing spec is an ordinary "unknown item type" error, never a
``type.upper()`` guess. Folder resolution stays in ``SquadPaths.folder_for``/``squad_relative``; do
not fold it in here without a dedicated design decision.

``label_for`` resolves a type's display name in one of four forms
(``singular``/``plural``/``singular_lower``/``plural_lower``) and, unlike ``prefix_for``, degrades
to a computed fallback (``_fallback_label``, its one home) for an undeclared type or missing spec.
"""

from typing import Any, Literal, cast

from squads._errors import SquadsError

type LabelForm = Literal["singular", "plural", "singular_lower", "plural_lower"]


def prefix_for(type_str: str, spec: object) -> str:
    """Return the canonical ID prefix for *type_str*, from ``spec.items[type_str].prefix`` for every
    type. It raises :class:`~squads._errors.SquadsError` when the spec does not declare it and never
    guesses. ``spec`` is typed ``object`` (duck-typed with a ``cast``) so this module imports no
    ``WorkflowSpec``.
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
    """Return *type_str*'s display label in *form*: the pinned
    ``spec.items[type_str].labels.<form>`` when present and non-empty, else the computed fallback
    (:func:`_fallback_label`). Unlike :func:`prefix_for` a missing ``spec`` or undeclared type is
    not an error, since the fallback needs only *type_str*; ``spec`` is typed ``object`` as there.
    """
    pinned = _pinned_label(type_str, form, spec)
    return pinned if pinned else _fallback_label(type_str, form)
