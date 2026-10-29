"""The sub-entity read DTOs: an item's sub-entities as a listing, and one sub-entity shown."""

from typing import ClassVar

from squads._api._dto._base import DTO
from squads._api._dto._items import (
    ItemAddress,
    Subentity,
    SubentityDisplay,
    SubentityRow,
    SubentitySummary,
)


class SubentitiesRequest(ItemAddress):
    """The item's sub-entities; *kind*, when given, is the kind the caller expects the item's
    type to host, refused when it hosts another."""

    kind: str | None = None


class SubentityRequest(SubentitiesRequest):
    """One sub-entity of the item, by its local id."""

    local: str


class KindDisplay(DTO):
    """How a sub-entity kind is named: its code, its label, its plural and the heading above its
    container in the item's body."""

    name: str
    label: str
    plural: str
    heading: str


class SubentityEntry(SubentityRow):
    """A sub-entity as a listing row: its stored state and its display."""

    TRAILING: ClassVar[tuple[str, ...]] = ("display",)

    display: SubentityDisplay


class SubentityList(DTO):
    """The item's sub-entities, their summary table and their kind."""

    items: list[SubentityEntry]
    summary: SubentitySummary
    kind: KindDisplay


class SubentityShowDisplay(SubentityDisplay):
    """How a shown sub-entity is displayed: its display plus its kind, the kind its mapping
    targets, and its stored discussion text when that holds no comment the discussion list can
    carry."""

    kind: KindDisplay
    maps_to_kind: str | None
    discussion: str | None


class SubentityShow(Subentity):
    """A sub-entity as ``show`` prints it."""

    display: SubentityShowDisplay  # pyright: ignore[reportIncompatibleVariableOverride]
