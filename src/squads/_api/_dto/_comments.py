"""The discussion DTOs: an item's top-level comments."""

from squads._api._dto._base import DTO
from squads._api._dto._items import Comment, ItemAddress


class CommentsRequest(ItemAddress):
    """The item's top-level discussion."""


class Comments(DTO):
    """The comments, oldest first."""

    items: list[Comment]
