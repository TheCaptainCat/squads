"""The workflow DTOs: the cheatsheet, one catalog per vocabulary map of the active spec, a view
resolved against an item, and the override lint.

A catalog lists one row per declared entry, every key present on every row, with the columns
its table shows."""

from typing import ClassVar

from squads._api._dto._base import DTO
from squads._api._dto._display import Column
from squads._api._dto._items import ItemShow
from squads._api._dto._roles import RoleShow
from squads._api._dto._subentities import SubentityEntry
from squads._api._dto._tree import TreeNode


class CatalogRequest(DTO):
    """Read one catalog of the active workflow spec."""


class FieldEntry(DTO):
    """A badge field a type or sub-entity kind declares: its code, label and collection."""

    code: str
    label: str
    collection: str


class AttributeEntry(DTO):
    """An attribute a type declares: its kind, whether it is required or settable, and the
    label a shown item gives it (``None`` when it is not shown)."""

    kind: str
    required: bool
    settable: bool
    label: str | None


class TypeRow(DTO):
    """A declared type."""

    type: str
    order: float | None
    prefix: str
    reserved: bool
    category: str
    subentity_kind: str | None
    lifecycle: str
    fields: list[FieldEntry]
    attributes: dict[str, AttributeEntry]
    labels: dict[str, str]


class TypeCatalog(DTO):
    """Every declared type, by ascending order then name."""

    items: list[TypeRow]
    columns: list[Column]


class SubentityKindRow(DTO):
    """A declared sub-entity kind."""

    subentity_kind: str
    label: str
    lifecycle: str
    plural: str
    local_prefix: str
    container_heading: str
    completion: str
    maps_to_parent: bool
    fields: list[FieldEntry]


class SubentityKindCatalog(DTO):
    """Every declared sub-entity kind, by name."""

    items: list[SubentityKindRow]
    columns: list[Column]


class LifecycleRow(DTO):
    """A declared lifecycle: its initial status, its statuses and its transitions, each a
    ``{from, to}`` object."""

    lifecycle: str
    initial: str
    states: list[str]
    transitions: list[dict[str, str]]


class LifecycleCatalog(DTO):
    """Every declared lifecycle, by name."""

    items: list[LifecycleRow]
    columns: list[Column]


class CollectionBadge(DTO):
    """A badge of a collection: its code, label and emoji."""

    code: str
    label: str
    emoji: str | None


class CollectionRow(DTO):
    """A declared badge collection."""

    collection: str
    label: str
    ordered: bool
    default: str | None
    badges: list[CollectionBadge]


class CollectionCatalog(DTO):
    """Every declared badge collection, by code."""

    items: list[CollectionRow]
    columns: list[Column]


class StatusRowDisplay(DTO):
    """How a status is shown in the catalog: the colour intent of its role."""

    intent: str


class StatusRow(DTO):
    """A declared status, its resolved role and its badge."""

    status: str
    role: str
    badge: str | None
    display: StatusRowDisplay


class StatusCatalog(DTO):
    """Every declared status, by name."""

    items: list[StatusRow]
    columns: list[Column]


class StatusRoleRow(DTO):
    """A declared status role."""

    role: str
    settled: bool
    hidden: bool
    color: str
    live: bool
    blocked: bool
    deferred: bool


class StatusRoleCatalog(DTO):
    """Every declared status role, by name."""

    items: list[StatusRoleRow]
    columns: list[Column]


class RefKindRow(DTO):
    """A declared ref kind."""

    kind: str
    label: str
    hint: str
    role: str | None
    direction: str | None


class RefKindCatalog(DTO):
    """Every declared ref kind, by name."""

    items: list[RefKindRow]
    columns: list[Column]


class ViewRow(DTO):
    """A declared view: its source and its transform, when it declares one."""

    view: str
    source_kind: str
    source_name: str | None
    transform: dict[str, str] | None


class ViewCatalog(DTO):
    """Every declared view, by name."""

    items: list[ViewRow]
    columns: list[Column]


class CheatsheetRequest(DTO):
    """Render the team workflow cheatsheet."""


class Cheatsheet(DTO):
    """The team workflow cheatsheet, as markdown."""

    markdown: str


class ViewResolveRequest(DTO):
    """Resolve the declared view *name* against the item *item*: its source, or, with *render*,
    its output rendered through the view's template instead."""

    name: str
    item: str
    render: bool = False


class SpecIdentity(DTO):
    """The workflow spec that resolved a view: the schema version, whether a project override
    was merged into it, and the SHA-256 of the merged spec, compared for equality only."""

    schema_version: str
    override: bool
    digest: str


class ItemShowWithSpec(ItemShow):
    """An item as ``show`` prints it, with the identity of the spec that resolved it."""

    TRAILING: ClassVar[tuple[str, ...]] = (
        "body",
        "views",
        "discussion",
        "badges",
        "spec",
        "display",
        "etag",
    )

    spec: SpecIdentity


class PlaybookLaneRole(DTO):
    """One role's guidance in a playbook lane."""

    slug: str
    enter: list[str]
    do: list[str]
    handoff: list[str]
    watch: list[str]
    authors: bool


class PlaybookLane(DTO):
    """A type's playbook lane: its overview, lifecycle note, commands and role guidance."""

    overview: str
    lifecycle: str
    commands: list[str]
    roles: list[PlaybookLaneRole]


class PlaybookRosterEntry(DTO):
    """A live role as a playbook source lists it."""

    slug: str
    full_name: str
    title: str
    is_default: bool
    mission: str
    responsibilities: list[str]
    capabilities: list[str]


class PlaybookView(DTO):
    """A playbook source: the type, its lane (``None`` outside every lane) and the live roster."""

    type: str
    lane: PlaybookLane | None
    roster: list[PlaybookRosterEntry]


type ViewSource = list[TreeNode] | list[SubentityEntry] | RoleShow | ItemShowWithSpec | PlaybookView


class ViewResult(DTO):
    """A view resolved against an item: its source in the shape of the command it comes from
    (``sq tree --json`` nodes, a sub-entity listing's rows, ``sq role show --json``, ``sq show
    --json`` plus the spec, or a playbook lane), or the output its template renders."""

    source: (
        list[TreeNode] | list[SubentityEntry] | RoleShow | ItemShowWithSpec | PlaybookView | None
    )
    output: str | None


class LintRequest(DTO):
    """Check the squad's workflow override."""


class LintFinding(DTO):
    """One problem with the override: where it is, what it is and how to fix it."""

    location: str
    message: str
    fix_hint: str


class LintReport(DTO):
    """Whether the squad has a workflow override, and the errors and warnings found in it."""

    override: bool
    errors: list[LintFinding]
    warnings: list[LintFinding]
