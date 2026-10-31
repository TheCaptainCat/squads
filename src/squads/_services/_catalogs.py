"""The workflow catalogs: one DTO per vocabulary map of a spec, each row holding every key, and
the columns its table shows."""

import math

from squads._api._dto._display import Column, titled_columns
from squads._api._dto._workflow import (
    AttributeEntry,
    CollectionBadge,
    CollectionCatalog,
    CollectionRow,
    FieldEntry,
    LifecycleCatalog,
    LifecycleRow,
    RefKindCatalog,
    RefKindRow,
    StatusCatalog,
    StatusRoleCatalog,
    StatusRoleRow,
    StatusRow,
    StatusRowDisplay,
    SubentityKindCatalog,
    SubentityKindRow,
    TypeCatalog,
    TypeRow,
    ViewCatalog,
    ViewRow,
)
from squads._models._vocab import labels_for
from squads._workflow._lifecycle_order import lifecycle_edges_in_order, lifecycle_states_in_order
from squads._workflow._models import FALLBACK_ROLE_NAME, WorkflowSpec


def _columns(*pairs: tuple[str, str]) -> list[Column]:
    return [Column(key=key, header=header) for key, header in pairs]


def _fields(type_or_kind: str, spec: WorkflowSpec) -> list[FieldEntry]:
    """The badge fields an item type or a sub-entity kind declares."""
    return [
        FieldEntry(code=f.code, label=f.label, collection=f.collection)
        for f in spec.fields_for(type_or_kind)
    ]


def type_catalog(spec: WorkflowSpec) -> TypeCatalog:
    """Every declared type, roster ones included, by ascending order (unset last), then name."""
    types = sorted(spec.items, key=lambda t: (spec.items[t].order, t))
    rows = [
        TypeRow(
            type=t,
            order=None if math.isinf(spec.items[t].order) else spec.items[t].order,
            prefix=spec.items[t].prefix,
            reserved=spec.items[t].category == "roster",
            category=spec.items[t].category,
            subentity_kind=spec.items[t].subentity_kind,
            lifecycle=spec.items[t].lifecycle,
            fields=_fields(t, spec),
            attributes={
                name: AttributeEntry(
                    kind=a.kind, required=a.required, settable=a.settable, label=a.label
                )
                for name, a in spec.item_attributes(t).items()
            },
            labels=dict(labels_for(t, spec)),
        )
        for t in types
    ]
    columns = _columns(
        ("type", "Type"),
        ("order", "Order"),
        ("prefix", "Prefix"),
        ("reserved", "Reserved"),
        ("category", "Category"),
    )
    return TypeCatalog(items=rows, columns=columns)


def subentity_kind_catalog(spec: WorkflowSpec) -> SubentityKindCatalog:
    """Every declared sub-entity kind, by name, with the heading sq writes above its blocks."""
    rows = [
        SubentityKindRow(
            subentity_kind=kind,
            label=spec.kind_label(kind),
            lifecycle=ks.lifecycle,
            plural=ks.plural,
            local_prefix=ks.local_prefix,
            container_heading=spec.subentity_container_heading(kind),
            completion=ks.completion,
            maps_to_parent=ks.maps_to_parent,
            fields=_fields(kind, spec),
        )
        for kind, ks in sorted(spec.subentity_kinds.items())
    ]
    columns = _columns(
        ("subentity_kind", "Kind"),
        ("lifecycle", "Lifecycle"),
        ("plural", "Plural"),
        ("local_prefix", "Prefix"),
        ("container_heading", "Heading"),
        ("completion", "Completion"),
        ("fields", "Fields"),
    )
    return SubentityKindCatalog(items=rows, columns=columns)


def lifecycle_catalog(spec: WorkflowSpec) -> LifecycleCatalog:
    """Every declared lifecycle, by name: its statuses in discovery order from the initial one,
    and its transitions with sources in that order."""
    rows = [
        LifecycleRow(
            lifecycle=name,
            initial=machine.initial,
            states=lifecycle_states_in_order(machine),
            transitions=[
                {"from": src, "to": dst} for src, dst in lifecycle_edges_in_order(machine)
            ],
        )
        for name, machine in sorted(spec.lifecycles.items())
    ]
    columns = _columns(
        ("lifecycle", "Lifecycle"),
        ("initial", "Initial"),
        ("states", "States"),
        ("transitions", "Transitions"),
    )
    return LifecycleCatalog(items=rows, columns=columns)


def collection_catalog(spec: WorkflowSpec) -> CollectionCatalog:
    """Every declared badge collection, by code, with its badges."""
    rows = [
        CollectionRow(
            collection=code,
            label=coll.label,
            ordered=coll.ordered,
            default=coll.default,
            badges=[
                CollectionBadge(code=b.code, label=b.label, emoji=b.emoji) for b in coll.badges
            ],
        )
        for code, coll in sorted(spec.collections.items())
    ]
    columns = _columns(
        ("collection", "Collection"),
        ("label", "Label"),
        ("ordered", "Ordered"),
        ("default", "Default"),
        ("badges", "Badges"),
    )
    return CollectionCatalog(items=rows, columns=columns)


def status_catalog(spec: WorkflowSpec) -> StatusCatalog:
    """Every declared status, by name, with its resolved role (the fallback one when it names
    none) and the colour intent of that role."""
    rows = [
        StatusRow(
            status=name,
            role=st.role or FALLBACK_ROLE_NAME,
            badge=st.badge,
            display=StatusRowDisplay(intent=spec.role_for(name).color),
        )
        for name, st in sorted(spec.statuses.items())
    ]
    columns = _columns(("status", "Status"), ("role", "Role"), ("badge", "Badge"))
    return StatusCatalog(items=rows, columns=columns)


def role_catalog(spec: WorkflowSpec) -> StatusRoleCatalog:
    """Every declared status role, by name."""
    rows = [
        StatusRoleRow(
            role=name,
            settled=r.settled,
            hidden=r.hidden,
            color=r.color,
            live=r.live,
            blocked=r.blocked,
            deferred=r.deferred,
        )
        for name, r in sorted(spec.roles.items())
    ]
    columns = titled_columns("role", "settled", "hidden", "color", "live", "blocked", "deferred")
    return StatusRoleCatalog(items=rows, columns=columns)


def ref_kind_catalog(spec: WorkflowSpec) -> RefKindCatalog:
    """Every declared ref kind, by name: the set ``ref add --kind`` accepts."""
    rows = [
        RefKindRow(kind=code, label=rk.label, hint=rk.hint, role=rk.role, direction=rk.direction)
        for code, rk in sorted(spec.ref_kinds.items())
    ]
    columns = _columns(
        ("kind", "Kind"),
        ("label", "Label"),
        ("hint", "Hint"),
        ("role", "Role"),
        ("direction", "Direction"),
    )
    return RefKindCatalog(items=rows, columns=columns)


def view_catalog(spec: WorkflowSpec) -> ViewCatalog:
    """Every declared view, by name, with its source and its merged transform declaration."""
    rows = [
        ViewRow(
            view=name,
            source_kind=v.source.kind,
            source_name=v.source.name,
            transform=v.transform.model_dump(exclude_none=True) if v.transform else None,
        )
        for name, v in sorted(spec.views.items())
    ]
    columns = _columns(
        ("view", "View"), ("source_kind", "Source kind"), ("source_name", "Source name")
    )
    return ViewCatalog(items=rows, columns=columns)
