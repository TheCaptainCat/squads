"""The search renderer: each matching item and its first matching lines."""

from rich.console import Console

from squads._api._dto._search import SearchResults
from squads._cli._render._style import e

#: How many matching lines a reader is shown per item.
_SHOWN_HITS = 3


def empty_note(empty: str, skipped: int) -> str:
    """The line for an empty result: *empty* when every item file was read, else marked partial
    with how many files were skipped, which are named after it."""
    if not skipped:
        return empty
    files = "item file" if skipped == 1 else "item files"
    return f"{empty} in what could be read — {skipped} {files} skipped, listed below"


def render_search(results: SearchResults, console: Console, *, text: str, skipped: int) -> None:
    """Each item that matched *text* with its first matching lines, or a line saying none did;
    *skipped* is how many item files could not be read."""
    if not results.items:
        console.print(f"[dim]{e(empty_note(f'no matches for {text}', skipped))}[/dim]")
    for hit in results.items:
        status_part = f"[dim]({e(hit.status)})[/dim]"
        console.print(f"[bold]{e(hit.id)}[/bold] {e(hit.title)} {status_part}")
        for match in hit.hits[:_SHOWN_HITS]:
            console.print(f"    [dim]{e(match.region)}:[/dim] {e(match.snippet)}")
