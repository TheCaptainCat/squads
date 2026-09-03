"""Derived views: resolve a declared ``[views]`` entry's source, project it into the one
uniform record shape every source and presentation shares, and render it.

A view has three parts and no fourth: **source** (what to project — refs of a declared kind
pointing at the item, a sub-entity collection, or a subtree, resolved by
:func:`resolve_records`), **projection** (which fields, how grouped, how ordered — produced by
:func:`project`, never a presentation decision), and **presentation** (a Jinja2 template over
the projected records, resolved by :func:`render_view` at ``templates/views/<name>.md.j2`` —
the view's own declared name, never a separate stored field). Every view is computed on
request; nothing here ever writes into an item body.

``--json`` callers use :func:`projection_json` directly and skip :func:`render_view` entirely
— the projection is the contract, presentation is one consumer of it.

Cost is one already-loaded index plus an inversion/walk over it — the same shape ``sq tree``
and ``sq blocked`` have always had; nothing here caches a projection or stores one on an item.
"""

from collections.abc import Callable
from dataclasses import dataclass

from squads._badges import badge_parts, resolve_collection
from squads._errors import SquadsError
from squads._models._index import SquadsDB
from squads._models._item import Item, effective_prefix, ref_id_matches, split_ref
from squads._models._subentity import SubEntity
from squads._paths import number_for_id
from squads._rendering._engine import render
from squads._workflow._models import VIEW_BASE_FIELDS_BY_SOURCE, ViewSpec, WorkflowSpec

JsonValue = str | bool | dict[str, str] | None


@dataclass(frozen=True)
class Cell:
    """One resolved field value on one record: a presentation-ready ``text`` (what every
    template needs, regardless of the field's type — a badge already carries its emoji), and a
    structured ``json_value`` for the ``--json`` contract (a plain scalar for a text field, a
    ``{code, label, emoji}`` object for a badge field, ``None`` for an absent value)."""

    text: str
    json_value: JsonValue


@dataclass(frozen=True)
class ViewFieldMeta:
    """One projected column's metadata — travels with the payload so a client can render an
    unfamiliar view without special-casing it."""

    code: str
    label: str
    type: str  # "text" | "badge"


@dataclass(frozen=True)
class ViewRecord:
    values: dict[str, Cell]


@dataclass(frozen=True)
class ViewGroup:
    """One group of records. ``key`` is ``None`` for an ungrouped view's single implicit
    group — the top-level shape stays ``groups`` either way, so a client never special-cases
    "this view happens to be ungrouped"."""

    key: JsonValue
    records: list[ViewRecord]


@dataclass(frozen=True)
class Projection:
    fields: list[ViewFieldMeta]
    group_by: str | None
    groups: list[ViewGroup]

    def records(self) -> list[ViewRecord]:
        return [r for g in self.groups for r in g.records]


@dataclass(frozen=True)
class _RawRecord:
    """A source record normalised to one shape before field projection — an ``Item`` or a
    ``SubEntity``, whichever the source produced. ``kind`` is the record's own item type (a
    ref/subtree source) or the declared sub-entity kind it was resolved under (a subentity
    source) — the namespace :func:`squads._badges.resolve_collection` looks a badge field up
    in. ``story``/``type`` sit outside every base-attribute set their source kind doesn't
    allow (:data:`~squads._workflow._models.VIEW_BASE_FIELDS_BY_SOURCE`), so a field
    resolution never reads them there."""

    identity: str
    kind: str
    status: str
    assignee: str | None
    title: str
    story: str | None
    badge_value: Callable[[str], str | None]


def _record_from_item(it: Item) -> _RawRecord:
    return _RawRecord(
        identity=it.id,
        kind=it.type,
        status=it.status,
        assignee=it.assignee,
        title=it.title,
        story=None,
        badge_value=it.badge_value,
    )


def _record_from_subentity(sub: SubEntity, kind: str) -> _RawRecord:
    return _RawRecord(
        identity=sub.local_id,
        kind=kind,
        status=sub.status,
        assignee=sub.assignee,
        title=sub.title,
        story=sub.story,
        badge_value=sub.badge_value,
    )


# --------------------------------------------------------------------------- source resolution


def _resolve_subentity_source(
    view: ViewSpec, view_name: str, item: Item, spec: WorkflowSpec
) -> list[_RawRecord]:
    kind = view.source.name
    hosted = spec.item_subentity_kind(item.type)
    if hosted != kind:
        hosted_desc = repr(hosted) if hosted else "none"
        raise SquadsError(
            f"view {view_name!r} projects {kind!r} sub-entities, but {item.id} is a "
            f"{item.type!r} item, which hosts {hosted_desc}"
        )
    return [_record_from_subentity(s, kind) for s in item.subentities]


def _resolve_ref_source(
    view: ViewSpec, item: Item, db: SquadsDB, spec: WorkflowSpec
) -> list[_RawRecord]:
    """Refs of the declared kind pointing at *item*, recovered by inverting stored forward
    edges — the same shape ``squads._services._refs.RefsMixin.refs_in`` computes, inlined here
    so it shares the one index load the caller already made rather than loading a second
    time."""
    target_kind = view.source.name
    default_kind = spec.default_ref_kind()
    target_prefix = effective_prefix(item.prefix)
    target_seq = item.sequence_id
    records: list[_RawRecord] = []
    for it in sorted(db.items.values(), key=lambda i: number_for_id(i.id)):
        for r in it.refs:
            rid, kind = split_ref(r)
            if (kind or default_kind) == target_kind and ref_id_matches(
                rid, target_prefix, target_seq
            ):
                records.append(_record_from_item(it))
                break
    return records


def _children_by_parent(db: SquadsDB) -> dict[str, list[Item]]:
    """Canonical-parent → children, width-tolerant (mirrors
    ``squads._services._base._build_tree_children``'s resolution, reimplemented rather than
    imported: ``_services`` sits above this module in the layering, so the edge runs one way
    only — a service may call into ``squads._views``, never the reverse)."""
    all_ids = {i.id for i in db.items.values()}
    seq_to_id = {number_for_id(i.id): i.id for i in db.items.values()}
    children: dict[str, list[Item]] = {}
    for it in db.items.values():
        if not it.parent:
            continue
        canonical = seq_to_id.get(number_for_id(it.parent))
        if canonical is not None and canonical in all_ids:
            children.setdefault(canonical, []).append(it)
    return children


def _resolve_subtree_source(view: ViewSpec, item: Item, db: SquadsDB) -> list[_RawRecord]:
    target_type = view.source.name
    children = _children_by_parent(db)
    seen = {item.id}
    stack = [item.id]
    matched: list[Item] = []
    while stack:
        current = stack.pop()
        for child in children.get(current, []):
            if child.id in seen:
                continue
            seen.add(child.id)
            stack.append(child.id)
            if child.type == target_type:
                matched.append(child)
    matched.sort(key=lambda i: number_for_id(i.id))
    return [_record_from_item(i) for i in matched]


def resolve_records(
    view: ViewSpec, view_name: str, item: Item, db: SquadsDB, spec: WorkflowSpec
) -> list[_RawRecord]:
    """Every raw record *view* projects when resolved against *item* — dispatches on the
    declared ``source.kind``; never named as a bare string here (it comes straight off the
    already-validated spec)."""
    if view.source.kind == "subentity":
        return _resolve_subentity_source(view, view_name, item, spec)
    if view.source.kind == "ref":
        return _resolve_ref_source(view, item, db, spec)
    return _resolve_subtree_source(view, item, db)


# --------------------------------------------------------------------------- field resolution

#: Base record attributes resolved directly off :class:`_RawRecord` / the active spec, never
#: off a declared badge field — the counterpart, at the resolving end, of
#: ``VIEW_BASE_FIELDS_BY_SOURCE`` at the declaring end. A code outside this set is resolved as
#: a badge field instead (already refused at load if it names neither).
_BASE_RESOLVERS: dict[str, Callable[[_RawRecord, WorkflowSpec], str | None]] = {
    "id": lambda r, _spec: r.identity,
    "type": lambda r, _spec: r.kind,
    "status": lambda r, _spec: r.status,
    "status_role": lambda r, spec: spec.status_role(r.status),
    "assignee": lambda r, _spec: r.assignee,
    "title": lambda r, _spec: r.title,
    "story": lambda r, _spec: r.story,
}


def _badge_cell(kind: str, code: str, raw: str, spec: WorkflowSpec) -> Cell:
    coll_code = resolve_collection(kind, code, spec)
    emoji, badge_code, label = badge_parts(coll_code, raw, spec)
    json_value = {"code": badge_code, "label": label, "emoji": emoji}
    return Cell(text=f"{emoji} {label}", json_value=json_value)


def _cell(rec: _RawRecord, code: str, spec: WorkflowSpec) -> Cell:
    base = _BASE_RESOLVERS.get(code)
    if base is not None:
        value = base(rec, spec)
        return Cell(text=value or "", json_value=value)
    raw = rec.badge_value(code)
    if raw is None:
        return Cell(text="", json_value=None)
    return _badge_cell(rec.kind, code, raw, spec)


def _sort_key(cell: Cell) -> tuple[int, str]:
    v = cell.json_value
    if v is None:
        return (0, "")
    if isinstance(v, dict):
        return (1, v.get("code", ""))
    return (1, str(v))


# --------------------------------------------------------------------------- projection


def project(view: ViewSpec, records: list[_RawRecord], spec: WorkflowSpec) -> Projection:
    """Records with typed fields, optionally grouped — identically shaped whichever source
    produced *records*. Makes no presentation decision: no template is touched
    here."""
    base_allowed = VIEW_BASE_FIELDS_BY_SOURCE[view.source.kind]
    field_meta = [
        ViewFieldMeta(
            code=f.code, label=f.label, type="text" if f.code in base_allowed else "badge"
        )
        for f in view.fields
    ]

    built: list[ViewRecord] = [
        ViewRecord(values={f.code: _cell(rec, f.code, spec) for f in view.fields})
        for rec in records
    ]

    if view.order_by:
        for code in reversed(view.order_by):
            built.sort(key=lambda r, c=code: _sort_key(r.values[c]))

    if view.group_by is None:
        groups = [ViewGroup(key=None, records=built)]
    else:
        buckets: dict[str, list[ViewRecord]] = {}
        bucket_key_repr: dict[str, JsonValue] = {}
        for rec in built:
            cell = rec.values[view.group_by]
            key_repr = "\0none" if cell.json_value is None else repr(cell.json_value)
            buckets.setdefault(key_repr, []).append(rec)
            bucket_key_repr[key_repr] = cell.json_value
        groups = [ViewGroup(key=bucket_key_repr[k], records=recs) for k, recs in buckets.items()]

    return Projection(fields=field_meta, group_by=view.group_by, groups=groups)


# --------------------------------------------------------------------------- output


def projection_json(projection: Projection) -> dict[str, object]:
    """The ``--json`` contract: field metadata + grouping + records, no presentation output."""
    return {
        "fields": [{"code": f.code, "label": f.label, "type": f.type} for f in projection.fields],
        "group_by": projection.group_by,
        "groups": [
            {
                "key": g.key,
                "count": len(g.records),
                "records": [
                    {code: cell.json_value for code, cell in rec.values.items()}
                    for rec in g.records
                ],
            }
            for g in projection.groups
        ],
    }


def render_view(view_name: str, projection: Projection) -> str:
    """Render *projection* through the presentation template declared at the view's own name —
    ``templates/views/<view_name>.md.j2``, resolved by the one Jinja2 engine every rendering
    path already uses. An adopter's ``.overrides/templates/views/<view_name>.md.j2`` shadows
    it exactly the way every other bundled template already does; no view-specific override
    code exists to do that."""
    return render(
        f"views/{view_name}.md.j2",
        fields=projection.fields,
        group_by=projection.group_by,
        groups=projection.groups,
    )
