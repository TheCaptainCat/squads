"""The item renderers: an item's show, a listing of items and a status move."""

from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from squads._api._dto._items import ItemList, ItemRow, ItemShow, Subentity
from squads._api._dto._queues import MineRow
from squads._cli._render._comments import (
    author_label,
    comment_title,
    edited_suffix,
    is_styled,
    print_comments_plain,
    print_comments_styled,
)
from squads._cli._render._style import cell_text, e, print_body, status_text
from squads._models._item import split_ref

#: What an item with no body shows in its place.
_EMPTY_BODY = "(empty — set it with `body`)"


def _refs_line(refs: list[str]) -> str:
    return ", ".join(rid if not kind else f"{rid} ({kind})" for rid, kind in map(split_ref, refs))


def _panel_rows(show: ItemShow) -> list[str]:
    rows = [
        f"[bold]{show.id}[/bold]  ({show.type})",
        f"[bold]title:[/bold] {e(show.title)}",
        f"[bold]status:[/bold] {show.status}",
    ]
    rows += [f"[bold]{code}:[/bold] {e(b.badge)}" for code, b in show.display.badges.items()]
    rows += [f"[bold]{e(a.label)}:[/bold] {e(a.value)}" for a in show.display.attributes]
    if show.description:
        rows.append(f"[bold]summary:[/bold] {e(show.description)}")
    if show.parent:
        rows.append(f"[bold]parent:[/bold] {show.parent}")
    if show.author:
        author = f"[bold]author:[/bold] {e(show.author)}"
        if show.created_session:
            author += (
                f" [dim]@ {e(show.created_session)}[/dim]"
                " [dim](best-effort session, untrusted)[/dim]"
            )
        rows.append(author)
    if show.modified_session:
        rows.append(
            f"[bold]last-modified session:[/bold] [dim]{e(show.modified_session)}[/dim]"
            " [dim](best-effort, untrusted)[/dim]"
        )
    if show.assignee:
        rows.append(f"[bold]assignee:[/bold] {e(show.assignee)}")
    if show.labels:
        rows.append(f"[bold]labels:[/bold] {e(', '.join(show.labels))}")
    if show.refs:
        rows.append(f"[bold]refs:[/bold] {e(_refs_line(show.refs))}")
    rows.append(f"[bold]file:[/bold] {show.path}")
    return rows


def _badge_line(sub: Subentity) -> str:
    """A sub-entity's badges on one line: status, each badge field, assignee, mapped sub-entity, and
    the item that carries its deferred work."""
    shown = sub.display
    parts = [shown.status.badge, *(b.badge_label for b in shown.badges.values())]
    if sub.assignee:
        parts.append(sub.assignee)
    if shown.maps_to:
        parts.append(shown.maps_to)
    if sub.deferred_to:
        carrier = f" — {shown.carrier_title}" if shown.carrier_title else ""
        parts.append(f"Deferred to {sub.deferred_to}{carrier}")
    return "  ".join(parts)


def _blocks(show: ItemShow) -> list[Subentity]:
    """The sub-entities shown in full: none when the type hosts no sub-entity kind."""
    if show.display.summary is None:
        return []
    return [sub for sub in show.subentities if isinstance(sub, Subentity)]


def _print_summary(console: Console, show: ItemShow) -> None:
    summary = show.display.summary
    if summary is None:
        return
    table = Table(box=None, pad_edge=False)
    for column in summary.columns:
        table.add_column(column)
    for cells in summary.rows:
        table.add_row(*(e(c) for c in cells))
    console.print()
    console.print(table)


def _print_full_panes(console: Console, show: ItemShow, *, styled: bool, comments: bool) -> None:
    for sub in _blocks(show):
        title = f"{sub.local_id} — {sub.title}  {_badge_line(sub)}"
        if not styled:
            console.print(f"=== {title} ===", markup=False, highlight=False)
            if sub.body:
                console.print(sub.body, markup=False, highlight=False)
            if comments:
                print_comments_plain(console, sub.discussion)
            console.print()
            continue
        from rich.markdown import Markdown

        inner: list[RenderableType] = [Markdown(sub.body)] if sub.body else []
        if comments:
            inner += [
                Panel(Markdown(c.body), title=comment_title(c), expand=False)
                for c in sub.discussion
            ]
        body: RenderableType = Group(*inner) if inner else Markdown("_(empty)_")
        console.print(Panel(body, title=e(title), expand=False))


def _print_discussion(console: Console, show: ItemShow, *, styled: bool) -> None:
    if not show.discussion:
        console.print("[dim](no discussion)[/dim]")
        return
    console.print()
    if styled:
        print_comments_styled(console, show.discussion)
    else:
        print_comments_plain(console, show.discussion)


def _raw_metadata(show: ItemShow) -> list[str]:
    lines = [f"- **status:** {show.status}"]
    lines += [f"- **{code}:** {b.badge}" for code, b in show.display.badges.items()]
    lines += [f"- **{a.label}:** {a.value}" for a in show.display.attributes]
    if show.assignee:
        lines.append(f"- **assignee:** {show.assignee}")
    if show.parent:
        lines.append(f"- **parent:** {show.parent}")
    if show.author:
        lines.append(f"- **author:** {show.author}")
    if show.refs:
        lines.append(f"- **refs:** {_refs_line(show.refs)}")
    if show.labels:
        lines.append(f"- **labels:** {', '.join(show.labels)}")
    return lines


def _render_raw(console: Console, show: ItemShow, *, comments: bool, full: bool) -> None:
    """The markdown dossier: heading, metadata bullets and the body, then optionally one section
    per sub-entity and the discussion, printed with no markup."""
    lines = [f"# {show.id} — {show.title}", "", *_raw_metadata(show), "", show.display.body]
    summary = show.display.summary
    if full and summary is not None:
        for sub in _blocks(show):
            heading = f"## {sub.display.type} {sub.local_id} — {sub.title}"
            lines += ["", heading, "", _badge_line(sub), "", sub.body]
    if comments:
        lines += ["", "## Discussion"]
        for cmt in show.discussion:
            head = f"### {cmt.short_hash} {author_label(cmt)} — {cmt.ts}{edited_suffix(cmt)}"
            lines += ["", head, "", cmt.body]
        if not show.discussion:
            lines += ["", "_(no discussion)_"]
    console.print("\n".join(lines), markup=False, highlight=False, soft_wrap=True)


def render_show(show: ItemShow, console: Console, *, raw: bool, comments: bool, full: bool) -> None:
    """An item's panel and body, its sub-entity summary, and with *full* one pane per
    sub-entity and with *comments* its discussion; *raw* prints a markdown dossier instead."""
    if raw:
        _render_raw(console, show, comments=comments, full=full)
        return
    console.print(Panel("\n".join(_panel_rows(show)), expand=False))
    styled = is_styled(console)
    print_body(console, show.display.body, styled=styled, empty_hint=_EMPTY_BODY)
    _print_summary(console, show)
    if full:
        _print_full_panes(console, show, styled=styled, comments=comments)
    if comments:
        _print_discussion(console, show, styled=styled)


def item_cell(row: ItemRow | MineRow, key: str) -> Text | str:
    """The cell of an item row's table that *key* names; the status is coloured by its intent."""
    if key == "status":
        return status_text(row.status, row.display.status.intent)
    return cell_text(row, key)


def render_list(listing: ItemList, console: Console, *, compact: bool) -> None:
    """A listing as a table, or one line per item with *compact*; an empty one says how many
    closed items it hid."""
    if not listing.items:
        if listing.hidden:
            console.print(f"[dim]{listing.hidden} closed items hidden — use --all[/dim]")
        else:
            console.print("[dim]no items[/dim]")
        return
    if compact:
        for row in listing.items:
            line = Text.assemble(
                (row.id, "bold"),
                "  ",
                status_text(row.status, row.display.status.intent),
                "  ",
                row.title,
            )
            console.print(line, no_wrap=True, overflow="ellipsis")
        return
    table = Table(box=None, pad_edge=False)
    for column in listing.columns:
        table.add_column(column.header)
    for row in listing.items:
        table.add_row(*(item_cell(row, column.key) for column in listing.columns))
    console.print(table)


def render_status(row: ItemRow, console: Console) -> None:
    """The move an item made: its id and the status it is at now."""
    console.print(f"{row.id} → [bold]{row.status}[/bold]")
