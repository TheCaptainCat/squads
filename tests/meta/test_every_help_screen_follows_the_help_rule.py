"""Every ``--help`` screen of the live command tree meets the mechanical half of the help rule in
CONTRIBUTING.md ("Writing ``--help`` text"): described options and arguments, a one-line summary,
one markup dialect, lines that fit 80 columns, no truncated enumeration, and a short body unless
a reviewer accepted a longer one.

The tree is walked twice: for the bundled vocabulary, and for a project override declaring one
custom type with a sub-entity kind and a ref kind, so a generated summary is held to the rule
for a name the bundled spec never saw. Each check is also run against a synthetic bad screen, so
a check that stops catching its violation fails here rather than passing silently.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from _help_tree import (
    CUSTOM_VOCABULARY_OVERRIDE,
    Node,
    command_nodes,
    documented_params,
    help_source,
    render_help,
    write_workflow_override,
)

pytestmark = pytest.mark.anyio

SUMMARY_MAX = 72
BODY_LINE_MAX = 78
BODY_LINES_MAX = 10

#: Commands whose body runs past ``BODY_LINES_MAX`` source lines, each with what a reader would
#: type or read differently without the extra lines. An entry that no longer matches a long
#: body fails as stale.
LONG_BODIES: tuple[tuple[str, str], ...] = ()

# What Rich reads as a tag: a bracketed span starting with a lowercase letter, `#`, `/` or `@`.
_BRACKET_TAG = re.compile(r"\[[a-z#/@][^\[\]]*\]")
_DOUBLED_BACKTICK = re.compile(r"``")
_ROLE = re.compile(r":[a-z]+:`")
_LITERAL_BLOCK_END = re.compile(r"::\s*$")


@dataclass(frozen=True)
class Screen:
    """What a check reads from one command."""

    label: str
    source: str
    params: tuple[tuple[str, str], ...]
    rendered: str

    @property
    def lines(self) -> list[str]:
        return self.source.splitlines()

    @property
    def summary(self) -> list[str]:
        out: list[str] = []
        for line in self.lines:
            if not line.strip():
                break
            out.append(line)
        return out

    @property
    def body(self) -> list[str]:
        rest = self.lines[len(self.summary) :]
        return [line for line in rest if line.strip()]

    @property
    def texts(self) -> list[str]:
        return [*self.lines, *(text for _, text in self.params)]


def screen_of(node: Node) -> Screen:
    params = tuple(
        (getattr(p, "name", "?") or "?", (getattr(p, "help", None) or "").strip())
        for p in documented_params(node)
    )
    return Screen(node.label, help_source(node), params, render_help(node))


def blank_descriptions(screen: Screen) -> list[str]:
    return [
        f"{screen.label}: {name} has no description" for name, text in screen.params if not text
    ]


def summary_shape(screen: Screen) -> list[str]:
    summary = screen.summary
    if len(summary) != 1:
        return [f"{screen.label}: the summary spans {len(summary)} lines, not one"]
    if len(summary[0]) > SUMMARY_MAX:
        return [f"{screen.label}: the summary is {len(summary[0])} characters"]
    return []


def one_markup_dialect(screen: Screen) -> list[str]:
    found: list[str] = []
    for text in screen.texts:
        if _DOUBLED_BACKTICK.search(text) or _ROLE.search(text):
            found.append(f"{screen.label}: doubled backtick or role in {text!r}")
        if _LITERAL_BLOCK_END.search(text):
            found.append(f"{screen.label}: line ends in `::`: {text!r}")
    return found


def no_bracket_tag(screen: Screen) -> list[str]:
    return [
        f"{screen.label}: Rich reads {m.group(0)!r} as a tag"
        for text in screen.texts
        for m in _BRACKET_TAG.finditer(text)
    ]


def lines_fit(screen: Screen) -> list[str]:
    return [
        f"{screen.label}: a line is {len(line)} columns: {line!r}"
        for line in screen.lines
        if len(line) > BODY_LINE_MAX
    ]


def nothing_truncated(screen: Screen) -> list[str]:
    return [
        f"{screen.label}: a screen line is cut by an ellipsis: {line!r}"
        for line in screen.rendered.splitlines()
        if "…" in line
    ]


def body_length(screen: Screen) -> int:
    return len(screen.body)


CHECKS: dict[str, Callable[[Screen], list[str]]] = {
    "every option and argument is described": blank_descriptions,
    "the summary is one line of 72 characters or fewer": summary_shape,
    "one markup dialect": one_markup_dialect,
    "no bracketed lowercase tag": no_bracket_tag,
    "no source line over 78 columns": lines_fit,
    "no enumeration cut by an ellipsis at 80 columns": nothing_truncated,
}


def _good() -> Screen:
    return Screen("sq good", "Do the thing.\n\nA body line.", (("--x", "What it is."),), "ok")


BAD_SCREENS: dict[str, Screen] = {
    "every option and argument is described": Screen("sq bad", "Do.", (("--x", ""),), ""),
    "the summary is one line of 72 characters or fewer": Screen("sq bad", "x" * 73, (), ""),
    "one markup dialect": Screen("sq bad", "Do ``it``.", (), ""),
    "no bracketed lowercase tag": Screen("sq bad", "Do.\n\nSee [bold] here.", (), ""),
    "no source line over 78 columns": Screen("sq bad", "Do.\n\n" + "x" * 79, (), ""),
    "no enumeration cut by an ellipsis at 80 columns": Screen("sq bad", "Do.", (), "a|b|c…"),
}


@pytest.mark.parametrize("name", list(CHECKS))
def test_each_check_catches_its_violation_and_passes_a_clean_screen(name: str) -> None:
    assert CHECKS[name](_good()) == []
    assert CHECKS[name](BAD_SCREENS[name]), name


def test_the_body_length_check_counts_non_blank_lines_after_the_summary() -> None:
    eleven = "Do.\n\n" + "\n\n".join(f"line {i}" for i in range(11))
    ten = "Do.\n\n" + "\n\n".join(f"line {i}" for i in range(10))
    assert body_length(Screen("sq x", eleven, (), "")) == 11
    assert body_length(Screen("sq x", ten, (), "")) == 10


def test_a_maintainer_note_after_a_form_feed_is_not_part_of_the_help() -> None:
    command = SimpleNamespace(help="Do it.\n\nBody.\f\nNote with [bold] and ``x``.", params=())
    assert "Note" not in help_source(Node(("x",), command, None))  # pyright: ignore[reportArgumentType]


def _screens() -> list[Screen]:
    return [screen_of(node) for node in command_nodes()]


def _violations(screens: list[Screen]) -> list[str]:
    return [
        f"[{name}] {found}"
        for name, check in CHECKS.items()
        for screen in screens
        for found in check(screen)
    ]


def _allowlist_problems(
    screens: list[Screen], allowlist: tuple[tuple[str, str], ...] = LONG_BODIES
) -> list[str]:
    long = {s.label for s in screens if body_length(s) > BODY_LINES_MAX}
    allowed = {path for path, _ in allowlist}
    return [
        *(f"[body over 10 lines, not on the allowlist] {path}" for path in sorted(long - allowed)),
        *(f"[stale allowlist entry] {path}" for path in sorted(allowed - long)),
        *(f"[allowlist entry without a reason] {path}" for path, why in allowlist if not why),
    ]


def test_a_long_body_off_the_allowlist_and_a_stale_entry_are_both_reported() -> None:
    long = Screen("sq long", "Do.\n\n" + "\n".join(f"line {i}" for i in range(11)), (), "")
    assert _allowlist_problems([long], ()) == ["[body over 10 lines, not on the allowlist] sq long"]
    assert _allowlist_problems([long], (("sq long", "reads differently"),)) == []
    stale = _allowlist_problems([_good()], (("sq long", "reads differently"),))
    assert stale == ["[stale allowlist entry] sq long"]


async def test_every_bundled_help_screen_passes(project) -> None:
    screens = _screens()
    found = [*_violations(screens), *_allowlist_problems(screens)]
    assert not found, "\n".join(found[:40])


async def test_every_custom_vocabulary_help_screen_passes(project) -> None:
    write_workflow_override(project.squad_dir, CUSTOM_VOCABULARY_OVERRIDE)
    screens = _screens()
    labels = {screen.label for screen in screens}
    assert {"sq investigation", "sq investigation analysis", "sq create investigation"} <= labels
    found = _violations(screens)
    assert not found, "\n".join(found[:40])
