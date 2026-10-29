"""The discussion renderers: comment panes on a terminal, delimited text otherwise."""

from rich.console import Console
from rich.panel import Panel

from squads._api._dto._items import Comment
from squads._cli._render._style import e


def is_styled(console: Console) -> bool:
    """Whether *console* renders markup: a terminal, colour enabled."""
    return console.is_terminal and not console.no_color


def author_label(cmt: Comment) -> str:
    """``Name (slug)``, or the slug once when the name is it."""
    return cmt.author if cmt.author == cmt.author_slug else f"{cmt.author} ({cmt.author_slug})"


def edited_suffix(cmt: Comment) -> str:
    """`` (edited <ts>)`` for an edited comment, else nothing."""
    return f" (edited {cmt.edited_ts})" if cmt.edited_ts else ""


def comment_title(cmt: Comment) -> str:
    """A comment pane's title: its hash, time and author, escaped."""
    return f"{e(cmt.short_hash)}  {e(cmt.ts)}  {e(author_label(cmt))}{e(edited_suffix(cmt))}"


def print_comments_plain(console: Console, comments: list[Comment]) -> None:
    """Each comment as a delimited header line, its body and a blank line, with no markup."""
    for cmt in comments:
        header = f"--- {cmt.short_hash} [{cmt.ts}] {author_label(cmt)}{edited_suffix(cmt)} ---"
        console.print(header, markup=False, highlight=False)
        console.print(cmt.body, markup=False, highlight=False)
        console.print()


def print_comments_styled(console: Console, comments: list[Comment]) -> None:
    """Each comment as a pane of rendered markdown."""
    from rich.markdown import Markdown

    for cmt in comments:
        console.print(Panel(Markdown(cmt.body), title=comment_title(cmt), expand=False))


def print_comments(console: Console, comments: list[Comment]) -> None:
    """*comments* as panes on a terminal and as delimited text otherwise; a line saying so when
    there are none."""
    if not comments:
        console.print("[dim](no comments)[/dim]")
    elif is_styled(console):
        print_comments_styled(console, comments)
    else:
        print_comments_plain(console, comments)
