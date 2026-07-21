"""The reader panel and its standalone screen: reading one item is one concern."""

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Vertical, VerticalScroll
from textual.content import Content
from textual.screen import Screen
from textual.widgets import Footer, Header, Markdown, Static, TabbedContent, TabPane

from squads import _badges as badges
from squads import _discussion as discussion
from squads._models._item import Item
from squads._models._subentity import SubEntity
from squads._services._service import Service
from squads._workflow import WorkflowSpec

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

    def __init__(self, svc: Service, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._svc = svc

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
        svc = self._svc
        item = await svc.get(item_id)
        body = await svc.read_body(item_id)
        discussion_region = await svc.read_discussion(item_id)

        self.query_one("#glance-header", Static).update(_glance_line(item, svc.spec))
        await self.query_one("#body-view", Markdown).update(body.strip() or "*(no body yet)*")
        subentities_md = await _subentities_view(svc, item, svc.spec)
        await self.query_one("#subentities-view", Markdown).update(subentities_md)
        comments = discussion.split_discussion(discussion_region)
        await self.query_one("#discussion-view", Markdown).update(_discussion_view(comments))


class ReaderScreen(Screen[None]):
    """A standalone item reader, reusing `ReaderPanel` — pushed wherever an item must be
    opened outside the browse tree (e.g. a search hit)."""

    BINDINGS: ClassVar[list[BindingType]] = [("escape", "close", "Back")]

    def __init__(self, svc: Service, item_id: str) -> None:
        super().__init__()
        self._item_id = item_id
        self._panel = ReaderPanel(svc, id="reader-panel")

    def compose(self) -> ComposeResult:
        yield Header()
        yield self._panel
        yield Footer()

    async def on_mount(self) -> None:
        await self._panel.load(self._item_id)

    def action_close(self) -> None:
        self.dismiss()


def _glance_line(item: Item, spec: WorkflowSpec) -> Content:
    # Static renders through Textual's own Content markup, which does not honor Rich's `\[`
    # escaping — so the assignee (free-form, may contain brackets) goes in as a template
    # variable rather than being concatenated into the markup string.
    parts = [badges.status_badge(item.status, spec)]
    priority = item.badge_value("priority")
    if priority:
        coll = badges.resolve_collection(item.type, "priority", spec)
        parts.append(badges.badge_render(coll, priority, spec, as_label=True))
    if item.assignee:
        template = "  ·  ".join([*parts, "$assignee"])
        return Content.from_markup(template, assignee=item.assignee)
    template = "  ·  ".join([*parts, "[dim]unassigned[/dim]"])
    return Content.from_markup(template)


def _subentity_head_line(sub: SubEntity, kind: str, spec: WorkflowSpec) -> str:
    parts = [badges.status_badge(sub.status, spec)]
    for field in spec.fields_for(kind):
        value = sub.badge_value(field.code)
        if value:
            coll = badges.resolve_collection(kind, field.code, spec)
            parts.append(badges.badge_render(coll, value, spec, as_label=True))
    if sub.assignee:
        parts.append(sub.assignee)
    kind_spec = spec.subentity_kinds.get(kind)
    if kind_spec is not None and kind_spec.maps_parent_story and sub.story:
        parts.append(sub.story)
    return "  ·  ".join(parts)


async def _subentities_view(svc: Service, item: Item, spec: WorkflowSpec) -> str:
    """Each sub-entity as its own block — head line (badges) plus its rendered body — not
    just a summary table, so the prose is actually visible without leaving the tab."""
    kind = spec.item_subentity_kind(item.type)
    if kind is None or not item.subentities:
        return _EMPTY
    blocks: list[str] = []
    for sub in item.subentities:
        detail = await svc.get_block(item.id, kind, sub.local_id)
        head = _subentity_head_line(sub, kind, spec)
        body = detail.body.strip() or "*(no body yet)*"
        blocks.append(f"### {sub.local_id} — {sub.title}\n\n{head}\n\n{body}")
    return "\n\n---\n\n".join(blocks)


def _discussion_view(comments: list[discussion.Comment]) -> str:
    if not comments:
        return _EMPTY
    blocks = [f"**{c.timestamp}** _{c.author}_\n\n{c.body}" for c in comments]
    return "\n\n---\n\n".join(blocks)
