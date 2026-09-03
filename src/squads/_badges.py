"""Badge/status-badge presentation helpers: resolve a spec-declared badge to emoji + label.

Pure presentation over the workflow spec's declared collections/fields — no discussion or
sub-entity concerns live here (see :mod:`squads._discussion` for that).
"""

import re
from collections.abc import Callable

from squads._workflow import WorkflowSpec, bundled_spec
from squads._workflow._models import Field

#: Neutral fallback badge for a status/collection that declares none — never crash.
_DEFAULT_BADGE = "⚪"


def resolve_badges(
    spec: WorkflowSpec, type_or_kind: str, badge_value: Callable[[str], str | None]
) -> dict[str, str]:
    """Every declared badge field *type_or_kind* carries, resolved generically — the
    type/sub-entity-kind's actual axes (e.g. a custom impact/urgency pair) rather than the
    fixed ``priority``/``severity`` attributes, keyed by field code, non-null values only.

    ``badge_value`` is the entity's own getter (``Item.badge_value`` / ``SubEntity.badge_value``)
    so this stays agnostic of which model it's resolving for — an item or a sub-entity.

    This is the shape ``sq graph --json`` already ships (``GraphNode.badges``); every other
    item-bearing ``--json`` surface (``tree``/``list``/``show`` + its ``subentities``) reuses it
    rather than re-deriving the same map.
    """
    return {
        f.code: value
        for f in spec.fields_for(type_or_kind)
        if (value := badge_value(f.code)) is not None
    }


def first_ordered_field(spec: WorkflowSpec) -> Field | None:
    """The first declared field — scanned across every non-roster type in declaration order
    (``ItemSpec.order``, type name), not just one arbitrary type — whose bound collection is
    ``ordered`` (squads' own "priority" axis is the bundled example, but this is generic over
    whatever axis a project's spec marks ordered).

    Generated prose that wants to teach "the ordered axis" (e.g. the squads skill's
    ``--priority`` line) must not probe a single hardcoded type for it: dropping that one
    type would silently delete the axis from the prose even though every other type still
    declares the identical field. Scanning every type instead means the axis survives as
    long as *any* surviving type carries it.

    Returns ``None`` when no non-roster type declares an ordered-collection field at all.
    """
    for item_type in sorted(spec.non_roster_types(), key=lambda t: (spec.items[t].order, t)):
        for f in spec.fields_for(item_type):
            coll = spec.collections.get(f.collection)
            if coll is not None and coll.ordered:
                return f
    return None


def status_badge(status_value: str, spec: WorkflowSpec | None = None) -> str:
    """``"InProgress"`` → ``"🟡 In Progress"`` (emoji + spaced label) for the header.

    The badge is resolved from the spec's declared ``StatusSpec.badge`` (built-in or custom); a
    status that declares none — including any custom status the bundled/default spec doesn't know
    about — falls back to the neutral :data:`_DEFAULT_BADGE` rather than crashing. ``spec``
    defaults to the bundled spec for call sites that don't thread one (e.g. the frozen migration
    runner, which only ever ran against the bundled vocabulary of its era).
    """
    label = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", status_value)
    active_spec = spec if spec is not None else bundled_spec()
    emoji = active_spec.status_badge(status_value) or _DEFAULT_BADGE
    return f"{emoji} {label}".strip()


def primary_field_code(
    kind: str, spec: WorkflowSpec | None = None, *, default: str = "severity"
) -> str:
    """The first field a sub-entity *kind* (or item type) declares — the axis an item template
    shows beside its sub-entity container (e.g. review's finding severity legend/example).

    Templates must not hardcode which field code that is (``'severity'``): a spec that relabels
    or replaces the kind's field (e.g. ``finding`` → ``impact``) still has SOME declared field,
    and this is it. Falls back to *default* only when the kind declares no field at all — the
    same graceful posture as :func:`field_label`/:func:`field_default`, so a spec that dropped
    the field entirely still renders something rather than crashing the template.
    """
    active_spec = spec if spec is not None else bundled_spec()
    fields = active_spec.fields_for(kind)
    return fields[0].code if fields else default


def declared_collection(
    type_or_kind: str, field_code: str, spec: WorkflowSpec | None = None
) -> str | None:
    """The collection code *type_or_kind* binds *field_code* to, or ``None`` when it declares
    no such field — the **strict** resolver, with no same-name fallback.

    This is the one to call when the answer decides whether a surface is *offered* or a value
    is *accepted*. :func:`resolve_collection`'s fallback exists for rendering a value that is
    already stored, and using it for a decision instead advertises a flag that can only ever
    error: a type declaring only ``urgency`` "resolves" ``priority`` to the same-named bundled
    collection, so the CLI offers ``--priority urgent|high|medium|low`` on a type whose own
    service gate refuses every one of those codes.
    """
    active_spec = spec if spec is not None else bundled_spec()
    field = next((f for f in active_spec.fields_for(type_or_kind) if f.code == field_code), None)
    return field.collection if field else None


def field_badge_codes(field_code: str, spec: WorkflowSpec | None = None) -> list[str]:
    """Every badge code any declared non-roster type's binding of *field_code* accepts, in
    type-declaration order, de-duplicated.

    The vocabulary for a **cross-type** door — ``sq list``/``tree``'s ``--priority`` filter
    runs over every type at once, so no single type's bound collection is the right authority
    and the bundled ``priority`` collection is merely one of them. Returns ``[]`` when no
    declared type binds *field_code* at all.
    """
    active_spec = spec if spec is not None else bundled_spec()
    codes: list[str] = []
    for item_type in sorted(
        active_spec.non_roster_types(), key=lambda t: (active_spec.items[t].order, t)
    ):
        coll_code = declared_collection(item_type, field_code, active_spec)
        coll = active_spec.collections.get(coll_code) if coll_code else None
        if coll is None:
            continue
        codes.extend(b.code for b in coll.badges if b.code not in codes)
    return codes


def resolve_collection(type_or_kind: str, field_code: str, spec: WorkflowSpec | None = None) -> str:
    """The collection code a declared field is bound to (``fields_for(type_or_kind)``).

    Falls back to *field_code* itself when the field isn't declared (graceful — e.g. a
    dropped/renamed field, or a frozen migration-era call with no live field to resolve) so
    the bundled ``priority``/``severity`` fields (whose code equals their collection code)
    keep working with no spec in hand.

    **Rendering only.** The fallback makes an already-stored value keep rendering after its
    field is dropped or renamed; it must never decide whether a flag is advertised or a value
    is valid, because a same-named collection then answers for a field the type does not
    declare. Use :func:`declared_collection` for any of those decisions.
    """
    return declared_collection(type_or_kind, field_code, spec) or field_code


def field_label(kind: str, field_code: str, spec: WorkflowSpec | None = None) -> str:
    """The declared ``Field.label`` for *field_code* on *kind* (item type or sub-entity kind).

    Falls back to the title-cased code when the field isn't declared — same graceful posture
    as :func:`resolve_collection`, so a template can relabel an axis (e.g. severity->impact)
    with no code change, and degrades sanely rather than crashing on a dropped field.
    """
    active_spec = spec if spec is not None else bundled_spec()
    field = next((f for f in active_spec.fields_for(kind) if f.code == field_code), None)
    return field.label if field else field_code.title()


def field_default(kind: str, field_code: str, spec: WorkflowSpec | None = None) -> str | None:
    """A valid example/fallback value for *field_code* on *kind*.

    The field's own ``default``, else its bound collection's ``default``, else the collection's
    first badge. Mirrors ``Service.field_default`` (the add-<kind> CLI's own omitted-flag
    fallback) so a template hint shows the same value the CLI would actually apply. Falls back
    to resolving *field_code* directly as a collection code when the field itself isn't
    declared (mirrors :func:`resolve_collection`'s fallback), so a dropped/renamed field with a
    same-named collection still yields a usable example.
    """
    active_spec = spec if spec is not None else bundled_spec()
    field = next((f for f in active_spec.fields_for(kind) if f.code == field_code), None)
    if field and field.default:
        return field.default
    coll = active_spec.collections.get(field.collection if field else field_code)
    if coll is None:
        return None
    if coll.default:
        return coll.default
    return coll.badges[0].code if coll.badges else None


def collection_legend(collection_code: str, spec: WorkflowSpec | None = None) -> str:
    """A ``" · "``-joined ``emoji code`` readout for every badge in *collection_code* — the
    review findings legend / any other flat-scale readout. Empty string if the collection is
    undeclared."""
    active_spec = spec if spec is not None else bundled_spec()
    coll = active_spec.collections.get(collection_code)
    if not coll:
        return ""
    return " · ".join(f"{b.emoji or _DEFAULT_BADGE} {b.code}" for b in coll.badges)


def badge_parts(
    collection_code: str, code: str, spec: WorkflowSpec | None = None
) -> tuple[str, str, str]:
    """``(emoji, code, label)`` for one declared badge in *collection_code* — the decomposed
    form behind :func:`badge_render`, for a caller that needs the parts separately (e.g. a
    JSON payload carrying structured badge metadata) rather than one rendered string. A
    missing collection/badge degrades to :data:`_DEFAULT_BADGE` + the raw/title-cased code,
    same graceful fallback as :func:`badge_render`.
    """
    active_spec = spec if spec is not None else bundled_spec()
    coll = active_spec.collections.get(collection_code)
    badge = next((b for b in coll.badges if b.code == code), None) if coll else None
    emoji = (badge.emoji if badge and badge.emoji else None) or _DEFAULT_BADGE
    label = badge.label if badge else code.title()
    return emoji, code, label


def badge_render(
    collection_code: str, code: str, spec: WorkflowSpec | None = None, *, as_label: bool = False
) -> str:
    """One generic badge renderer for every flat presentation axis (priority/severity/…).

    ``as_label=False`` (the default) renders ``emoji + raw code`` — the list/panel/summary
    convention. ``as_label=True`` renders ``emoji + Title-case label`` — the head/pane-title
    convention. Resolves from *collection_code* in the given (or bundled, or active) spec via
    :func:`badge_parts`; a missing collection/badge degrades gracefully rather than crashing
    (mirrors :func:`status_badge`).
    """
    emoji, raw_code, label = badge_parts(collection_code, code, spec)
    text = label if as_label else raw_code
    return f"{emoji} {text}"
