"""The comment DTOs of every discussion host: adding a comment, and showing, editing, previewing
the removal of and removing one by its hash, on an item, a sub-entity or a roster entry.

A roster host is named by its address alone; the roster kind is the operation's."""

from pydantic import Field

from squads._api._dto._base import DTO
from squads._api._dto._items import Comment, ItemAddress
from squads._api._dto._roster import RosterAddress
from squads._api._dto._subentities import SubentityRequest


class _Text(DTO):
    """A comment's points, one per ``-m``, or one file's text."""

    texts: list[str] = Field(default_factory=list[str])


class _Hash(DTO):
    """A comment addressed by 4 or more leading hex characters of its hash, or the full hash."""

    hash: str


class CommentAddRequest(ItemAddress, _Text):
    """Add a comment to the item's discussion, written by the declared actor."""


class SubentityCommentAddRequest(SubentityRequest, _Text):
    """Add a comment to the sub-entity's discussion, written by the declared actor."""


class RosterCommentAddRequest(RosterAddress, _Text):
    """Add a comment to the roster entry's discussion, written by the declared actor."""


class CommentRequest(ItemAddress, _Hash):
    """One comment of the item's discussion."""


class SubentityCommentRequest(SubentityRequest, _Hash):
    """One comment of the sub-entity's discussion."""


class RosterCommentRequest(RosterAddress, _Hash):
    """One comment of the roster entry's discussion."""


class CommentEditRequest(CommentRequest, _Text):
    """Replace the text of one comment of the item's discussion, as its author."""


class SubentityCommentEditRequest(SubentityCommentRequest, _Text):
    """Replace the text of one comment of the sub-entity's discussion, as its author."""


class RosterCommentEditRequest(RosterCommentRequest, _Text):
    """Replace the text of one comment of the roster entry's discussion, as its author."""


class CommentShown(Comment):
    """A comment with the item whose discussion holds it, its scope (``<kind>:<local id>`` for a
    sub-entity's discussion, else ``None``) and how many copies of it the discussion holds."""

    item: str
    scope: str | None
    copies: int


class CommentAdded(DTO):
    """The comment a write added."""

    entry: CommentShown


class CommentEdited(Comment):
    """The comment as now stored, with its item and scope, whether anything was written and the
    comment as it was."""

    item: str
    scope: str | None
    changed: bool
    previous: Comment


class CommentSelection(DTO):
    """The comments one hash addresses, every copy of a comment written twice, with the item and
    scope that hold them; each carries the full hash a removal sends."""

    items: list[Comment]
    item: str
    scope: str | None
