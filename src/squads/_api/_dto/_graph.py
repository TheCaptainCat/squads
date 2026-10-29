"""The ref graph DTOs: the request and the root node, whose children are the items a ref
reaches."""

from pydantic import Field

from squads._api._dto._base import DTO
from squads._api._dto._display import Display


class GraphRequest(DTO):
    """The items linked to *root* by refs, *depth* hops out, following only the ref kinds in
    ``kind`` when it names any, in *direction* ``out``, ``in`` or ``both``; ``all`` keeps closed
    items."""

    root: str
    depth: int = 2
    kind: list[str] = Field(default_factory=list[str])
    direction: str = "both"
    all: bool = False


class GraphNodeDisplay(Display):
    """How a graph node is shown: its display plus the text its edge is drawn with, and the
    declared label of the ref kind that reached it."""

    edge: str | None
    edge_label: str | None


class GraphNode(DTO):
    """One item of the graph and the ref that reached it; ``seen`` marks an item already shown,
    which is not expanded again."""

    id: str
    type: str
    status: str
    priority: str | None
    badges: dict[str, str]
    assignee: str | None
    edge_kind: str | None
    edge_semantic: str | None
    direction: str | None
    seen: bool
    children: list[GraphNode]
    display: GraphNodeDisplay
