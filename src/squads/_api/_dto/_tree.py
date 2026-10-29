"""The tree DTOs: the request, which takes the filters of ``sq tree``, and the hierarchy of
nodes it answers with."""

from pydantic import Field

from squads._api._dto._base import DTO
from squads._api._dto._display import Display


class TreeRequest(DTO):
    """The item hierarchy, under *root* when given: every filter given must match, ``badge`` and
    ``min_badge`` hold ``CODE=VALUE`` pairs, *sort* names a badge field each level is ranked by,
    and ``all`` keeps closed items."""

    root: str | None = None
    type: str | None = None
    status: str | None = None
    assignee: str | None = None
    category: str | None = None
    badge: list[str] = Field(default_factory=list[str])
    min_badge: list[str] = Field(default_factory=list[str])
    sort: str | None = None
    depth: int | None = None
    all: bool = False


class TreeNodeDisplay(Display):
    """How a tree node is shown: its display plus whether it is dimmed as an ancestor kept only
    for a match below it, the note beside a root invented for a parent cycle, and a role's or
    operator's pronouns when the squad shows them."""

    dimmed: bool
    anchor: str | None
    pronouns: str | None


class TreeNode(DTO):
    """One item of the hierarchy, with the items below it."""

    id: str
    type: str
    title: str
    status: str
    priority: str | None
    assignee: str | None
    blocked: bool
    badges: dict[str, str]
    anchor: bool
    children: list[TreeNode]
    display: TreeNodeDisplay


class TreeView(DTO):
    """The hierarchy's root nodes, and how many closed items the default filter hid."""

    items: list[TreeNode]
    hidden: int
