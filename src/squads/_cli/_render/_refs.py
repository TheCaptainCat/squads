"""The refs renderer: one table per direction asked for."""

from rich.console import Console
from rich.table import Table

from squads._api._dto._refs import RefEntry, Refs


def render_refs(refs: Refs, console: Console) -> None:
    """The refs the item carries, then the refs carried to it, each direction that was asked
    for; an empty direction says so."""
    for entries, label in ((refs.out, "→ refs"), (refs.incoming, "← backrefs")):
        if entries is not None:
            _print_direction(console, label, entries)


def _print_direction(console: Console, label: str, entries: list[RefEntry]) -> None:
    if not entries:
        console.print(f"[dim]{label}: none[/dim]")
        return
    table = Table(title=label, box=None, pad_edge=False, title_justify="left")
    table.add_column("ID")
    table.add_column("Kind")
    for entry in entries:
        table.add_row(entry.id, entry.kind)
    console.print(table)
