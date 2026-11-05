"""The board renderers: the listing, one notice in full, a posted notice and a cleared one."""

from rich.console import Console

from squads._api import NoticeDetail, NoticeList, NoticeRow, NoticeWrite
from squads._cli._render._raw import print_raw
from squads._cli._render._style import e


def _raw_notice(n: NoticeRow) -> list[str]:
    """A notice as a numbered markdown item: its summary, then its author and expiry."""
    first, *rest = n.summary.splitlines() or [""]
    until = f", until {n.until}" if n.until else ""
    lines = [f"{n.n}. {first}", *(f"   {line}".rstrip() for line in rest)]
    lines[-1] += f" — {n.author}{until}"
    return lines


def render_notices(listing: NoticeList, console: Console, *, raw: bool = False) -> None:
    """One numbered line per notice, with its summary, author and expiry; *raw* prints each as a
    numbered markdown item, then the command that reads one in full."""
    if raw:
        if not listing.items:
            print_raw(console, ["no current notices"])
            return
        lines = [line for n in listing.items for line in _raw_notice(n)]
        print_raw(console, [*lines, "", "Read a notice in full with `sq board show <n>`."])
        return
    if not listing.items:
        console.print("[dim]no current notices[/dim]")
        return
    for n in listing.items:
        until = f"  [dim]until {e(n.until)}[/dim]" if n.until else ""
        console.print(f"[bold]{n.n}.[/bold] {e(n.summary)}  [dim]({e(n.author)})[/dim]{until}")


def render_notice(notice: NoticeDetail, console: Console) -> None:
    """The notice's summary, author, time and expiry, then its body when it has one."""
    console.print(f"[bold]{e(notice.summary)}[/bold]")
    console.print(f"[dim]author: {e(notice.author)}[/dim]")
    console.print(f"[dim]posted: {e(notice.posted_at)}[/dim]")
    if notice.until:
        console.print(f"[dim]until: {e(notice.until)}[/dim]")
    if notice.body:
        console.print()
        console.print(notice.body, markup=False, highlight=False)


def render_posted(posted: NoticeWrite, console: Console) -> None:
    console.print(f"posted [bold]{e(posted.entry.id)}[/bold] as {e(posted.entry.author)}")


def render_cleared(cleared: NoticeWrite, console: Console) -> None:
    console.print(f"cleared [bold]{e(cleared.entry.id)}[/bold]")
