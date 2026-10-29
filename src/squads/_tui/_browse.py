"""The browse screen: item tree + reader panel, the base of the `sq ui` screen stack."""

from dataclasses import dataclass, field
from typing import ClassVar, Literal

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import ContentSwitcher, Footer, Header, Static, Tree

from squads._api import _ops as ops
from squads._api._dto._memory import MemoryListRequest, MemoryRow
from squads._api._dto._tree import TreeNode, TreeRequest
from squads._errors import SquadsError
from squads._tui._board import BoardScreen
from squads._tui._filter import FilterScreen
from squads._tui._memory_reader import MemoryReaderPanel
from squads._tui._reader import ReaderPanel
from squads._tui._search import SearchScreen
from squads._tui._session import Session
from squads._tui._tree import MemoryNodeData, NodeData, populate_tree, roster_identity_slugs


@dataclass(frozen=True)
class TreeFilter:
    """The filter fields of the `tree` operation the filter screen sets; `badges` holds
    (field code, badge code) pairs."""

    item_type: str | None = None
    status: str | None = None
    category: str | None = None
    assignee: str | None = None
    label: str | None = None
    badges: tuple[tuple[str, str], ...] = ()

    def is_empty(self) -> bool:
        return self == TreeFilter()


@dataclass(frozen=True)
class SortKey:
    """A presentation-only sibling-sort choice; `badge_code` is set only for `kind="badge"`."""

    kind: Literal["sequence", "status", "title", "updated", "badge"] = "sequence"
    badge_code: str | None = None


@dataclass(frozen=True)
class BrowseState:
    """The active filter/sort view state — owned by `BrowseScreen`, edited by `FilterScreen`."""

    filter: TreeFilter = field(default_factory=TreeFilter)
    include_closed: bool = False
    sort: SortKey = field(default_factory=SortKey)

    def is_default(self) -> bool:
        return self.filter.is_empty() and not self.include_closed and self.sort == SortKey()

    def tree_request(self) -> TreeRequest:
        f = self.filter
        return TreeRequest(
            type=f.item_type,
            status=f.status,
            assignee=f.assignee,
            category=f.category,
            label=f.label,
            badge=[f"{code}={value}" for code, value in f.badges],
            all=self.include_closed,
        )


def _sort_key_value(node: TreeNode, sort: SortKey) -> tuple[int, str]:
    """A comparable, always-`tuple[int, str]` key so one `sorted()` call never mixes types."""
    if sort.kind == "status":
        return (0, node.status)
    if sort.kind == "title":
        return (0, node.title.lower())
    if sort.kind == "updated":
        return (0, node.updated_at)
    value = node.badges.get(sort.badge_code) if sort.badge_code else None
    return (1, "") if value is None else (0, value)


def sort_siblings(nodes: list[TreeNode], sort: SortKey) -> list[TreeNode]:
    """Reorder siblings at every level of *nodes* per *sort* — presentation-only:
    recurses into children, never reorders across levels, and makes no call."""
    reordered = [n.model_copy(update={"children": sort_siblings(n.children, sort)}) for n in nodes]
    if sort.kind == "sequence":
        return reordered
    return sorted(reordered, key=lambda n: _sort_key_value(n, sort))


@dataclass(frozen=True)
class BrowseView:
    """What the tree shows: the sorted roots, and each notebook slug's memory entries with how
    many of its memory files could not be read."""

    nodes: list[TreeNode]
    memory: dict[str, tuple[list[MemoryRow], int]]


async def fetch_view(session: Session, state: BrowseState) -> BrowseView:
    """Run the `tree` operation under *state*'s filter and toggle, sort it, and list the memory
    of every role and operator it holds.

    Every visible Role/Operator's memory pool is fetched here, once per identity, not on node
    expansion: the view compares hygiene across the roster at a glance.
    """
    view = await session.call(ops.TREE, state.tree_request())
    nodes = sort_siblings(view.data.items, state.sort)
    memory: dict[str, tuple[list[MemoryRow], int]] = {}
    for slug in roster_identity_slugs(nodes):
        listed = await session.call(ops.MEMORY_LIST, MemoryListRequest(role=slug))
        memory[slug] = (listed.data.items, len(listed.omitted))
    return BrowseView(nodes, memory)


class BrowseScreen(Screen[None]):
    """Item tree + reader panel: the base screen of the `sq ui` stack."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("f", "open_filter", "Filter"),
        ("/", "open_search", "Search"),
        ("b", "open_board", "Board"),
    ]

    def __init__(self, session: Session, opening: BrowseView) -> None:
        super().__init__()
        self._session = session
        self._opening = opening
        self.state = BrowseState()
        self._tree: Tree[NodeData] = Tree[NodeData]("squad", id="item-tree")
        self._reader = ReaderPanel(session, id="reader-panel")
        self._memory_reader = MemoryReaderPanel(session, id="memory-reader-panel")
        self._indicator = Static(id="filter-indicator")

    def compose(self) -> ComposeResult:
        yield Header()
        yield self._indicator
        with Horizontal():
            yield self._tree
            with ContentSwitcher(initial="reader-panel", id="reader-switcher"):
                yield self._reader
                yield self._memory_reader
        yield Footer()

    async def on_mount(self) -> None:
        self._show(self._opening)
        self._tree.focus()

    async def refresh_tree(self) -> None:
        """Fetch the view under the active state and repopulate the tree."""
        self._show(await fetch_view(self._session, self.state))

    def _show(self, view: BrowseView) -> None:
        self._tree.reset("squad")
        populate_tree(self._tree, view.nodes, self._session.catalogs.types, view.memory)
        self._update_indicator()

    def _update_indicator(self) -> None:
        self._indicator.update("" if self.state.is_default() else "[reverse] FILTERED [/reverse]")

    async def on_tree_node_highlighted(self, event: Tree.NodeHighlighted[NodeData]) -> None:
        data = event.node.data
        if data is None:
            return
        switcher = self.query_one("#reader-switcher", ContentSwitcher)
        if isinstance(data, MemoryNodeData):
            switcher.current = "memory-reader-panel"
            await self._memory_reader.load(data.role_slug, data.entry_slug)
            return
        switcher.current = "reader-panel"
        await self._reader.load(data)

    def action_open_filter(self) -> None:
        self.app.push_screen(  # pyright: ignore[reportUnknownMemberType]
            FilterScreen(self.state, self._session.catalogs), self._apply_filter
        )

    async def _apply_filter(self, result: BrowseState | None) -> None:
        if result is None:
            return
        previous, self.state = self.state, result
        try:
            await self.refresh_tree()
        except SquadsError as exc:
            self.state = previous
            self.notify(str(exc), severity="error")

    def action_open_search(self) -> None:
        self.app.push_screen(SearchScreen(self._session))  # pyright: ignore[reportUnknownMemberType]

    def action_open_board(self) -> None:
        self.app.push_screen(BoardScreen(self._session))  # pyright: ignore[reportUnknownMemberType]
