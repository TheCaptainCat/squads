"""The memory reader panel: one role/operator's memory entry — not shaped like an item.

A memory has no sub-entities and no discussion, so the three-tab `ReaderPanel` (`_reader.py`)
is the wrong shape for it: a lightweight header (slug, created-at, tags) over a single
markdown body, peer in spirit to `ReaderPanel` but its own widget.
"""

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.content import Content
from textual.widgets import Markdown, Static

from squads._memory._model import MemoryEntry
from squads._services._service import Service


def _glance_line(entry: MemoryEntry) -> Content:
    # Static renders through Textual's own Content markup, which does not honor Rich's `\[`
    # escaping — the summary/tags are free-form and may contain brackets, so they go in as
    # template variables rather than being concatenated into the markup string.
    if entry.tags:
        template = "[bold]$slug[/bold]  ·  $created  ·  tags: $tags"
        return Content.from_markup(
            template,
            slug=entry.slug,
            created=entry.created_at,
            tags=", ".join(entry.tags),
        )
    template = "[bold]$slug[/bold]  ·  $created"
    return Content.from_markup(template, slug=entry.slug, created=entry.created_at)


class MemoryReaderPanel(Vertical):
    """Header + markdown body for one memory entry, loaded by role slug + entry slug."""

    DEFAULT_CSS = """
    MemoryReaderPanel #memory-body-scroll {
        height: 1fr;
    }
    """

    def __init__(self, svc: Service, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._svc = svc

    def compose(self) -> ComposeResult:
        yield Static(id="memory-glance-header")
        with VerticalScroll(id="memory-body-scroll"):
            yield Markdown(id="memory-body-view")

    async def load(self, role_slug: str, entry_slug: str) -> None:
        entry = await self._svc.memory_show(role_slug, entry_slug)
        self.query_one("#memory-glance-header", Static).update(_glance_line(entry))
        await self.query_one("#memory-body-view", Markdown).update(
            entry.body.strip() or "*(no body yet)*"
        )
