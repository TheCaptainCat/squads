"""The full-text search screen: a query input over a results list of snippets."""

from typing import ClassVar

from textual import work
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Horizontal
from textual.content import Content
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, ListItem, ListView, Select, Static
from textual.widgets.select import NoSelection

from squads._services._results import SearchResult
from squads._services._service import Service
from squads._tui._reader import ReaderScreen

_PROMPT = "Type to search…"


def _render_hit(result: SearchResult) -> Content:
    # Static renders through Textual's own Content markup, which does not honor Rich's `\[`
    # escaping — ids/titles/snippets (all free-form, snippets especially bracket-heavy) go in
    # as template variables rather than being concatenated into the markup string.
    item = result.item
    content = Content.from_markup(
        "[bold]$id[/bold] [dim]($type)[/dim] $title", id=item.id, type=item.type, title=item.title
    )
    for hit in result.hits:
        line = Content.from_markup(
            "  [dim]$location:[/dim] $snippet", location=hit.location, snippet=hit.snippet
        )
        content = content + "\n" + line
    return content


def _selected(select: Select[str]) -> str | None:
    value = select.value
    return None if isinstance(value, NoSelection) else value


class _HitItem(ListItem):
    """A `ListItem` row that remembers which item it stands for."""

    def __init__(self, result: SearchResult) -> None:
        super().__init__(Static(_render_hit(result)))
        self.item_id = result.item.id


class SearchScreen(Screen[None]):
    """A dedicated search mode over the whole corpus — pushed over `BrowseScreen`, which it
    fully replaces (search is its own mode, not an overlay)."""

    BINDINGS: ClassVar[list[BindingType]] = [("escape", "close", "Back")]

    # The selects row (a Horizontal) defaults to height:1fr like every Horizontal, so it was
    # eating the space meant for the results list; pin it to its content and let the list fill.
    DEFAULT_CSS = """
    SearchScreen #search-filters {
        height: auto;
    }
    SearchScreen #search-results {
        height: 1fr;
    }
    """

    def __init__(self, svc: Service) -> None:
        super().__init__()
        self._svc = svc
        self._query = Input(placeholder=_PROMPT, id="search-query")
        self._type_select: Select[str] = Select(
            [(t, t) for t in sorted(svc.spec.work_types())], id="search-type"
        )
        self._status_select: Select[str] = Select(
            [(s, s) for s in sorted(svc.spec.statuses)], id="search-status-filter"
        )
        self._status = Static(_PROMPT, id="search-status")
        self._results: ListView = ListView(id="search-results")

    def compose(self) -> ComposeResult:
        yield Header()
        yield self._query
        with Horizontal(id="search-filters"):
            yield self._type_select
            yield self._status_select
        yield self._status
        yield self._results
        yield Footer()

    async def on_mount(self) -> None:
        self._query.focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        await self._search(event.value)

    async def on_select_changed(self, event: Select.Changed) -> None:
        if event.select is self._type_select or event.select is self._status_select:
            await self._search(self._query.value)

    async def _search(self, raw_text: str) -> None:
        text = raw_text.strip()
        if not text:
            self._results.loading = False
            await self._results.clear()
            self._status.update(_PROMPT)
            return
        self._status.update("Searching…")
        self._results.loading = True
        self._run_search(text, _selected(self._type_select), _selected(self._status_select))

    @work(exclusive=True)
    async def _run_search(self, text: str, item_type: str | None, status: str | None) -> None:
        results = await self._svc.search(text, item_type=item_type, status=status)
        await self._results.clear()
        self._results.loading = False
        if not results:
            self._status.update(Content.from_markup("No results for $query", query=repr(text)))
            return
        self._status.update("")
        await self._results.extend(_HitItem(r) for r in results)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, _HitItem):
            self.app.push_screen(  # pyright: ignore[reportUnknownMemberType]
                ReaderScreen(self._svc, event.item.item_id)
            )

    def action_close(self) -> None:
        self.dismiss()
