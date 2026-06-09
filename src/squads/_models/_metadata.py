"""Declarative schema of the per-item-type ``extra`` metadata that ``sq update --set`` may write.

Global fields (title/status/parent/author/assignee/labels) are dedicated `update` flags; this module
covers only the **type-specific** `extra` keys, with the value kind used to coerce the CLI string.
Identity/derived keys (``slug``, ``is_dev``) are intentionally absent — they're not settable.
"""

from dataclasses import dataclass
from typing import Any, Literal

from squads._errors import SquadsError
from squads._models._enums import ItemType, Severity
from squads._models._extras import ExtraKey as X

Kind = Literal["str", "list", "bool", "severity"]


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
EXTRA_FIELDS: dict[ItemType, tuple[Field, ...]] = {
    ItemType.ROLE: _ROLE_FIELDS,
    ItemType.SKILL: (Field(X.WHEN_TO_USE), Field(X.ALLOWED_TOOLS), Field(X.MODEL)),
    ItemType.GUIDE: (Field(X.TAGS, "list"),),
    ItemType.REVIEW: (Field(X.TARGET_REF),),
    ItemType.BUG: (Field(X.SEVERITY, "severity"),),
}

#: Global fields with their own `update` flags — named so `--set author=…` can hint to use the flag.
GLOBAL_FIELDS = frozenset(
    {"title", "description", "status", "parent", "author", "assignee", "labels"}
)


def settable(item_type: ItemType) -> dict[str, Field]:
    return {f.key: f for f in EXTRA_FIELDS.get(item_type, ())}


def coerce(field: Field, raw: str) -> Any:
    if field.kind == "list":
        return [part.strip() for part in raw.split(",") if part.strip()]
    if field.kind == "bool":
        return raw.strip().lower() in ("1", "true", "yes", "on")
    if field.kind == "severity":
        try:
            return Severity(raw.strip().lower()).value
        except ValueError:
            choices = ", ".join(s.value for s in Severity)
            raise SquadsError(f"invalid severity {raw!r} (one of: {choices})") from None
    return raw


def coerce_extra(item_type: ItemType, key: str, raw: str) -> Any:
    """Validate ``key`` is settable for ``item_type`` and coerce ``raw`` to its value kind."""
    fields = settable(item_type)
    field = fields.get(key)
    if field is None:
        valid = ", ".join(sorted(fields)) or "(none)"
        hint = " (use the dedicated --<flag>)" if key in GLOBAL_FIELDS else ""
        raise SquadsError(
            f"{key!r} is not a settable field on a {item_type.value}{hint}; valid: {valid}"
        )
    return coerce(field, raw)
