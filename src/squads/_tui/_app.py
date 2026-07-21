"""The `sq ui` Textual application: item tree + reader panel (read-only)."""

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import BindingType
from textual.containers import Horizontal
from textual.widgets import Footer, Header, Tree

from squads._services._service import Service
from squads._tui._reader import ReaderPanel
from squads._tui._tree import populate_tree


class SquadsApp(App[None]):
    """Browse a squad: keyboard-navigable item tree, reader panel on selection."""

    TITLE = "sq ui"
    BINDINGS: ClassVar[list[BindingType]] = [("q", "quit", "Quit")]

    def __init__(self, svc: Service) -> None:
        super().__init__()
        self._svc = svc
        self._tree: Tree[str] = Tree[str]("squad", id="item-tree")
        self._reader = ReaderPanel(svc, id="reader-panel")

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield self._tree
            yield self._reader
        yield Footer()

    async def on_mount(self) -> None:
        nodes = await self._svc.tree_view()
        populate_tree(self._tree, nodes)
        self._tree.focus()

    async def on_tree_node_highlighted(self, event: Tree.NodeHighlighted[str]) -> None:
        item_id = event.node.data
        if item_id is None:
            return
        await self._reader.load(item_id)
