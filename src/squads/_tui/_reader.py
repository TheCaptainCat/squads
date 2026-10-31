"""The reader panel and its standalone screen: reading one item is one concern."""

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Vertical, VerticalScroll
from textual.content import Content
from textual.screen import Screen
from textual.widgets import Footer, Header, Markdown, Static, TabbedContent, TabPane

from squads._api import _ops as ops
from squads._api._dto._display import Display
from squads._api._dto._items import Comment, ItemShow, ItemShowRequest, Subentity
from squads._tui._session import Session

_EMPTY = "*(none)*"


class ReaderPanel(Vertical):
    # TabbedContent/TabPane default to height:auto, so a tab's content only ever grows to fit
    # itself instead of filling the panel — its VerticalScroll child then never scrolls either.
    DEFAULT_CSS = """
    ReaderPanel TabbedContent {
        height: 1fr;
    }
    ReaderPanel TabPane {
        height: 1fr;
    }
    """

    def __init__(self, session: Session, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._session = session

    def compose(self) -> ComposeResult:
        yield Static(id="glance-header")
        with TabbedContent(id="reader-tabs"):
            with TabPane("Body", id="tab-body"), VerticalScroll(id="body-scroll"):
                yield Markdown(id="body-view")
            with TabPane("Sub-entities", id="tab-subentities"), VerticalScroll(id="sub-scroll"):
                yield Markdown(id="subentities-view")
            with TabPane("Discussion", id="tab-discussion"), VerticalScroll(id="disc-scroll"):
                yield Markdown(id="discussion-view")

    async def load(self, item_id: str) -> None:
        item = (await self._session.call(ops.ITEM_SHOW, ItemShowRequest(id=item_id))).data
        self.query_one("#glance-header", Static).update(_glance_line(item))
        body = item.display.body.strip() or "*(no body yet)*"
        await self.query_one("#body-view", Markdown).update(body)
        await self.query_one("#subentities-view", Markdown).update(_subentities_view(item))
        await self.query_one("#discussion-view", Markdown).update(_discussion_view(item.discussion))


class ReaderScreen(Screen[None]):
    """A standalone item reader, reusing `ReaderPanel` — pushed wherever an item must be
    opened outside the browse tree (e.g. a search hit)."""

    BINDINGS: ClassVar[list[BindingType]] = [("escape", "close", "Back")]

    def __init__(self, session: Session, item_id: str) -> None:
        super().__init__()
        self._item_id = item_id
        self._panel = ReaderPanel(session, id="reader-panel")

    def compose(self) -> ComposeResult:
        yield Header()
        yield self._panel
        yield Footer()

    async def on_mount(self) -> None:
        await self._panel.load(self._item_id)

    def action_close(self) -> None:
        self.dismiss()


def _badge_parts(display: Display) -> list[str]:
    """The status badge, then each badge field holding a value, by its label, in declared
    order."""
    return [display.status.badge, *(b.badge_label for b in display.badges.values())]


def _glance_line(item: ItemShow) -> Content:
    """The item header: status, one badge per field carrying a value, then the assignee."""
    # Static renders through Textual's own Content markup, which does not honor Rich's `\[`
    # escaping — so the assignee (free-form, may contain brackets) goes in as a template
    # variable rather than being concatenated into the markup string.
    parts = _badge_parts(item.display)
    if item.assignee:
        template = "  ·  ".join([*parts, "$assignee"])
        return Content.from_markup(template, assignee=item.assignee)
    template = "  ·  ".join([*parts, "[dim]unassigned[/dim]"])
    return Content.from_markup(template)


def _subentity_head_line(sub: Subentity) -> str:
    parts = _badge_parts(sub.display)
    if sub.assignee:
        parts.append(sub.assignee)
    if sub.display.maps_to:
        parts.append(sub.display.maps_to)
    return "  ·  ".join(parts)


def _subentities_view(item: ItemShow) -> str:
    """Each sub-entity as its own block — head line (badges) plus its rendered body — not
    just a summary table, so the prose is actually visible without leaving the tab."""
    subs = [sub for sub in item.subentities if isinstance(sub, Subentity)]
    if not subs:
        return _EMPTY
    blocks: list[str] = []
    for sub in subs:
        body = sub.body.strip() or "*(no body yet)*"
        blocks.append(f"### {sub.local_id} — {sub.title}\n\n{_subentity_head_line(sub)}\n\n{body}")
    return "\n\n---\n\n".join(blocks)


def _author_label(comment: Comment) -> str:
    """The author as a person reads it: ``Name (slug)``, or the slug once when the name is it."""
    if comment.author == comment.author_slug:
        return comment.author
    return f"{comment.author} ({comment.author_slug})"


def _discussion_view(comments: list[Comment]) -> str:
    if not comments:
        return _EMPTY
    blocks = [
        f"`{c.short_hash}` **{c.ts}** _{_author_label(c)}_"
        + (f" (edited {c.edited_ts})" if c.edited_ts else "")
        + f"\n\n{c.body}"
        for c in comments
    ]
    return "\n\n---\n\n".join(blocks)
