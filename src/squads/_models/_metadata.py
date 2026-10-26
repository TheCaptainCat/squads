"""Coercion and validation of attribute values against their declared kind.

Which attributes a type declares, and their kinds, come from the workflow spec; callers pass
the type's declarations in (``WorkflowSpec.item_attributes``). This module imports no spec
(``_models`` stays free of ``_workflow``).

Global fields (title/status/parent/author/assignee/labels) are dedicated `update` flags, and an
item-level badge (priority/severity or a custom field) is routed to its own setter; this module
covers only the type-declared attributes.
"""

from collections.abc import Mapping
from datetime import date
from typing import Any, cast

from squads._errors import SquadsError
from squads._models._attributes import AttributeKey, AttributeSpec

#: Global fields with their own `update` flags — named so `--set author=…` can hint to use the flag.
GLOBAL_FIELDS = frozenset(
    {"title", "description", "status", "parent", "author", "assignee", "labels"}
)

#: Role keys that are not settable here because a role verb or the role's definition owns them.
#: An operator reaching for one of them has a real intent and a real place to satisfy it, so the
#: refusal names that place rather than reporting an unknown field.
_ROLE_DEFINITION_KEYS: frozenset[str] = frozenset(
    {
        "job_title",
        "mission",
        "responsibilities",
        "agreements",
        "color",
        "can_spawn",
        "capabilities",
        "description",
    }
)

#: A role's display name is operator-settable on the item itself, through ``sq role activate
#: --name`` / ``sq dev add --name``, and the item's own top-level ``title`` is where it lives.
_ROLE_NAME_KEY: str = "full_name"

#: The developer marker an earlier release stored on a role; a developer is the role that holds a
#: capability the ``dev`` template declares.
_RETIRED_ROLE_DEV_KEY: str = "is_dev"

#: A role's skill list is a computed projection over the playbook and the index; a stored copy
#: of it is a retired mirror key.
_RETIRED_ROLE_SKILLS_KEY: str = "skills"

#: The retired mirror keys of a role item: the stored name copy, the skill list and the developer
#: marker. A closed, named set — never "every key this build does not recognise" — so a sweep
#: never deletes a key some other tool put on a role item.
RETIRED_ROLE_KEYS: frozenset[str] = frozenset(
    {_ROLE_NAME_KEY, _RETIRED_ROLE_SKILLS_KEY, _RETIRED_ROLE_DEV_KEY}
)


def settable(attributes: Mapping[str, AttributeSpec]) -> dict[str, AttributeSpec]:
    """The declared attributes ``sq update --set`` may write."""
    return {name: spec for name, spec in attributes.items() if spec.settable}


def coerce(key: str, spec: AttributeSpec, raw: str) -> Any:
    """*raw* (a command-line string) as a value of *spec*'s kind, or a ``SquadsError`` naming
    *key* when it does not parse."""
    if spec.kind == "list":
        return [part.strip() for part in raw.split(",") if part.strip()]
    if spec.kind == "bool":
        return _coerce_bool(key, raw)
    if spec.kind == "date":
        return _coerce_date(key, raw)
    return raw


def _coerce_bool(key: str, raw: str) -> bool:
    text = raw.strip().lower()
    if text in ("1", "true", "yes", "on"):
        return True
    if text in ("0", "false", "no", "off"):
        return False
    raise SquadsError(f"{key!r} expects true or false; got {raw!r}")


def _coerce_date(key: str, raw: str) -> str:
    """Normalise a calendar-date value to ``YYYY-MM-DD``, refusing (rather than storing)
    anything ``date.fromisoformat`` can't parse."""
    try:
        return date.fromisoformat(raw.strip()).isoformat()
    except ValueError as exc:
        raise SquadsError(f"{key!r} expects an ISO date (YYYY-MM-DD); got {raw!r}") from exc


def value_problem(spec: AttributeSpec, value: Any) -> str | None:
    """Why *value* is not a value of *spec*'s kind, or ``None`` when it is."""
    if _is_kind(spec.kind, value):
        return None
    return f"expected {_kind_phrase(spec.kind)}, got {_describe(value)}"


def _is_kind(kind: str, value: Any) -> bool:
    if kind == "str":
        return isinstance(value, str)
    if kind == "bool":
        return isinstance(value, bool)
    if kind == "list":
        return isinstance(value, list) and all(
            isinstance(part, str) for part in cast("list[Any]", value)
        )
    return _is_iso_date(value)


def _kind_phrase(kind: str) -> str:
    if kind == "str":
        return "a string"
    if kind == "list":
        return "a list of strings"
    if kind == "bool":
        return "true or false"
    return "an ISO date (YYYY-MM-DD)"


def _is_iso_date(value: Any) -> bool:
    if isinstance(value, date):
        return True
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value.strip())
    except ValueError:
        return False
    return True


def _describe(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, dict):
        return "a mapping"
    if isinstance(value, list):
        return "a list"
    return f"{type(value).__name__} {value!r}"


def coerce_attribute(
    item_type: str, key: str, raw: str, attributes: Mapping[str, AttributeSpec]
) -> Any:
    """Validate ``key`` is a settable attribute of ``item_type`` and coerce ``raw`` to its kind."""
    return coerce(key, require_settable(item_type, key, attributes), raw)


def require_settable(
    item_type: str, key: str, attributes: Mapping[str, AttributeSpec]
) -> AttributeSpec:
    """The settable attribute named ``key`` on ``item_type``, or a ``SquadsError`` listing the
    valid ones — the one check ``set`` and ``unset`` share."""
    fields = settable(attributes)
    spec = fields.get(key)
    if spec is None:
        valid = ", ".join(sorted(fields)) or "(none)"
        hint = _refusal_hint(item_type, key, attributes)
        raise SquadsError(f"{key!r} is not a settable field on a {item_type}{hint}; valid: {valid}")
    return spec


def _refusal_hint(item_type: str, key: str, attributes: Mapping[str, AttributeSpec]) -> str:
    """The remedy clause for an unsettable *key*, empty when there is nothing true to say.

    The role clauses are gated on ``item_type``: the same key name means different things on
    different types, and sending an operator to a role override document from a skill's refusal
    would be a remedy that does not apply."""
    if item_type == "role":
        if key in (_ROLE_NAME_KEY, "title"):
            return (
                " — a role's name lives on the item's own `title` field; set it with"
                " `sq role <slug> update --title`"
            )
        if key in _ROLE_DEFINITION_KEYS:
            return (
                " — a role's definition is set with `sq role <slug> update`"
                " (item-defined roles only), or declared in `.overrides/roles/<slug>.toml`"
            )
    if key == AttributeKey.PRONOUNS and item_type in ("role", "operator"):
        return f" — set it with `sq {item_type} <addr> update --pronouns`"
    if key in attributes:
        return " (a dedicated command owns it)"
    if key in GLOBAL_FIELDS:
        return " (use the dedicated --<flag>)"
    return ""
