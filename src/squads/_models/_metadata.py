"""Declarative schema of the per-item-type ``extra`` metadata that ``sq update --set`` may write.

Global fields (title/status/parent/author/assignee/labels) are dedicated `update` flags; this module
covers only the **type-specific** `extra` keys, with the value kind used to coerce the CLI string.
Identity/derived keys (``slug``, ``is_dev``) are intentionally absent — they're not settable.

Item-level bug severity is no longer one of these ``extra`` keys — it's a top-level, spec-declared
badge field (``Item.severity``); ``ItemsMixin._apply_extra`` routes ``--set severity=`` onto it
directly (validated against the spec's ``severity`` collection), a frozen per-axis shim until a
follow-up generalizes ``--set`` over every declared field.
"""

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

#: Settable ``extra`` fields per item type. Types absent here have no type-specific metadata.
#: Keyed by str so callers with a widened Item.type (str) can look up without casting.
EXTRA_FIELDS: dict[str, tuple[Field, ...]] = {
    "role": _ROLE_FIELDS,
    "skill": (Field(X.WHEN_TO_USE), Field(X.ALLOWED_TOOLS), Field(X.MODEL)),
    "guide": (Field(X.TAGS, "list"),),
    "review": (Field(X.TARGET_REF),),
}

#: Global fields with their own `update` flags — named so `--set author=…` can hint to use the flag.
GLOBAL_FIELDS = frozenset(
    {"title", "description", "status", "parent", "author", "assignee", "labels"}
)


def settable(item_type: str) -> dict[str, Field]:
    return {f.key: f for f in EXTRA_FIELDS.get(item_type, ())}


def coerce(field: Field, raw: str) -> Any:
    if field.kind == "list":
        return [part.strip() for part in raw.split(",") if part.strip()]
    if field.kind == "bool":
        return raw.strip().lower() in ("1", "true", "yes", "on")
    return raw


def coerce_extra(item_type: str, key: str, raw: str) -> Any:
    """Validate ``key`` is settable for ``item_type`` and coerce ``raw`` to its value kind."""
    fields = settable(item_type)
    field = fields.get(key)
    if field is None:
        valid = ", ".join(sorted(fields)) or "(none)"
        hint = " (use the dedicated --<flag>)" if key in GLOBAL_FIELDS else ""
        raise SquadsError(f"{key!r} is not a settable field on a {item_type}{hint}; valid: {valid}")
    return coerce(field, raw)
