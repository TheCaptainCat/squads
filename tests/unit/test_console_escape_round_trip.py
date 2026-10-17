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


PAIR_CONTEXTS = ["{}{}", "{}: {}", "[red]{}[/red][red]{}[/red]", "{}[red]{}[/red]"]
PAIRS = [
    (r"x\[y", "z]"),
    (r"x\[/", "]"),
    (r"\[", "a]"),
    ("[", "x]"),
    ("trail\\", "[x]"),
    *[(a, b) for a in FIX[:4] for b in ("]", "z]", "[x]", "\\")],
]


@pytest.mark.parametrize("colour", [False, True])
@pytest.mark.parametrize("context", PAIR_CONTEXTS)
@pytest.mark.parametrize(("a", "b"), PAIRS)
def test_adjacent_escaped_values_print_byte_for_byte(
    a: str, b: str, context: str, colour: bool
) -> None:
    expected = _TAGS.sub("", context).format(a, b)
    assert _render(context.format(e(a), e(b)), colour=colour) == expected
