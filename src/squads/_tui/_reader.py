"""The reader panel: at-a-glance header + body/sub-entities/discussion tabs."""

from rich.markup import escape as e
from rich.table import Table
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Markdown, Static, TabbedContent, TabPane

from squads import _badges as badges
from squads import _discussion as discussion
from squads._models._item import Item
from squads._services._service import Service
from squads._workflow import WorkflowSpec

_EMPTY = "[dim](none)[/dim]"


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
                yield Static(id="subentities-view")
            with TabPane("Discussion", id="tab-discussion"), VerticalScroll(id="disc-scroll"):
                yield Static(id="discussion-view")

    async def load(self, item_id: str) -> None:
        svc = self._svc
        item = await svc.get(item_id)
        body = await svc.read_body(item_id)
        discussion_region = await svc.read_discussion(item_id)

        self.query_one("#glance-header", Static).update(_glance_line(item, svc.spec))
        await self.query_one("#body-view", Markdown).update(body.strip() or "*(no body yet)*")
        self.query_one("#subentities-view", Static).update(_subentities_view(item, svc.spec))
        comments = discussion.split_discussion(discussion_region)
        self.query_one("#discussion-view", Static).update(_discussion_view(comments))


def _glance_line(item: Item, spec: WorkflowSpec) -> str:
    parts = [badges.status_badge(item.status, spec)]
    priority = item.badge_value("priority")
    if priority:
        coll = badges.resolve_collection(item.type, "priority", spec)
        parts.append(badges.badge_render(coll, priority, spec, as_label=True))
    parts.append(e(item.assignee) if item.assignee else "[dim]unassigned[/dim]")
    return "  ·  ".join(parts)


def _subentities_view(item: Item, spec: WorkflowSpec) -> str | Table:
    kind = spec.item_subentity_kind(item.type)
    if kind is None or not item.subentities:
        return _EMPTY
    table = Table(box=None, pad_edge=False)
    for col in discussion.summary_columns(kind, spec):
        table.add_column(col)
    for sub in item.subentities:
        table.add_row(*(e(c) for c in discussion.summary_row(kind, sub, spec)))
    return table


def _discussion_view(comments: list[discussion.Comment]) -> str:
    if not comments:
        return _EMPTY
    blocks = [
        f"[bold]{e(c.timestamp)}[/bold] [dim]{e(c.author)}[/dim]\n{e(c.body)}" for c in comments
    ]
    return "\n\n".join(blocks)
