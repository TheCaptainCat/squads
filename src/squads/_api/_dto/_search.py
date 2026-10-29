"""The search DTOs: the query and the items it matched, each with its matching lines."""

from squads._api._dto._base import DTO
from squads._api._dto._display import Display


class SearchRequest(DTO):
    """The items whose title, summary, body or discussion contains *q*, ignoring case; *type*
    and *status* narrow the search."""

    q: str
    type: str | None = None
    status: str | None = None


class SearchMatch(DTO):
    """One matching line: where it is (``region`` for a program, ``location`` for a reader), the
    text around the match, and the full hash of the comment it is in, when it is in one."""

    region: str
    location: str
    snippet: str
    hash: str | None


class SearchHit(DTO):
    """An item that matched, with every matching line."""

    id: str
    title: str
    type: str
    status: str
    hits: list[SearchMatch]
    display: Display


class SearchResults(DTO):
    """The items that matched."""

    items: list[SearchHit]
