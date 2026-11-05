"""The raw markdown form of a show: a heading, the metadata list and the body, written whole."""

from rich.console import Console

from squads._api import Comment
from squads._cli._render._comments import author_label, edited_suffix, notice_lines
from squads._cli._render._rows import Row, raw_lines


def raw_head(rows: list[Row], heading: str | None, *, no_header: bool) -> list[str]:
    """The lines that open a raw show: given a *heading*, the heading and a blank line, then the
    rows as a list and a blank line; none with *no_header*."""
    if no_header:
        return []
    lines = [f"# {heading}", ""] if heading is not None else []
    return [*lines, *raw_lines(rows), ""]


def raw_discussion(lines: list[str], comments: list[Comment]) -> None:
    """Append the discussion to a raw show's *lines*, one section per comment."""
    lines += ["", "## Discussion"]
    for cmt in comments:
        head = f"### {cmt.short_hash} {author_label(cmt)} — {cmt.ts}{edited_suffix(cmt)}"
        lines += ["", head, "", *(f"_{n}_" for n in notice_lines(cmt)), cmt.body]
    if not comments:
        lines += ["", "_(no discussion)_"]


def print_raw(console: Console, lines: list[str]) -> None:
    """*lines* written in one call, as plain text: no markup, emoji, highlighting or wrapping."""
    text = "\n".join(lines).rstrip("\n")
    console.print(text, markup=False, highlight=False, emoji=False, soft_wrap=True)
