"""The board renderers: the numbered listing, a posted notice and a cleared one."""

from rich.console import Console

from squads._api import NoticeList, NoticeRow, NoticeWrite
from squads._cli._render._raw import print_raw
from squads._cli._render._style import e


def _raw_notice(n: NoticeRow) -> list[str]:
    """A notice as a numbered markdown item: its whole text, then its author, time and expiry."""
    first, *rest = n.body.splitlines() or [""]
    until = f", until {n.until}" if n.until else ""
    return [
        f"{n.n}. {first}",
        *(f"   {line}".rstrip() for line in rest),
        f"   — {n.author}, {n.posted_at}{until}",
    ]


def render_notices(listing: NoticeList, console: Console, *, raw: bool = False) -> None:
    """One numbered line per notice, with its author, time and expiry; *raw* prints each as a
    numbered markdown item with its whole text."""
    if raw:
        lines = [line for n in listing.items for line in _raw_notice(n)]
        print_raw(console, lines or ["no current notices"])
        return
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
