"""The item DTOs: the addressed and listing requests, an item's row, its full show, and a
listing."""

from typing import Any, ClassVar

from pydantic import ConfigDict, Field, JsonValue, SerializerFunctionWrapHandler, model_serializer

from squads._api._dto._base import DTO
from squads._api._dto._display import AttributeDisplay, Column, Display


class ItemAddress(DTO):
    """An item as a client names it: its id, alone enough to address it; the type a command
    expects, refused when the item has another; and the address as typed, which messages
    quote."""

    id: str
    type: str | None = None
    address: str | None = None


class ItemShowRequest(ItemAddress):
    """Show one item."""


class ItemStatusRequest(ItemAddress):
    """Move one item to *status*; *force* makes a transition its lifecycle does not allow."""

    status: str
    force: bool = False


class ItemListRequest(DTO):
    """List items: every filter given must match. ``badge`` and ``min_badge`` hold
    ``CODE=VALUE`` pairs; ``all`` keeps closed items."""

    type: str | None = None
    status: str | None = None
    parent: str | None = None
    label: str | None = None
    assignee: str | None = None
    category: str | None = None
    badge: list[str] = Field(default_factory=list[str])
    min_badge: list[str] = Field(default_factory=list[str])
    sort: str | None = None
    all: bool = False


class Comment(DTO):
    """One discussion entry."""

    author: str
    author_slug: str
    ts: str
    edited_ts: str | None
    hash: str
    short_hash: str
    body: str


class SubentityDisplay(Display):
    """How a sub-entity is shown: the mapped story when its kind shows one, and the title of
    the item that carries its deferred work."""

    story: str | None
    carrier_title: str | None


class SubentityRow(DTO):
    """A sub-entity's stored state."""

    local_id: str
    title: str
    status: str
    assignee: str | None
    severity: str | None
    story: str | None
    deferred_to: str | None
    extra: dict[str, JsonValue]


class Subentity(SubentityRow):
    """A sub-entity with its body, badges, discussion and display."""

    body: str
    badges: dict[str, str]
    discussion: list[Comment]
    display: SubentityDisplay


class SubentitySummary(DTO):
    """The sub-entity summary table of an item: the kind, its headers and one row of cells per
    sub-entity."""

    kind: str
    columns: list[str]
    rows: list[list[str]]


class ItemShowDisplay(Display):
    """How a shown item is displayed: its display plus its body with view tags expanded, its
    sub-entity summary, and each labelled attribute it holds a value for, in declared order."""

    body: str
    summary: SubentitySummary | None
    attributes: list[AttributeDisplay]


class _TrailingKeys(DTO):
    """Serializes the keys a command adds after the item's stored attributes."""

    TRAILING: ClassVar[tuple[str, ...]] = ()

    @model_serializer(mode="wrap")
    def _ordered(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        dumped: dict[str, Any] = handler(self)
        ordered = {k: v for k, v in dumped.items() if k not in self.TRAILING}
        ordered.update((k, dumped[k]) for k in self.TRAILING if k in dumped)
        return ordered


class ItemFields(_TrailingKeys):
    """An item's fields, with each stored attribute flat at the top level; a row adds its own
    keys after them."""

    model_config = ConfigDict(extra="allow")

    sequence_id: int
    type: str
    title: str
    slug: str
    status: str
    description: str
    parent: str | None
    author: str | None
    assignee: str | None
    priority: str | None
    severity: str | None
    labels: list[str]
    refs: list[str]
    subentities: list[SubentityRow]
    path: str
    created_at: str
    updated_at: str
    created_session: str | None
    modified_session: str | None
    id: str


class ItemRow(ItemFields):
    """An item as a listing row: its fields, each stored attribute flat at the top level, its
    badges by field code and its display."""

    TRAILING: ClassVar[tuple[str, ...]] = ("badges", "display")

    badges: dict[str, str]
    display: Display


class ItemShow(ItemRow):
    """An item as ``show`` prints it: its row with every sub-entity in full (in its stored form
    when the type hosts no sub-entity kind), the stored body, each view's data and the
    discussion."""

    TRAILING: ClassVar[tuple[str, ...]] = (
        "body",
        "views",
        "discussion",
        "badges",
        "display",
    )

    subentities: list[Subentity | SubentityRow]  # pyright: ignore[reportIncompatibleVariableOverride]
    body: str
    views: dict[str, JsonValue]
    discussion: list[Comment]
    display: ItemShowDisplay  # pyright: ignore[reportIncompatibleVariableOverride]


class ItemList(DTO):
    """A listing: its rows, the columns a table shows, and how many closed items it hid."""

    items: list[ItemRow]
    columns: list[Column]
    hidden: int
