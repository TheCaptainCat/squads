"""Declarative schema of the per-item-type ``extra`` metadata that ``sq update --set`` may write.

Global fields (title/status/parent/author/assignee/labels) are dedicated `update` flags; this module
covers only the **type-specific** `extra` keys, with the value kind used to coerce the CLI string.
Identity/derived keys (``slug``, ``is_dev``) are intentionally absent — they're not settable.

Item-level bug severity is no longer one of these ``extra`` keys — it's a top-level, spec-declared
badge field (``Item.severity``); ``ItemsMixin._apply_extra`` routes ``--set severity=`` onto it
directly (validated against the spec's ``severity`` collection), a frozen per-axis shim until a
follow-up generalizes ``--set`` over every declared field.

Role/skill entries stay keyed by their literal type name below — both are reserved meta-types
(``WorkflowSpec.META_TYPES``), bound by name elsewhere in the engine already, so hardcoding them
here doesn't create a new rename hazard. Every ordinary work type (guide/review's tags/target_ref)
instead advertises its generic keys via the spec (``ItemSpec.extra_fields`` /
``WorkflowSpec.item_extra_fields``) — callers pass the resolved keys in, so a renamed guide/review
(or a custom type declaring the same key) keeps the field settable. This module has no spec import
(``_models`` stays dependency-free of ``_workflow``, per the project's layering).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal

from squads._errors import SquadsError
from squads._models._extras import ExtraKey as X

Kind = Literal["str", "list", "bool"]


@dataclass(frozen=True)
class Field:
    key: str
    kind: Kind = "str"


_ROLE_FIELDS: tuple[Field, ...] = (
    Field(X.FULL_NAME),
    Field(X.TITLE),
    Field(X.MISSION),
    Field(X.RESPONSIBILITIES, "list"),
    Field(X.MODEL),
    Field(X.COLOR),
    Field(X.SKILLS, "list"),
    Field(X.IS_DEFAULT, "bool"),
    Field(X.TECH),  # only meaningful for dev roles, harmless elsewhere
)

#: Settable ``extra`` fields for the two reserved meta-types. Keyed by str so callers with a
#: widened Item.type (str) can look up without casting.
EXTRA_FIELDS: dict[str, tuple[Field, ...]] = {
    "role": _ROLE_FIELDS,
    "skill": (Field(X.WHEN_TO_USE), Field(X.ALLOWED_TOOLS), Field(X.MODEL)),
}

#: Catalog of generic (non-badge) extra fields any spec-declared work type may advertise by key
#: (``ItemSpec.extra_fields``) — identity is the ``ExtraKey`` value, never a type's literal name.
_GENERIC_FIELDS: dict[str, Field] = {
    X.TAGS: Field(X.TAGS, "list"),
    X.TARGET_REF: Field(X.TARGET_REF),
}

#: Global fields with their own `update` flags — named so `--set author=…` can hint to use the flag.
GLOBAL_FIELDS = frozenset(
    {"title", "description", "status", "parent", "author", "assignee", "labels"}
)


def settable(item_type: str, extra_keys: Iterable[str] = ()) -> dict[str, Field]:
    """Settable ``extra`` fields for *item_type*: its reserved meta-type fields (if any) plus
    the caller-resolved generic keys (``spec.item_extra_fields(item_type)`` for a work type)."""
    result = {f.key: f for f in EXTRA_FIELDS.get(item_type, ())}
    result.update({k: _GENERIC_FIELDS[k] for k in extra_keys if k in _GENERIC_FIELDS})
    return result


def coerce(field: Field, raw: str) -> Any:
    if field.kind == "list":
        return [part.strip() for part in raw.split(",") if part.strip()]
    if field.kind == "bool":
        return raw.strip().lower() in ("1", "true", "yes", "on")
    return raw


def coerce_extra(item_type: str, key: str, raw: str, extra_keys: Iterable[str] = ()) -> Any:
    """Validate ``key`` is settable for ``item_type`` and coerce ``raw`` to its value kind.

    *extra_keys* is the spec-resolved list of generic extra-field keys this type advertises
    (``WorkflowSpec.item_extra_fields``) — passed in by the caller, which holds the spec.
    """
    fields = settable(item_type, extra_keys)
    field = fields.get(key)
    if field is None:
        valid = ", ".join(sorted(fields)) or "(none)"
        hint = " (use the dedicated --<flag>)" if key in GLOBAL_FIELDS else ""
        raise SquadsError(f"{key!r} is not a settable field on a {item_type}{hint}; valid: {valid}")
    return coerce(field, raw)
