"""The browse screen: item tree + reader panel, the base of the `sq ui` screen stack."""

from dataclasses import dataclass, field, replace
from typing import ClassVar, Literal

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Footer, Header, Static, Tree

from squads._models._item import Item
from squads._services._base import ItemFilter
from squads._services._results import TreeNode
from squads._services._service import Service
from squads._tui._filter import FilterScreen
from squads._tui._reader import ReaderPanel
from squads._tui._search import SearchScreen
from squads._tui._tree import populate_tree


@dataclass(frozen=True)
class SortKey:
    """A presentation-only sibling-sort choice; `badge_code` is set only for `kind="badge"`."""

    kind: Literal["sequence", "status", "title", "updated", "badge"] = "sequence"
    badge_code: str | None = None


@dataclass(frozen=True)
class BrowseState:
    """The active filter/sort view state — owned by `BrowseScreen`, edited by `FilterScreen`."""

    filter: ItemFilter = field(default_factory=ItemFilter)
    include_closed: bool = False
    sort: SortKey = field(default_factory=SortKey)

    def is_default(self) -> bool:
        return self.filter.is_empty() and not self.include_closed and self.sort == SortKey()


def _sort_key_value(item: Item, sort: SortKey) -> tuple[int, str]:
    """A comparable, always-`tuple[int, str]` key so one `sorted()` call never mixes types."""
    if sort.kind == "status":
        return (0, item.status)
    if sort.kind == "title":
        return (0, item.title.lower())
    if sort.kind == "updated":
        return (0, item.updated_at.isoformat())
    value = item.badge_value(sort.badge_code) if sort.badge_code else None
    return (1, "") if value is None else (0, value)


def sort_siblings(nodes: list[TreeNode], sort: SortKey) -> list[TreeNode]:
    """Reorder siblings at every level of *nodes* per *sort* — presentation-only:
    recurses into children, never reorders across levels, and never calls the service."""
    reordered = [replace(n, children=sort_siblings(n.children, sort)) for n in nodes]
    if sort.kind == "sequence":
        return reordered
    return sorted(reordered, key=lambda n: _sort_key_value(n.item, sort))


class BrowseScreen(Screen[None]):
    """Item tree + reader panel: the base screen of the `sq ui` stack."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("f", "open_filter", "Filter"),
        ("/", "open_search", "Search"),
    ]

    def __init__(self, svc: Service) -> None:
        super().__init__()
        self._svc = svc
        self.state = BrowseState()
        self._tree: Tree[str] = Tree[str]("squad", id="item-tree")
        self._reader = ReaderPanel(svc, id="reader-panel")
        self._indicator = Static(id="filter-indicator")

    def compose(self) -> ComposeResult:
        yield Header()
        yield self._indicator
        with Horizontal():
            yield self._tree
            yield self._reader
        yield Footer()

    async def on_mount(self) -> None:
        await self.refresh_tree()
        self._tree.focus()

    async def refresh_tree(self) -> None:
        """Re-run `tree_view()` under the active filter/closed toggle, reorder siblings per the
        active sort, and repopulate the tree."""
        nodes = await self._svc.tree_view(
            filter=self.state.filter, include_closed=self.state.include_closed
        )
        nodes = sort_siblings(nodes, self.state.sort)
        self._tree.reset("squad")
        populate_tree(self._tree, nodes, self._svc.spec)
        self._update_indicator()

    def _update_indicator(self) -> None:
        self._indicator.update("" if self.state.is_default() else "[reverse] FILTERED [/reverse]")

    async def on_tree_node_highlighted(self, event: Tree.NodeHighlighted[str]) -> None:
        item_id = event.node.data
        if item_id is None:
            return
        await self._reader.load(item_id)

    def action_open_filter(self) -> None:
        self.app.push_screen(  # pyright: ignore[reportUnknownMemberType]
            FilterScreen(self.state, self._svc.spec), self._apply_filter
        )

    async def _apply_filter(self, result: BrowseState | None) -> None:
        if result is None:
            return
        self.state = result
        await self.refresh_tree()

    def action_open_search(self) -> None:
        self.app.push_screen(SearchScreen(self._svc))  # pyright: ignore[reportUnknownMemberType]
