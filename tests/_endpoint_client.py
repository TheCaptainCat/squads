"""The client of the daemon's command endpoint in the test process, standing in for the shim.

It sends a case's command line to the daemon application of its squad, answers a prompt from the
case's input, and runs locally what the shim would. The case's forged clock is bound on the
served command in process; it never travels on the wire.
"""

import base64
import os
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from squads._cli import app
from squads._context import get_context
from squads._daemon._lifecycle import fingerprint
from squads._endpoint import ChangeDirError, Endpoint, change_directory, endpoint_for
from squads._paths import resolve
from squads._shim import SENT_ENVIRONMENT
from tests._daemon_harness import Reply, Served, serve_squad

#: The commands that run in the client's own process.
LOCAL_ONLY = frozenset({"init", "adopt", "daemon", "ui"})

_VALUE_OPTIONS = frozenset({"-C", "--at", "--dir"})


@dataclass(frozen=True)
class Outcome:
    """What a command printed, as the runner's result reads."""

    exit_code: int
    output: str
    stdout: str
    stderr: str


def _leading(argv: list[str]) -> tuple[list[str], str | None]:
    """The `-C` values of *argv* and its first command word."""
    changes: list[str] = []
    i = 0
    while i < len(argv):
        word = argv[i]
        if word in _VALUE_OPTIONS:
            if word == "-C" and i + 1 < len(argv):
                changes.append(argv[i + 1])
            i += 2
        elif word.startswith("-C") and not word.startswith("--"):
            changes.append(word[2:])
            i += 1
        elif word.startswith("-"):
            i += 1
        else:
            return changes, word
    return changes, None


def _file_arguments(argv: list[str], command: str | None) -> list[str]:
    """The arguments that name a client file: the value of `--file`, and `import`'s first word."""
    named: list[str] = []
    for i, word in enumerate(argv):
        if word == "--file" and i + 1 < len(argv):
            named.append(argv[i + 1])
        elif word.startswith("--file="):
            named.append(word.removeprefix("--file="))
    if command == "import":
        after = argv[argv.index("import") + 1 :]
        named.extend(word for word in after[:1] if word == "-" or not word.startswith("-"))
    return named


def _terminal() -> dict[str, Any]:
    """A client whose streams are pipes."""
    stream = {"tty": False, "encoding": "utf-8"}
    return {"stdin": stream, "stdout": stream, "stderr": stream}


def post_commands(served: Served, body: dict[str, Any]) -> Reply:
    """Send *body* to the command endpoint of *served*."""
    return served.request("POST", "/v1/commands", body)


def command_body(argv: list[str], **fields: Any) -> dict[str, Any]:
    """The request that sends *argv* from the current directory as a client with piped streams
    would, with each of *fields* in place of the default."""
    cwd = str(Path.cwd())
    return {
        "argv": argv,
        "cwd": cwd,
        "client_dir": cwd,
        "env": {},
        "prog_name": "sq",
        "terminal": _terminal(),
        "attachments": {},
        "answers": [],
        **fields,
    }


class EndpointClient:
    """Runs a case's command lines through the daemon application of its squad."""

    def __init__(self) -> None:
        self._served: dict[Path, tuple[str, Served, ExitStack]] = {}
        self._clock: datetime | None = None

    def close(self) -> None:
        for _, _, stack in self._served.values():
            stack.close()
        self._served.clear()

    def _application(self, endpoint: Endpoint) -> Served:
        """The application serving *endpoint*'s squad on its current configuration."""
        current = fingerprint(endpoint.root, endpoint.squad_dir)
        held = self._served.get(endpoint.root)
        if held is not None and held[0] == current:
            return held[1]
        if held is not None:
            held[2].close()
        stack = ExitStack()
        served = stack.enter_context(
            serve_squad(resolve(client_cwd=endpoint.root), clock=lambda: self._clock)
        )
        self._served[endpoint.root] = (current, served, stack)
        return served

    @staticmethod
    def _attachments(
        argv: list[str], command: str | None, client_dir: Path, stdin: str
    ) -> dict[str, str] | None:
        """The client files the command line names, or ``None`` when one cannot be read."""
        attached: dict[str, str] = {}
        for name in _file_arguments(argv, command):
            try:
                raw = stdin.encode() if name == "-" else (client_dir / name).read_bytes()
            except OSError:
                return None
            attached[name] = base64.b64encode(raw).decode("ascii")
        return attached

    def _plan(self, argv: list[str], stdin: str) -> dict[str, Any] | None:
        """The request that serves *argv*, or ``None`` when the shim would run it locally."""
        changes, command = _leading(argv)
        if command in LOCAL_ONLY or argv == ["--version"]:
            return None
        cwd = Path.cwd()
        try:
            client_dir = change_directory(cwd, changes)
        except ChangeDirError, OSError:
            return None
        endpoint = endpoint_for(client_dir, environ={}, version="test")
        if endpoint is None or not endpoint.enabled:
            return None
        attachments = self._attachments(argv, command, client_dir, stdin)
        if attachments is None:
            return None
        env = {name: os.environ[name] for name in SENT_ENVIRONMENT if name in os.environ}
        request = command_body(argv, client_dir=str(client_dir), env=env, attachments=attachments)
        return {"endpoint": endpoint, "request": request}

    def invoke(self, runner: CliRunner, argv: list[str], *, input: str | None = None) -> Any:
        """The result of *argv*: the daemon's, or the runner's when the shim would not ask it."""
        stdin = input or ""
        plan = self._plan(argv, stdin)
        if plan is None:
            return runner.invoke(app, argv, input=input)
        self._clock = get_context().clock_override
        served = self._application(plan["endpoint"])
        typed = iter(stdin.splitlines())
        shown: list[tuple[str, str]] = []
        request = plan["request"]
        while True:
            reply = post_commands(served, request)
            if reply.status == 503:
                return runner.invoke(app, argv, input=input)
            assert reply.status == 200, reply.body
            answer = reply.json()
            shown.extend((stream, text) for stream, text in answer["output"])
            if answer["kind"] == "done":
                return _outcome(answer["exit_code"], shown)
            shown.append((answer["stream"], answer["text"]))
            line = next(typed, "")
            if answer["stream"] == "stdout":
                # The runner echoes the line a prompt reads, as a terminal does.
                shown.append(("stdout", line + "\n"))
            request = {
                **request,
                "answers": [*request["answers"], {"digest": answer["digest"], "line": line}],
            }


def _outcome(exit_code: int, shown: list[tuple[str, str]]) -> Outcome:
    return Outcome(
        exit_code=exit_code,
        output="".join(text for _, text in shown),
        stdout="".join(text for stream, text in shown if stream == "stdout"),
        stderr="".join(text for stream, text in shown if stream == "stderr"),
    )
