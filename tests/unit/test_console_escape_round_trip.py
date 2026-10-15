import io
import re

import pytest
from rich.console import Console

from squads._cli._common import e

FIX = [
    r"\[A-Z]",
    r"\\[A-Z]",
    r"\[[A-Z]+-\d+\]",
    "trail\\",
    "a\\\\",
    r"x\[a-z]+\\",
]
GUARD = ["[x]", "[/x]", r"\[x]", r"\\\[x]", "[[x]", "plain", ""]
CONTEXTS = ["{}", "{} tail", "[red]{}[/red]"]
_TAGS = re.compile(r"\[/?red\]")
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _render(markup: str, *, colour: bool) -> str:
    buf = io.StringIO()
    console = Console(
        file=buf,
        color_system="standard" if colour else None,
        force_terminal=colour,
        width=500,
        highlight=False,
    )
    console.print(markup, end="")
    return _ANSI.sub("", buf.getvalue())


@pytest.mark.parametrize("colour", [False, True])
@pytest.mark.parametrize("context", CONTEXTS)
@pytest.mark.parametrize("s", FIX + GUARD)
def test_escaped_text_prints_byte_for_byte(s: str, context: str, colour: bool) -> None:
    expected = _TAGS.sub("", context).format(s)
    assert _render(context.format(e(s)), colour=colour) == expected
