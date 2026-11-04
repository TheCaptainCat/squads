"""The operator DTOs: an operator's row, show and listing, and the requests and reports of the
operator verbs."""

from pydantic import Field

from squads._api._dto._base import DTO
from squads._api._dto._display import Column
from squads._api._dto._items import Comment
from squads._api._dto._roster import NameDisplay, RosterAddress, SeveredRef


class OperatorRow(DTO):
    """A registered person: their fields, status, display and tracker user IDs by source name."""

    id: str
    slug: str
    full_name: str
    pronouns: str | None
    status: str
    display: NameDisplay
    identities: dict[str, str]


class OperatorWrite(DTO):
    """A write that reports nothing beside the operator it wrote: the operator after the
    write, or as it was for a removal."""

    entry: OperatorRow


class OperatorListRequest(DTO):
    """The registered people."""


class OperatorList(DTO):
    """The registered people and the columns their table shows."""

    items: list[OperatorRow]
    columns: list[Column]


class OperatorShowDisplay(NameDisplay):
    """How an operator's show is displayed beyond their fields: their body with view tags
    expanded, and their discussion."""

    body: str
    discussion: list[Comment]


class OperatorShow(DTO):
    """A registered person with their file and display."""

    id: str
    slug: str
    full_name: str
    pronouns: str | None
    status: str
    path: str
    display: OperatorShowDisplay
    identities: dict[str, str]


class OperatorAddRequest(DTO):
    """Register *name*, under *slug* when given."""

    name: str
    slug: str | None = None
    pronouns: str | None = None


class OperatorUpdateRequest(RosterAddress):
    """Rename an operator, set their pronouns (a blank value clears them) or set and remove the
    keys of their map attributes (a value sets, ``None`` removes)."""

    title: str | None = None
    pronouns: str | None = None
    map_attributes: dict[str, dict[str, str | None]] = Field(
        default_factory=dict[str, dict[str, str | None]]
    )


class OperatorStatusMove(DTO):
    """The operator after a status move, and the refs a retirement removed."""

    entry: OperatorRow
    severed: list[SeveredRef]
