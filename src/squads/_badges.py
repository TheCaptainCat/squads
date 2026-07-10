"""Badge/status-badge presentation helpers: resolve a spec-declared badge to emoji + label.

Pure presentation over the workflow spec's declared collections/fields — no discussion or
sub-entity concerns live here (see :mod:`squads._discussion` for that).
"""

import re

from squads._workflow import WorkflowSpec, bundled_spec

#: Neutral fallback badge for a status/collection that declares none — never crash.
_DEFAULT_BADGE = "⚪"


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


def resolve_collection(type_or_kind: str, field_code: str, spec: WorkflowSpec | None = None) -> str:
    """The collection code a declared field is bound to (``fields_for(type_or_kind)``).

    Falls back to *field_code* itself when the field isn't declared (graceful — e.g. a
    dropped/renamed field, or a frozen migration-era call with no live field to resolve) so
    the bundled ``priority``/``severity`` fields (whose code equals their collection code)
    keep working with no spec in hand.
    """
    active_spec = spec if spec is not None else bundled_spec()
    field = next((f for f in active_spec.fields_for(type_or_kind) if f.code == field_code), None)
    return field.collection if field else field_code


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


def badge_render(
    collection_code: str, code: str, spec: WorkflowSpec | None = None, *, as_label: bool = False
) -> str:
    """One generic badge renderer for every flat presentation axis (priority/severity/…).

    ``as_label=False`` (the default) renders ``emoji + raw code`` — the list/panel/summary
    convention. ``as_label=True`` renders ``emoji + Title-case label`` — the head/pane-title
    convention. Resolves from *collection_code* in the given (or bundled, or active) spec;
    a missing collection/badge degrades to :data:`_DEFAULT_BADGE` + the raw/title-cased code
    rather than crashing (graceful, mirrors :func:`status_badge`).
    """
    active_spec = spec if spec is not None else bundled_spec()
    coll = active_spec.collections.get(collection_code)
    badge = next((b for b in coll.badges if b.code == code), None) if coll else None
    emoji = (badge.emoji if badge and badge.emoji else None) or _DEFAULT_BADGE
    text = (badge.label if badge else code.title()) if as_label else code
    return f"{emoji} {text}"
