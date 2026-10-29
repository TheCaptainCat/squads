"""Badge/status-badge presentation helpers: resolve a spec-declared badge to emoji + label.

Pure presentation over the workflow spec's declared collections/fields — no discussion or
sub-entity concerns live here (see :mod:`squads._discussion` for that).
"""

import math
import re
from collections.abc import Callable

from squads._workflow import WorkflowSpec
from squads._workflow._models import Field

#: Neutral fallback badge for a status/collection that declares none — never crash.
_DEFAULT_BADGE = "⚪"


def resolve_badges(
    spec: WorkflowSpec, type_or_kind: str, badge_value: Callable[[str], str | None]
) -> dict[str, str]:
    """Every declared badge field *type_or_kind* carries, keyed by field code, non-null values only.

    Generic over the type's or kind's actual axes (e.g. a custom impact/urgency pair), not a
    fixed ``priority``/``severity``. ``badge_value`` is the entity's own getter
    (``Item.badge_value``/``SubEntity.badge_value``), so it serves items and sub-entities alike. It
    is the map ``sq graph --json`` ships as ``GraphNode.badges`` and every other item-bearing
    ``--json`` surface reuses.
    """
    return {
        f.code: value
        for f in spec.fields_for(type_or_kind)
        if (value := badge_value(f.code)) is not None
    }


def first_ordered_field(spec: WorkflowSpec) -> Field | None:
    """The first declared field, across every non-roster type, whose collection is ``ordered``.

    Types are scanned in declaration order (``ItemSpec.order``, type name); squads' "priority" is
    the bundled example. Generated prose that teaches "the ordered axis" (the squads skill's
    ``--priority`` line) must not probe one hardcoded type: dropping it would delete the axis from
    the prose while other types still declare it. ``None`` when no non-roster type declares one.
    """
    for item_type in sorted(spec.non_roster_types(), key=lambda t: (spec.items[t].order, t)):
        for f in spec.fields_for(item_type):
            coll = spec.collections.get(f.collection)
            if coll is not None and coll.ordered:
                return f
    return None


def status_badge(status_value: str, spec: WorkflowSpec) -> str:
    """``"InProgress"`` → ``"🟡 In Progress"`` (emoji + spaced label) for the header.

    The badge is resolved from the spec's declared ``StatusSpec.badge`` (built-in or custom); a
    status that declares none — including any custom status the bundled/default spec doesn't know
    about — falls back to the neutral :data:`_DEFAULT_BADGE` rather than crashing.
    """
    label = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", status_value)
    emoji = spec.status_badge(status_value) or _DEFAULT_BADGE
    return f"{emoji} {label}".strip()


def primary_field_code(kind: str, spec: WorkflowSpec, *, default: str = "severity") -> str:
    """The first field a sub-entity *kind* (or item type) declares, shown beside its container.

    Templates must not hardcode the code (``'severity'``): a spec that replaces the kind's field
    (``finding`` to ``impact``) still has a first field. Falls back to *default* only when the
    kind declares none, as :func:`field_label`/:func:`field_default` do, so the template still
    renders.
    """
    fields = spec.fields_for(kind)
    return fields[0].code if fields else default


def declared_collection(type_or_kind: str, field_code: str, spec: WorkflowSpec) -> str | None:
    """The collection code *type_or_kind* binds *field_code* to, or ``None``: the strict resolver.

    There is no same-name fallback. Use it when the answer decides whether a surface is offered or
    a value accepted: :func:`resolve_collection`'s fallback is for rendering stored values, and
    deciding with it would advertise a flag that can only error (a type declaring only ``urgency``
    would "resolve" ``priority`` to the bundled collection, and the CLI would offer ``--priority``
    while the service gate refuses every code).
    """
    field = next((f for f in spec.fields_for(type_or_kind) if f.code == field_code), None)
    return field.collection if field else None


def field_badge_codes(field_code: str, spec: WorkflowSpec) -> list[str]:
    """Every badge code any declared non-roster type's binding of *field_code* accepts.

    In type-declaration order, de-duplicated; ``[]`` when no type binds the field. It is the
    vocabulary for a cross-type door, such as the ``--priority`` filter of ``sq list``/``tree``,
    where no single type's collection is the authority.
    """
    codes: list[str] = []
    for item_type in sorted(spec.non_roster_types(), key=lambda t: (spec.items[t].order, t)):
        coll_code = declared_collection(item_type, field_code, spec)
        coll = spec.collections.get(coll_code) if coll_code else None
        if coll is None:
            continue
        codes.extend(b.code for b in coll.badges if b.code not in codes)
    return codes


def resolve_collection(type_or_kind: str, field_code: str, spec: WorkflowSpec) -> str:
    """The collection code a declared field is bound to (``fields_for(type_or_kind)``).

    Falls back to *field_code* itself when the field is not declared (a dropped or renamed field,
    or a frozen migration-era call), so the bundled ``priority``/``severity`` fields keep working
    with no spec in hand. Rendering only: the fallback keeps a stored value rendering after its
    field is dropped, and must never decide whether a flag is advertised or a value valid, since a
    same-named collection would answer for an undeclared field. Use :func:`declared_collection`
    for those.
    """
    return declared_collection(type_or_kind, field_code, spec) or field_code


def field_label(kind: str, field_code: str, spec: WorkflowSpec) -> str:
    """The declared ``Field.label`` for *field_code* on *kind* (item type or sub-entity kind).

    Falls back to the title-cased code when the field isn't declared — same graceful posture
    as :func:`resolve_collection`, so a template can relabel an axis (e.g. severity->impact)
    with no code change, and degrades sanely rather than crashing on a dropped field.
    """
    field = next((f for f in spec.fields_for(kind) if f.code == field_code), None)
    return field.label if field else field_code.title()


def field_default(kind: str, field_code: str, spec: WorkflowSpec) -> str | None:
    """A valid example or fallback value for *field_code* on *kind*.

    The field's own ``default``, else its collection's ``default``, else the collection's first
    badge, as ``Service.field_default`` (the add-<kind> CLI's omitted-flag fallback) gives, so a
    template hint shows the value the CLI would apply. An undeclared field is resolved directly as a
    collection code, as in :func:`resolve_collection`.
    """
    field = next((f for f in spec.fields_for(kind) if f.code == field_code), None)
    if field and field.default:
        return field.default
    coll = spec.collections.get(field.collection if field else field_code)
    if coll is None:
        return None
    if coll.default:
        return coll.default
    return coll.badges[0].code if coll.badges else None


def collection_legend(collection_code: str, spec: WorkflowSpec) -> str:
    """A ``" · "``-joined ``emoji code`` readout for every badge in *collection_code* — the
    review findings legend / any other flat-scale readout. Empty string if the collection is
    undeclared."""
    coll = spec.collections.get(collection_code)
    if not coll:
        return ""
    return " · ".join(f"{b.emoji or _DEFAULT_BADGE} {b.code}" for b in coll.badges)


def badge_parts(collection_code: str, code: str, spec: WorkflowSpec) -> tuple[str, str, str]:
    """``(emoji, code, label)`` for one declared badge in *collection_code* — the decomposed
    form behind :func:`badge_render`, for a caller that needs the parts separately (e.g. a
    JSON payload carrying structured badge metadata) rather than one rendered string. A
    missing collection/badge degrades to :data:`_DEFAULT_BADGE` + the raw/title-cased code,
    same graceful fallback as :func:`badge_render`.
    """
    coll = spec.collections.get(collection_code)
    badge = next((b for b in coll.badges if b.code == code), None) if coll else None
    emoji = (badge.emoji if badge and badge.emoji else None) or _DEFAULT_BADGE
    label = badge.label if badge else code.title()
    return emoji, code, label


def badge_render(
    collection_code: str, code: str, spec: WorkflowSpec, *, as_label: bool = False
) -> str:
    """One badge renderer for every flat presentation axis (priority, severity, …).

    ``as_label=False`` renders emoji plus raw code (list/panel/summary); ``as_label=True`` emoji
    plus Title-case label (head/pane title). It resolves *collection_code* in the given, bundled
    or active spec via :func:`badge_parts`, and degrades on a missing collection or badge rather
    than crashing, like :func:`status_badge`.
    """
    emoji, raw_code, label = badge_parts(collection_code, code, spec)
    text = label if as_label else raw_code
    return f"{emoji} {text}"


def badge_rank(type_or_kind: str, field_code: str, value: str | None, spec: WorkflowSpec) -> float:
    """The position of *value* in the ordered collection *type_or_kind* binds *field_code* to
    (lower first); a value that does not resolve sorts last."""
    collection = declared_collection(type_or_kind, field_code, spec)
    coll = spec.collections.get(collection) if collection else None
    if coll is None or value is None:
        return math.inf
    codes = [b.code for b in coll.badges]
    return codes.index(value) if value in codes else math.inf
