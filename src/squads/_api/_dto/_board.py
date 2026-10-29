"""The board DTOs: a listing of the current notices, a posted notice and a cleared one."""

from squads._api._dto._base import DTO


class BoardListRequest(DTO):
    """List the notices that have not expired."""


class NoticeRow(DTO):
    """A notice as the listing numbers it: ``n`` is its position, which ``board clear`` takes."""

    n: int
    id: str
    author: str
    posted_at: str
    until: str | None
    body: str


class NoticeList(DTO):
    """The current notices, oldest first."""

    items: list[NoticeRow]


class BoardPostRequest(DTO):
    """Post *body* as the request's actor, hidden after *until* when given."""

    body: str
    until: str | None = None


class BoardClearRequest(DTO):
    """Take down the notice at position *n* of the current listing."""

    n: int


class Notice(DTO):
    """A notice: its id, author, times and text."""

    id: str
    author: str
    posted_at: str
    until: str | None
    body: str


class NoticeWrite(DTO):
    """What a board write answers: the notice posted, or the notice as it was when taken down."""

    entry: Notice
