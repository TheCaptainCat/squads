"""A copyable remedy inside a long CLI error message survives being piped, independent of the
platform and independent of which console width Rich would otherwise wrap at.

Rich's ``Console.print`` reflows text to fit the console's latched width unless told not to; a
captured stderr pipe is a console just like a terminal, so without ``soft_wrap=True`` a long
enough ``error: ...`` message reflows and can insert a bare newline inside a command an operator
is told to copy and paste, or a script is told to grep. The three single-line ``error:`` render
sites -- the ``handle_errors`` decorator, the ``command`` async bridge, and the dynamically
registered refusal shim -- each print with ``soft_wrap=True`` for exactly this reason.

Each test below drives one of the three sites directly, with a captured in-memory console
pinned to a fixed width, so the guard is deterministic on every OS and does not depend on any
one real CLI command's message happening to be long enough on a given day. Assert the remedy
token has no newline inserted inside it -- not a particular wrap column.
"""

import io

import pytest
import typer
from rich.console import Console

from squads._cli import _common as common
from squads._errors import SquadsError

#: Padding long enough that the whole rendered line exceeds eighty columns, so a console that
#: still hard-wraps would reflow it.
_PADDING = "x" * 60
#: The copyable remedy token: what an operator would paste and a script would grep for.
_REMEDY = "sq role tech-writer status Active"
_MESSAGE = f"a refusal padded past eighty columns {_PADDING} -- run `{_REMEDY}` to fix it"


def _captured_console() -> tuple[Console, io.StringIO]:
    """A stderr-shaped console pinned to 80 columns, writing into an in-memory buffer -- so the
    assertion is deterministic everywhere rather than depending on a real terminal or pipe."""
    buf = io.StringIO()
    return Console(file=buf, stderr=True, width=80, legacy_windows=False), buf


def _assert_remedy_intact(buf: io.StringIO) -> None:
    output = buf.getvalue()
    assert _REMEDY in output, output
    # The regression this guards: a wrap inserts a real newline *inside* the remedy, splitting
    # it across two lines -- assert its absence, not any particular wrap column.
    assert "\n" not in output.strip("\n")


def test_handle_errors_site_keeps_the_remedy_on_one_line(monkeypatch) -> None:
    console, buf = _captured_console()
    monkeypatch.setattr(common, "err_console", console)

    @common.handle_errors
    def _boom() -> None:
        raise SquadsError(_MESSAGE)

    with pytest.raises(typer.Exit):
        _boom()

    _assert_remedy_intact(buf)


def test_command_bridge_site_keeps_the_remedy_on_one_line(monkeypatch) -> None:
    console, buf = _captured_console()
    monkeypatch.setattr(common, "err_console", console)

    @common.command
    async def _boom() -> None:
        raise SquadsError(_MESSAGE)

    with pytest.raises(typer.Exit):
        _boom()

    _assert_remedy_intact(buf)


def test_refusal_shim_site_keeps_the_remedy_on_one_line(monkeypatch) -> None:
    console, buf = _captured_console()
    monkeypatch.setattr(common, "err_console", console)
    # `spec_error_command` builds its refusal from whatever `_pending_spec_error` reports --
    # stand in for a genuinely failed workflow override with a fixed long message.
    monkeypatch.setattr(common, "_pending_spec_error", lambda ctx: _MESSAGE)

    leaf = common.spec_error_command("widget")
    assert leaf is not None
    ctx = leaf.make_context("widget", [])
    with pytest.raises(typer.Exit):
        leaf.invoke(ctx)

    _assert_remedy_intact(buf)
