"""The board renderers: the listing, one notice in full, a posted notice and a cleared one."""

from rich.console import Console

from squads._api import NoticeDetail, NoticeList, NoticeRow, NoticeWrite
from squads._cli._render._raw import indented_body, print_raw
from squads._cli._render._style import e


def _raw_notice(n: NoticeRow) -> list[str]:
    """A notice as a numbered markdown item: its summary, then its author and expiry; further lines
    sit under the item, indented by the width of its marker."""
    first, *rest = n.summary.splitlines() or [""]
    until = f", until {n.until}" if n.until else ""
    marker = f"{n.n}. "
    pad = " " * len(marker)
    lines = [f"{marker}{first}", *(f"{pad}{line}".rstrip() for line in rest)]
    lines[-1] += f" — {n.author}{until}"
    return [*lines, *(indented_body(n.body, pad) if n.body else [])]


def render_notices(listing: NoticeList, console: Console, *, raw: bool = False) -> None:
    """One numbered line per notice, with its summary, author and expiry; *raw* prints each as a
    numbered markdown item, then the command that reads one in full. A listing that carries the
    bodies prints each under its notice and omits that command."""
    if raw:
        if not listing.items:
            print_raw(console, ["no current notices"])
            return
        lines = [line for n in listing.items for line in _raw_notice(n)]
        full = any(n.body is not None for n in listing.items)
        closing = [] if full else ["", "Read a notice in full with `sq board show <n>`."]
        print_raw(console, [*lines, *closing])
        return
    if not listing.items:
        console.print("[dim]no current notices[/dim]")
        return
    for n in listing.items:
        until = f"  [dim]until {e(n.until)}[/dim]" if n.until else ""
        console.print(f"[bold]{n.n}.[/bold] {e(n.summary)}  [dim]({e(n.author)})[/dim]{until}")
        for line in indented_body(n.body, "   ") if n.body else []:
            console.print(e(line) if line else "")


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
