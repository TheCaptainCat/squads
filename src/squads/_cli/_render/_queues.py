"""The work-queue renderers: an inbox, the items assigned to someone, the blocked items and
each assignee's workload."""

from rich.console import Console
from rich.table import Table

from squads._api._dto._queues import Blocked, Inbox, Mine, Workload
from squads._cli._render._items import item_cell
from squads._cli._render._search import empty_note
from squads._cli._render._style import cell_text, e


def render_inbox(inbox: Inbox, console: Console, *, skipped: int) -> None:
    """Each item that mentions the slug with its mentioning lines, or a line saying none does;
    *skipped* is how many item files could not be read."""
    if not inbox.items:
        console.print(f"[dim]{e(empty_note(f'nothing for @{inbox.slug}', skipped))}[/dim]")
    for entry in inbox.items:
        status = entry.display.status_code
        console.print(f"[bold]{entry.id}[/bold] {e(entry.title)} [dim]({status})[/dim]")
        for line, region in zip(entry.lines, entry.regions, strict=True):
            suffix = f" [dim]({e(region)})[/dim]" if region else ""
            console.print(f"    {e(line)}{suffix}")


def render_mine(mine: Mine, console: Console) -> None:
    """The assigned items as a table, or a line saying there are none."""
    if not mine.items:
        console.print(f"[dim]nothing assigned to {e(mine.slug)}[/dim]")
        return
    table = Table(box=None, pad_edge=False)
    for column in mine.columns:
        table.add_column(column.header)
    for row in mine.items:
        table.add_row(*(item_cell(row, column.key) for column in mine.columns))
    console.print(table)


def render_blocked(blocked: Blocked, console: Console) -> None:
    """Each waiting item and what it waits on, or a line saying nothing is blocked."""
    if not blocked.items:
        console.print("[dim]nothing blocked[/dim]")
        return
    for entry in blocked.items:
        status = entry.display.status_code
        console.print(f"[bold]{entry.id}[/bold] {e(entry.title)} [dim]({status})[/dim]")
        for b in entry.blockers:
            console.print(f"    [red]blocked by[/red] {b.id} {e(b.title)} [dim]({b.status})[/dim]")


def render_workload(workload: Workload, console: Console) -> None:
    """Each assignee's counts as a table, or a line saying there is no work."""
    if not workload.items:
        console.print("[dim]no items[/dim]")
        return
    table = Table(box=None, pad_edge=False)
    for column in workload.columns:
        table.add_column(column.header)
    for row in workload.items:
        table.add_row(*(cell_text(row, column.key) for column in workload.columns))
    console.print(table)
