"""The sub-entity read renderers: an item's sub-entities as a table, and one sub-entity shown."""

from rich.console import Console
from rich.table import Table

from squads._api._dto._subentities import SubentityList, SubentityShow
from squads._cli._render._comments import is_styled, print_comments_plain, print_comments_styled
from squads._cli._render._style import e


def render_subentities(listing: SubentityList, console: Console) -> None:
    """The summary table of the item's sub-entities, or a line saying it has none."""
    if not listing.items:
        console.print(f"[dim]no {listing.kind.name}s[/dim]")
        return
    table = Table(box=None, pad_edge=False)
    for column in listing.summary.columns:
        table.add_column(column)
    for cells in listing.summary.rows:
        table.add_row(*(e(c) for c in cells))
    console.print(table)


def _meta_line(sub: SubentityShow) -> str:
    """Status, assignee, each badge field with a value, mapping and deferral, on one line."""
    shown = sub.display
    meta = [f"status: {e(sub.status)}"]
    if sub.assignee:
        meta.append(f"assignee: {e(sub.assignee)}")
    meta += [f"{b.label.lower()}: {e(sub.badges[code])}" for code, b in shown.badges.items()]
    if sub.maps_to and shown.maps_to_kind:
        meta.append(f"{e(shown.maps_to_kind.label.lower())}: {e(sub.maps_to)}")
    if sub.deferred_to:
        carrier = f" — {e(shown.carrier_title)}" if shown.carrier_title else ""
        meta.append(f"deferred to: {e(sub.deferred_to)}{carrier}")
    return "  " + "   ".join(meta)


def render_subentity(sub: SubentityShow, console: Console) -> None:
    """A sub-entity's heading, metadata, body and discussion."""
    shown = sub.display
    console.print(f"[bold]{sub.local_id}[/bold] — {e(sub.title)}  [dim]({shown.kind.name})[/dim]")
    console.print(_meta_line(sub))
    console.print()
    console.print(e(sub.body) if sub.body else "[dim](no body yet)[/dim]")
    console.print("\n[bold]Discussion[/bold]")
    if sub.discussion:
        if is_styled(console):
            print_comments_styled(console, sub.discussion)
        else:
            print_comments_plain(console, sub.discussion)
    else:
        console.print(e(shown.discussion) if shown.discussion else "[dim](none)[/dim]")
