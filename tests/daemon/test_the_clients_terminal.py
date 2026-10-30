"""What a served command takes from its client's terminal and environment: encodings, whether
streams are terminals, size, a Windows console's features, spans, and Typer's own consoles."""

import inspect
import os
import re
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import typer
import typer.main
from rich.default_styles import DEFAULT_STYLES
from typer._click import Command

from squads._cli import _common as common
from squads._cli import main_callback
from squads._context import ServedCommand, bind_context, get_context
from squads._daemon._proxies import TYPER_CONSOLE, TYPER_STYLES
from squads._paths import SquadPaths
from tests._endpoint_client import command_body, post_commands, terminal_facts

#: What the daemon would otherwise inherit from the developer's shell.
CLIENT_VARIABLES = {
    "COLUMNS",
    "LINES",
    "FORCE_COLOR",
    "CLICOLOR_FORCE",
    "PY_COLORS",
    "TERMINAL_WIDTH",
    "TTY_COMPATIBLE",
    "TTY_INTERACTIVE",
    "_TYPER_FORCE_DISABLE_TERMINAL",
    "NO_COLOR",
    "COLORTERM",
    "GITHUB_ACTIONS",
    "SQUADS_SPANS",
}

SQ = str(Path(sys.executable).parent / ("sq.exe" if sys.platform == "win32" else "sq"))

#: Cases that compare with a real `sq` process, which a Windows console lays out by its own rules.
needs_posix = pytest.mark.skipif(sys.platform == "win32", reason="compares with a POSIX process")


def _clean_environment() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k not in CLIENT_VARIABLES}


def _local(argv: list[str], env: dict[str, str], cwd: Path) -> str:
    """What `sq` run as a process prints, its streams pipes."""
    done = subprocess.run(
        [SQ, *argv],
        env={**_clean_environment(), "SQUADS_DAEMON": "off", **env},
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout


def _in_a_terminal(argv: list[str], env: dict[str, str], cwd: Path, size: tuple[int, int]) -> str:
    """What `sq` prints on a pseudo-terminal of *size* (columns, lines)."""
    import fcntl
    import pty
    import struct
    import termios

    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", size[1], size[0], 0, 0))
    process = subprocess.Popen(
        [SQ, *argv],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        env={**_clean_environment(), "SQUADS_DAEMON": "off", **env},
        cwd=cwd,
    )
    os.close(slave)
    received = b""
    while True:
        try:
            data = os.read(master, 65536)
        except OSError:
            break
        if not data:
            break
        received += data
    process.wait()
    os.close(master)
    return received.decode().replace("\r\n", "\n")


def _help(served, terminal: dict[str, Any], env: dict[str, str] | None = None) -> str:
    reply = post_commands(served, command_body(["--help"], env=env or {}, terminal=terminal))
    assert reply.status == 200
    [(_, text)] = reply.json()["output"]
    return text


TERMINAL_ENV = {"TERM": "xterm-256color"}


@needs_posix
def test_a_client_on_a_terminal_gets_the_layout_local_mode_gives_a_terminal(
    project: SquadPaths, serve, tmp_path: Path
) -> None:
    local = _in_a_terminal(["--help"], TERMINAL_ENV, tmp_path, (70, 20))
    assert "\x1b[" in local

    served = _help(serve(project), terminal_facts(tty=True, size=(70, 20)), TERMINAL_ENV)

    assert served == local


@needs_posix
def test_a_client_that_is_not_a_terminal_gets_the_plain_layout(
    project: SquadPaths, serve, tmp_path: Path
) -> None:
    served = _help(serve(project), terminal_facts(tty=False), TERMINAL_ENV)

    assert served == _local(["--help"], TERMINAL_ENV, tmp_path)
    assert "\x1b[" not in served


def test_the_size_of_the_clients_terminal_decides_the_width(project: SquadPaths, serve) -> None:
    daemon = serve(project)
    narrow = _help(daemon, terminal_facts(tty=True, size=(50, 20)), TERMINAL_ENV)
    wide = _help(daemon, terminal_facts(tty=True, size=(90, 20)), TERMINAL_ENV)

    assert max(len(re.sub(r"\x1b\[[0-9;]*m", "", ln)) for ln in narrow.splitlines()) == 50
    assert max(len(re.sub(r"\x1b\[[0-9;]*m", "", ln)) for ln in wide.splitlines()) == 90


def test_a_windows_console_without_virtual_terminal_processing_is_laid_out_as_legacy(
    project: SquadPaths, serve
) -> None:
    daemon = serve(project)
    modern = _help(daemon, terminal_facts(tty=True, size=(70, 20), windows_vt=True), TERMINAL_ENV)
    legacy = _help(daemon, terminal_facts(tty=True, size=(70, 20), windows_vt=False), TERMINAL_ENV)

    assert modern != legacy


@pytest.mark.parametrize(
    ("detected", "legacy", "truecolor", "chosen"),
    [
        (None, False, True, None),
        ("256", False, None, "256"),
        ("256", False, True, "truecolor"),
        ("truecolor", False, False, "256"),
        ("truecolor", True, True, "windows"),
    ],
)
def test_a_windows_clients_console_decides_the_colour_system(
    detected: str | None, legacy: bool, truecolor: bool | None, chosen: str | None
) -> None:
    assert common.windows_color_system(detected, legacy, truecolor) == chosen


def test_a_served_console_takes_its_colour_system_from_the_clients_console(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TTY_COMPATIBLE", "1")
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.delenv("COLORTERM", raising=False)

    def system(truecolor: bool) -> str | None:
        served = ServedCommand({}, "utf-8", None, None, True, truecolor, 0.0, lambda: None)
        bind_context(replace(get_context(), served=served))
        return common.build_console(stderr=False).color_system

    assert (system(True), system(False)) == ("truecolor", "256")


def test_a_prompt_answered_with_the_end_of_input_aborts_the_command(
    project: SquadPaths, serve, runner
) -> None:
    from squads._cli import app

    runner.invoke(app, ["create", "task", "Prompted", "--author", "manager"])
    runner.invoke(app, ["task", "2", "comment", "-m", "Doomed", "--as", "manager"])
    short = re.search(r"\b[0-9a-f]{7}\b", runner.invoke(app, ["task", "2", "comments"]).output)
    assert short is not None
    argv = ["task", "2", "comment", short.group(0), "remove", "--as", "manager"]
    daemon = serve(project)
    asked = post_commands(daemon, command_body(argv)).json()

    answers = [{"digest": asked["digest"], "line": None}]
    ended = post_commands(daemon, command_body(argv, answers=answers))

    assert (ended.status, ended.json()) == (
        200,
        {"kind": "done", "output": [["stderr", "Aborted.\n"]], "exit_code": 1},
    )
    assert "Doomed" in runner.invoke(app, ["task", "2", "comments"]).output


def _echoing() -> Command:
    host = typer.Typer(name="sq")
    host.callback()(main_callback)

    @host.command("echo-cafe")
    def echo_cafe() -> None:  # pyright: ignore[reportUnusedFunction]
        typer.echo("Café")

    @host.command("which-stream")
    def which_stream() -> None:  # pyright: ignore[reportUnusedFunction]
        from typer._click._compat import _default_text_stdout  # pyright: ignore[reportPrivateUsage]

        typer.echo("itself" if _default_text_stdout() is sys.stdout else "wrapped")

    return typer.main.get_command(host)


def test_click_writes_text_to_the_proxy_itself_so_no_wrapper_translates_its_newlines(
    project: SquadPaths, serve
) -> None:
    reply = post_commands(serve(project, command=_echoing()), command_body(["which-stream"]))

    assert reply.json()["output"] == [["stdout", "itself\n"]]


def test_each_request_is_written_in_its_own_clients_encoding(project: SquadPaths, serve) -> None:
    daemon = serve(project, command=_echoing())
    answers = []
    for encoding in ("cp1252", "utf-8", "cp1252"):
        body = command_body(["echo-cafe"], terminal=terminal_facts(encoding=encoding))
        answers.append(post_commands(daemon, body).json())

    assert answers == [{"kind": "done", "output": [["stdout", "Café\n"]], "exit_code": 0}] * 3


def _span_names(output: list[list[str]]) -> list[str]:
    return [
        line.split()[1]
        for stream, text in output
        if stream == "stderr"
        for line in text.splitlines()
        if line.startswith("SQUADS_SPAN ")
    ]


def test_spans_are_printed_when_the_client_asks_for_them_and_never_for_the_daemons_own_switch(
    project: SquadPaths, serve, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SQUADS_SPANS", "1")
    daemon = serve(project)
    asked = post_commands(
        daemon, command_body(["list", "--json"], env={"SQUADS_SPANS": "1"})
    ).json()
    unasked = post_commands(daemon, command_body(["list", "--json"])).json()

    assert "startup" in _span_names(asked["output"])
    assert _span_names(unasked["output"]) == []


def test_the_spans_of_a_command_count_from_its_requests_arrival(project: SquadPaths, serve) -> None:
    daemon = serve(project)
    reply = post_commands(
        daemon, command_body(["list", "--json"], env={"SQUADS_SPANS": "t=0.0"})
    ).json()

    startup = next(
        float(line.split()[2])
        for stream, text in reply["output"]
        if stream == "stderr"
        for line in text.splitlines()
        if line.startswith("SQUADS_SPAN startup ")
    )
    assert 0 <= startup < 2000


HELP_CLIENTS = [
    (
        {"FORCE_COLOR": "1", "COLUMNS": "60", "COLORTERM": "truecolor", "TERM": "xterm-256color"},
        True,
    ),
    ({"TERMINAL_WIDTH": "50", "FORCE_COLOR": "1", "TERM": "xterm-256color"}, True),
    ({"PY_COLORS": "1", "TERM": "xterm-256color"}, True),
    ({"GITHUB_ACTIONS": "true", "TERM": "xterm-256color"}, True),
    ({"FORCE_COLOR": "1", "_TYPER_FORCE_DISABLE_TERMINAL": "1", "TERM": "xterm-256color"}, False),
]


@needs_posix
@pytest.mark.parametrize(("client", "coloured"), HELP_CLIENTS)
def test_help_is_laid_out_for_the_clients_environment_as_local_mode_lays_it_out(
    client: dict[str, str], coloured: bool, project: SquadPaths, serve, tmp_path: Path
) -> None:
    local = _local(["--help"], client, tmp_path)
    assert ("\x1b[" in local) is coloured

    assert _help(serve(project), terminal_facts(), client) == local


def test_the_typer_console_a_served_command_replaces_is_the_shape_it_expects() -> None:
    parameters = inspect.signature(TYPER_CONSOLE).parameters
    console = TYPER_CONSOLE()
    theme = console._theme_stack._entries[-1]  # pyright: ignore[reportPrivateUsage]

    assert [(p.name, p.default) for p in parameters.values()] == [("stderr", False)]
    assert set(theme) - set(DEFAULT_STYLES) == set(TYPER_STYLES)
