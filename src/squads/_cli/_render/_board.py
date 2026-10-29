"""The board renderers: the numbered listing, a posted notice and a cleared one."""

from rich.console import Console

from squads._api._dto._board import NoticeList, NoticeWrite
from squads._cli._render._style import e


def render_notices(listing: NoticeList, console: Console) -> None:
    """One numbered line per notice, with its author, time and expiry."""
    if not listing.items:
        console.print("[dim]no current notices[/dim]")
        return
    for n in listing.items:
        until = f"  [dim]until {e(n.until)}[/dim]" if n.until else ""
        console.print(
            f"[bold]{n.n}.[/bold] {e(n.body)}  [dim]({e(n.author)} @ {e(n.posted_at)})[/dim]{until}"
        )


def render_posted(posted: NoticeWrite, console: Console) -> None:
    console.print(f"posted [bold]{e(posted.entry.id)}[/bold] as {e(posted.entry.author)}")


def render_cleared(cleared: NoticeWrite, console: Console) -> None:
    console.print(f"cleared [bold]{e(cleared.entry.id)}[/bold]")
