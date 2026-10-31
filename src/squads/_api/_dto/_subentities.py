"""The sub-entity read DTOs: an item's sub-entities as a listing, and one sub-entity shown."""

from squads._api._dto._base import DTO
from squads._api._dto._items import (
    ItemAddress,
    KindDisplay,
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


class SubentityEntry(SubentityRow):
    """A sub-entity as a listing row: its stored state and its display."""

    display: SubentityDisplay


class SubentityList(DTO):
    """The item's sub-entities, their summary table and their kind."""

    items: list[SubentityEntry]
    summary: SubentitySummary
    kind: KindDisplay
    maps_to_kind: KindDisplay | None


class SubentityShowDisplay(SubentityDisplay):
    """How a shown sub-entity is displayed: its display plus its kind, and its stored discussion
    text when that holds no comment the discussion list can carry."""

    kind: KindDisplay
    discussion: str | None


class SubentityShow(Subentity):
    """A sub-entity as ``show`` prints it."""

    display: SubentityShowDisplay  # pyright: ignore[reportIncompatibleVariableOverride]
