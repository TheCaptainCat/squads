"""Items projected onto their DTOs, with the display content the spec and the roster decide."""

from collections.abc import Callable, Mapping, Sequence
from typing import cast

from squads import _badges as badges
from squads import _discussion as discussion
from squads import _pronouns
from squads._api._dto._display import AttributeDisplay, BadgeDisplay, Column, Display, StatusDisplay
from squads._api._dto._items import (
    Comment,
    ItemRow,
    ItemShowDisplay,
    Subentity,
    SubentityDisplay,
    SubentitySummary,
)
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._models._subentity import SubEntity
from squads._models._vocab import label_for
from squads._services._results import SubentityDetail
from squads._workflow import ROSTER_OPERATOR, ROSTER_ROLE
from squads._workflow._models import WorkflowSpec

#: The columns of the ``list`` table, each keyed by the path to the value its cell shows. The
#: priority column is the dedicated ``--priority`` field's badge.
LIST_COLUMNS: tuple[Column, ...] = (
    Column(key="id", header="ID"),
    Column(key="type", header="Type"),
    Column(key="status", header="Status"),
    Column(key="display.badges.priority.badge", header="Priority"),
    Column(key="title", header="Title"),
    Column(key="parent", header="Parent"),
    Column(key="assignee", header="Assignee"),
)


def participant_names(db: SquadsDB, pronouns: Mapping[str, str | None]) -> dict[str, str]:
    """Each role's and operator's name, by slug, followed by the pronouns *pronouns* gives it."""
    return {
        it.slug: _pronouns.named(it.title, pronouns.get(it.slug), enabled=True).plain
        for it in db.items.values()
        if it.type in (ROSTER_ROLE, ROSTER_OPERATOR)
    }


def status_display(status: str, spec: WorkflowSpec) -> StatusDisplay:
    """*status*'s badge and its role's colour intent."""
    return StatusDisplay(
        badge=badges.status_badge(status, spec), intent=spec.role_for(status).color
    )


def badge_displays(
    spec: WorkflowSpec, type_or_kind: str, badge_value: Callable[[str], str | None]
) -> dict[str, BadgeDisplay]:
    """Each declared badge field that holds a value, by field code in declared order."""
    shown: dict[str, BadgeDisplay] = {}
    for field in spec.fields_for(type_or_kind):
        value = badge_value(field.code)
        if value:
            shown[field.code] = BadgeDisplay(
                label=field.label,
                badge=badges.badge_render(field.collection, value, spec),
                badge_label=badges.badge_render(field.collection, value, spec, as_label=True),
            )
    return shown


def item_display(item: Item, spec: WorkflowSpec, names: Mapping[str, str]) -> Display:
    """How *item* is shown in a listing."""
    return Display(
        type=label_for(item.type, "singular", spec),
        status=status_display(item.status, spec),
        badges=badge_displays(spec, item.type, item.badge_value),
        assignee=names.get(item.assignee) if item.assignee else None,
    )


def item_row(item: Item, spec: WorkflowSpec, names: Mapping[str, str]) -> ItemRow:
    """*item* as a listing row."""
    return ItemRow.model_validate(
        {
            **item.to_row(),
            "badges": badges.resolve_badges(spec, item.type, item.badge_value),
            "display": item_display(item, spec, names),
        }
    )


def comment_dtos(comments: Sequence[discussion.Comment]) -> list[Comment]:
    """A discussion's entries, each with its hash shown at the scope's length."""
    return [Comment.model_validate(entry) for entry in discussion.comments_json(comments)]


def subentity_display(
    kind: str,
    sub: SubEntity,
    carrier_title: str | None,
    spec: WorkflowSpec,
    names: Mapping[str, str],
) -> SubentityDisplay:
    """How a sub-entity of *kind* is shown; *carrier_title* is the title of the item that
    carries its deferred work."""
    kind_spec = spec.subentity_kinds.get(kind)
    return SubentityDisplay(
        type=kind.title(),
        status=status_display(sub.status, spec),
        badges=badge_displays(spec, kind, sub.badge_value),
        assignee=names.get(sub.assignee) if sub.assignee else None,
        story=sub.story if kind_spec is not None and kind_spec.maps_to_parent else None,
        carrier_title=carrier_title,
    )


def subentity_dto(
    kind: str, detail: SubentityDetail, spec: WorkflowSpec, names: Mapping[str, str]
) -> Subentity:
    """A sub-entity of *kind* in full, from its detail."""
    info = detail.info
    return Subentity.model_validate(
        {
            **info.model_dump(mode="json"),
            "body": detail.body,
            "badges": badges.resolve_badges(spec, kind, info.badge_value),
            "discussion": comment_dtos(detail.comments),
            "display": subentity_display(kind, info, detail.carrier_title, spec, names),
        }
    )


def attribute_text(value: object) -> str:
    """A stored attribute value as display text: a date or a string as stored, a list joined
    with ", ", a boolean as "yes" or "no"."""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, list):
        return ", ".join(str(v) for v in cast(list[object], value))
    return str(value)


def show_display(
    item: Item, kind: str | None, body: str, spec: WorkflowSpec, names: Mapping[str, str]
) -> ItemShowDisplay:
    """How *item* is shown by ``show``: its listing display, its *body* with view tags expanded,
    its sub-entity summary and each labelled attribute it holds a value for."""
    summary = None
    if kind is not None and item.subentities:
        summary = SubentitySummary(
            kind=kind,
            columns=discussion.summary_columns(kind, spec),
            rows=[discussion.summary_row(kind, sub, spec) for sub in item.subentities],
        )
    row = item.to_row()
    attributes = [
        AttributeDisplay(key=name, label=declared.label, value=attribute_text(row[name]))
        for name, declared in spec.item_attributes(item.type).items()
        if declared.label is not None and row.get(name) is not None
    ]
    return ItemShowDisplay(
        **dict(item_display(item, spec, names)),
        body=body,
        summary=summary,
        attributes=attributes,
    )


def sort_by_badge(items: list[Item], sort: str | None, spec: WorkflowSpec) -> list[Item]:
    """*items* stable-sorted by a badge field's rank when *sort* names one."""
    if sort is None:
        return items
    return sorted(
        items, key=lambda it: badges.badge_rank(it.type, sort, it.badge_value(sort), spec)
    )
