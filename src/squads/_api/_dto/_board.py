"""The board DTOs: a listing of the current notices, a posted notice and a cleared one."""

from pydantic import Field

from squads._api._dto._base import DTO


def _absent(value: object) -> bool:
    return value is None


class BoardListRequest(DTO):
    """List the notices that have not expired; with *full*, each row carries its body."""

    full: bool = False


class NoticeRow(DTO):
    """A notice as the listing numbers it: ``n`` is its position, which ``board clear`` takes."""

    n: int
    id: str
    summary: str
    author: str
    author_name: str
    posted_at: str
    until: str | None
    #: The body, present only in a listing that asked for it in full.
    body: str | None = Field(default=None, exclude_if=_absent)


class NoticeDetail(DTO):
    """One notice in full: the listing row and its body, empty when the notice has none."""

    n: int
    id: str
    summary: str
    author: str
    author_name: str
    posted_at: str
    until: str | None
    body: str


class NoticeList(DTO):
    """The current notices, oldest first."""

    items: list[NoticeRow]


class BoardPostRequest(DTO):
    """Post *summary* over an optional *body* as the request's actor, hidden after *until*."""

    summary: str
    body: str | None = None
    until: str | None = None


class BoardShowRequest(DTO):
    """Read the notice at position *n* of the current listing."""

    n: int


class BoardClearRequest(DTO):
    """Take down the notice at position *n* of the current listing."""

    n: int


class Notice(DTO):
    """A notice: its id, summary, author, times and body."""

    id: str
    summary: str
    author: str
    author_name: str
    posted_at: str
    until: str | None
    body: str


class NoticeWrite(DTO):
    """What a board write answers: the notice posted, or the notice as it was when taken down."""

    entry: Notice
