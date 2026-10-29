"""The work-queue DTOs: a participant's inbox and assigned items, the blocked items, and each
assignee's workload."""

from typing import ClassVar

from squads._api._dto._base import DTO
from squads._api._dto._display import Column, Display
from squads._api._dto._items import ItemFields


class QueueDisplay(Display):
    """How a queued item is shown: its display plus its stored status, which the row itself does
    not carry."""

    status_code: str


class InboxRequest(DTO):
    """The open items whose discussion mentions *slug*."""

    slug: str


class InboxEntry(DTO):
    """An item that mentions the slug: each mentioning line, the sub-entity region it is in
    (``None`` at item level) and the full hash of the comment it is in, by position."""

    id: str
    title: str
    lines: list[str]
    regions: list[str | None]
    hashes: list[str | None]
    display: QueueDisplay


class Inbox(DTO):
    """The slug as the roster spells it, and the items that mention it."""

    slug: str
    items: list[InboxEntry]


class MineRequest(DTO):
    """The items assigned to *slug*, directly or through a sub-entity; ``all`` keeps closed
    ones."""

    slug: str
    all: bool = False


class MatchedSubentity(DTO):
    """A sub-entity of the row's item assigned to the slug."""

    local_id: str
    kind: str | None
    title: str
    status: str


class MineDisplay(Display):
    """How an assigned item is shown: its display plus the sub-entities that make it the slug's,
    as one cell."""

    matched: str


class MineRow(ItemFields):
    """An assigned item as a listing row: its fields and stored attributes, then the sub-entities
    assigned to the slug and its display."""

    TRAILING: ClassVar[tuple[str, ...]] = ("matched_subentities", "display")

    matched_subentities: list[MatchedSubentity]
    display: MineDisplay


class Mine(DTO):
    """The slug as the roster spells it, its rows, and the columns a table shows."""

    slug: str
    items: list[MineRow]
    columns: list[Column]


class BlockedRequest(DTO):
    """The open items that wait on another open item."""


class Blocker(DTO):
    """An open item another one waits on."""

    id: str
    title: str
    status: str


class BlockedEntry(DTO):
    """A waiting item and what it waits on."""

    id: str
    title: str
    blockers: list[Blocker]
    display: QueueDisplay


class Blocked(DTO):
    """The waiting items."""

    items: list[BlockedEntry]


class WorkloadRequest(DTO):
    """Each assignee's open and closed work."""


class WorkloadDisplay(DTO):
    """How a workload row is shown: the assignee, or a word for the unassigned."""

    assignee: str


class WorkloadEntry(DTO):
    """One assignee's counts (``None`` is the unassigned work): items, then sub-entities,
    counted apart."""

    assignee: str | None
    open: int
    closed: int
    total: int
    subentity_open: int
    subentity_closed: int
    subentity_total: int
    display: WorkloadDisplay


class Workload(DTO):
    """The rows, busiest first, and the columns a table shows."""

    items: list[WorkloadEntry]
    columns: list[Column]
