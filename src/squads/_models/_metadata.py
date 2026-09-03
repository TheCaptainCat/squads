"""Declarative schema of the per-item-type ``extra`` metadata that ``sq update --set`` may write.

Global fields (title/status/parent/author/assignee/labels) are dedicated `update` flags; this module
covers only the **type-specific** `extra` keys, with the value kind used to coerce the CLI string.
Identity/derived keys (``slug``, ``is_dev``) are intentionally absent — they're not settable.

Item-level bug severity is no longer one of these ``extra`` keys — it's a top-level, spec-declared
badge field (``Item.severity``); ``ItemsMixin._apply_extra`` routes ``--set severity=`` onto it
directly (validated against the spec's ``severity`` collection), a frozen per-axis shim until a
follow-up generalizes ``--set`` over every declared field.

Role/skill entries stay keyed by their literal type name below — both are reserved roster types
(``WorkflowSpec.ROSTER_TYPES``), bound by name elsewhere in the engine already, so hardcoding them
here doesn't create a new rename hazard. Every ordinary work type (guide/review's tags/target_ref)
instead advertises its generic keys via the spec (``ItemSpec.extra_fields`` /
``WorkflowSpec.item_extra_fields``) — callers pass the resolved keys in, so a renamed guide/review
(or a custom type declaring the same key) keeps the field settable. This module has no spec import
(``_models`` stays dependency-free of ``_workflow``, per the project's layering).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from squads._errors import SquadsError
from squads._models._extras import ExtraKey as X

Kind = Literal["str", "list", "bool", "date"]


@dataclass(frozen=True)
class Field:
    key: str
    kind: Kind = "str"


#: Settable ``extra`` fields on a role. Narrow on purpose: a role's definition is resolved
#: from the role catalog on every read, not stored, so a key that merely *looks* settable here
#: would accept a value nothing reads and no writer ever refreshes. What is left is the
#: stored state with no catalog answer — a developer's ``model`` and ``tech``, and the
#: default-role designation. See :data:`_ROLE_DECLARED_IN_OVERRIDES` for where the rest is
#: declared now, and :func:`coerce_extra` for the refusal that names it.
_ROLE_FIELDS: tuple[Field, ...] = (
    Field(X.MODEL),
    Field(X.IS_DEFAULT, "bool"),
    Field(X.TECH),  # only meaningful for dev roles, harmless elsewhere
)

#: Role ``extra`` keys that used to be settable here and are now resolved from the role
#: catalog. An operator reaching for one of them has a real intent and there is a real place
#: to satisfy it, so the refusal names that place rather than reporting an unknown field —
#: this is the remedy half of the narrowing above, not decoration.
_ROLE_DECLARED_IN_OVERRIDES: frozenset[str] = frozenset(
    {
        X.TITLE,
        X.MISSION,
        X.RESPONSIBILITIES,
        X.AGREEMENTS,
        X.COLOR,
        X.CAN_SPAWN,
        X.DESCRIPTION,
    }
)

#: The one moved key whose remedy is *not* an override document: a role's display name is
#: operator-settable on the item itself, through ``sq role activate --name`` / ``sq dev add
#: --name``, and the item's own top-level ``title`` is where it lives.
_ROLE_NAME_KEY: str = X.FULL_NAME

#: The role ``extra`` keys that a release before this one mirrored onto the item from the
#: role's resolved definition, and that no writer in this build produces any more — the two
#: refusal groups above united — each of them names a key that moved out of ``extra`` in that
#: same change and each refusal already has to stay in step with it — plus the one retired key
#: with no member left to name it (see :data:`_RETIRED_ROLE_SKILLS_KEY`).
#:
#: Declared here rather than restated by the reader so the two can never drift: a key that
#: comes back would have to leave one of the groups above, and a key that leaves must lose its
#: refusal at the same time. It is a **closed, named** set, never "every key this build does
#: not recognise" — an ``extra`` key some other tool put on a role item is not this build's to
#: interpret, let alone to delete.
#:
#: Four keys the mirror also wrote are deliberately absent, each because something still
#: writes it: ``slug`` by ``RoleDef.to_extra`` itself; ``model`` by the same method for a
#: developer role, which makes it a question about a role's *shape* rather than one this set
#: can answer; ``is_dev``/``tech`` by ``sq dev add``; and ``is_default`` by
#: ``sq role set-default``.
#: The one retired key with no :class:`ExtraKey` member to name it by. ``extra.skills`` was a
#: cache of a role's skill list; the list is a computed projection over the playbook and the
#: index (``Service.resolved_skills_for_role``), so the cache, its writer and its ``ExtraKey``
#: member were all deleted together. The member's absence is why this is spelled out rather
#: than referenced, and the reason to keep the name at all is that a corpus written before
#: that deletion still carries the key: a name has to survive its constant long enough to be
#: removed from disk.
_RETIRED_ROLE_SKILLS_KEY: str = "skills"

RETIRED_ROLE_EXTRA_KEYS: frozenset[str] = (
    _ROLE_DECLARED_IN_OVERRIDES | {_ROLE_NAME_KEY} | {_RETIRED_ROLE_SKILLS_KEY}
)

#: Settable ``extra`` fields for the two reserved roster types. Keyed by str so callers with a
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
    X.TECH: Field(X.TECH),
    X.TARGET_DATE: Field(X.TARGET_DATE, "date"),
}

#: Global fields with their own `update` flags — named so `--set author=…` can hint to use the flag.
GLOBAL_FIELDS = frozenset(
    {"title", "description", "status", "parent", "author", "assignee", "labels"}
)


def settable(item_type: str, extra_keys: Iterable[str] = ()) -> dict[str, Field]:
    """Settable ``extra`` fields for *item_type*: its reserved roster-type fields (if any) plus
    the caller-resolved generic keys (``spec.item_extra_fields(item_type)`` for a work type)."""
    result = {f.key: f for f in EXTRA_FIELDS.get(item_type, ())}
    result.update({k: _GENERIC_FIELDS[k] for k in extra_keys if k in _GENERIC_FIELDS})
    return result


def coerce(field: Field, raw: str) -> Any:
    if field.kind == "list":
        return [part.strip() for part in raw.split(",") if part.strip()]
    if field.kind == "bool":
        return raw.strip().lower() in ("1", "true", "yes", "on")
    if field.kind == "date":
        return _coerce_date(field.key, raw)
    return raw


def _coerce_date(key: str, raw: str) -> str:
    """Normalise a calendar-date ``extra`` value to ``YYYY-MM-DD``, refusing (rather than
    storing) anything ``date.fromisoformat`` can't parse — the field name travels with the
    refusal so a caller sees which key was rejected, not just that some value was."""
    try:
        return date.fromisoformat(raw.strip()).isoformat()
    except ValueError as exc:
        raise SquadsError(f"{key!r} expects an ISO date (YYYY-MM-DD); got {raw!r}") from exc


def coerce_extra(item_type: str, key: str, raw: str, extra_keys: Iterable[str] = ()) -> Any:
    """Validate ``key`` is settable for ``item_type`` and coerce ``raw`` to its value kind.

    *extra_keys* is the spec-resolved list of generic extra-field keys this type advertises
    (``WorkflowSpec.item_extra_fields``) — passed in by the caller, which holds the spec.
    """
    fields = settable(item_type, extra_keys)
    field = fields.get(key)
    if field is None:
        valid = ", ".join(sorted(fields)) or "(none)"
        hint = _refusal_hint(item_type, key)
        raise SquadsError(f"{key!r} is not a settable field on a {item_type}{hint}; valid: {valid}")
    return coerce(field, raw)


def _refusal_hint(item_type: str, key: str) -> str:
    """The remedy clause :func:`coerce_extra`'s refusal carries for an unsettable *key*.

    Empty when there is nothing true to say — a key that never had a home gets the plain
    refusal rather than an invented remedy.

    The role clauses come first and are gated on ``item_type``, because these key names are
    not role-only and the same word means two different things on a role item: ``title`` is
    the *role's* title in ``extra`` and the role holder's display name at the top level, and
    ``description``/``model`` mean something else again on a skill. Sending an operator to a
    role override document from a skill's refusal, or to the top-level flag for a value that
    is now a catalog answer, would each be a remedy that does not apply.
    """
    if item_type == "role":
        if key == _ROLE_NAME_KEY:
            return (
                " — a role's name lives on the item's own `title` field; set it with"
                " `sq role activate --name` / `sq dev add --name`"
            )
        if key in _ROLE_DECLARED_IN_OVERRIDES:
            return (
                " — a role's definition is resolved from the role catalog, not stored on the"
                " item; declare it in `.overrides/roles.toml`, or in"
                " `.overrides/roles/<slug>.toml` for a project-defined role"
            )
    if key in GLOBAL_FIELDS:
        return " (use the dedicated --<flag>)"
    return ""
