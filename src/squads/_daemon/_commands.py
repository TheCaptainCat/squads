"""The command endpoint: a CLI command line run in this process on the daemon's own operations.

It runs on the daemon's squad and reads no path the client names; the client's files come with the
request and the command's output goes back as ordered chunks.
"""

import base64
import binascii
import json
import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

import typer._click as _click  # underscore is upstream's own private module path, not ours
import typer.main
from pydantic import BaseModel, ConfigDict, ValidationError

from squads import _aio as aio
from squads._api._api import Api, Operation
from squads._api._response import Response
from squads._cli import app
from squads._cli import run as run_cli
from squads._context import RequestContext, ServedCommand
from squads._daemon import _proxies as proxies
from squads._errors import SquadsError
from squads._services._service import RequestScope

_log = logging.getLogger("squads.daemon")

#: The text a client reads when the daemon's command failed for a reason of its own.
INTERNAL_ERROR = "error: internal error; the traceback is in the daemon's log\n"


class StreamFacts(BaseModel):
    """Whether one of the client's standard streams is a terminal, and its encoding."""

    model_config = ConfigDict(extra="forbid")

    tty: bool
    encoding: str


class Terminal(BaseModel):
    """The client's terminal: its three standard streams, its size when one of them is a terminal,
    and on Windows whether the console has virtual-terminal processing."""

    model_config = ConfigDict(extra="forbid")

    stdin: StreamFacts
    stdout: StreamFacts
    stderr: StreamFacts
    size: tuple[int, int] | None = None
    windows_vt: bool | None = None


class CommandRequest(BaseModel):
    """A command line and what it needs from the client's machine."""

    model_config = ConfigDict(extra="forbid")

    argv: list[str]
    cwd: str
    client_dir: str
    env: dict[str, str] = {}
    prog_name: str
    terminal: Terminal
    attachments: dict[str, str] = {}
    answers: list[proxies.Answer] = []


def parse_request(raw: bytes) -> CommandRequest:
    """The request *raw* carries, read with the standard library so a lone surrogate in an
    argument survives; an invalid one is refused as an invalid request."""
    try:
        decoded: Any = json.loads(raw)
        return CommandRequest.model_validate(decoded)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        raise SquadsError(f"invalid request: {problems}") from exc
    except ValueError as exc:  # a body that is not JSON, or not UTF-8
        raise SquadsError(f"invalid request: the body is not valid JSON: {exc}") from exc


def _attachments(encoded: dict[str, str]) -> dict[str, bytes]:
    try:
        return {name: base64.b64decode(data, validate=True) for name, data in encoded.items()}
    except binascii.Error as exc:
        raise SquadsError(f"invalid request: an attachment is not base64: {exc}") from exc


class ServedApi:
    """The daemon's operations as a served command calls them, noting whether one has written."""

    def __init__(self, inner: Api) -> None:
        self._inner = inner
        self.written = False

    async def call[Req: BaseModel, Res](self, op: Operation[Req, Res], req: Req) -> Response[Res]:
        if op.method != "GET":
            self.written = True
        return await self._inner.call(op, req)


class Session:
    """One served command: its request, the capture it writes to and the operations it calls."""

    def __init__(self, request: CommandRequest, api: Api) -> None:
        for path in (request.cwd, request.client_dir):
            if not Path(path).is_absolute():
                raise SquadsError(f"invalid request: {path!r} is not an absolute path")
        terminal = request.terminal
        self.request = request
        self.api = ServedApi(api)
        self.capture = proxies.Capture(
            env={name: value for name, value in request.env.items() if name in proxies.SENT},
            ttys={
                proxies.STDIN: terminal.stdin.tty,
                proxies.STDOUT: terminal.stdout.tty,
                proxies.STDERR: terminal.stderr.tty,
            },
            encodings={
                proxies.STDIN: terminal.stdin.encoding,
                proxies.STDOUT: terminal.stdout.encoding,
                proxies.STDERR: terminal.stderr.encoding,
            },
            answers=request.answers,
        )
        size = terminal.size
        self.served = ServedCommand(
            attachments=_attachments(request.attachments),
            stdin_encoding=terminal.stdin.encoding,
            columns=size[0] if size else None,
            lines=size[1] if size else None,
            windows_vt=terminal.windows_vt,
            begin_prompt=self._begin_prompt,
        )

    def _begin_prompt(self) -> None:
        if self.api.written:
            raise RuntimeError("a prompt was reached after an operation had written")
        self.capture.begin_prompt()


class Commands:
    """Runs command lines on the daemon's squad, one command tree for all of them."""

    def __init__(
        self,
        scope: RequestScope,
        command: _click.Command | None = None,
        clock: Callable[[], datetime | None] = lambda: None,
    ) -> None:
        proxies.install()
        self._scope = scope
        #: The command tree, built when the daemon starts.
        self._command = command if command is not None else typer.main.get_command(app)
        #: The forged time a harness binds on every command's context; the wire never carries it.
        self._clock = clock

    def context(self, session: Session) -> RequestContext:
        """The context *session*'s command starts from: the daemon's squad, paths spelled from the
        client's directory, and the request's own operations and files."""
        base = self._scope.command_context(Path(session.request.cwd))
        return replace(base, clock_override=self._clock(), api=session.api, served=session.served)

    async def run(self, session: Session) -> dict[str, Any]:
        """The command's answer: ``done`` with its output and exit code, or ``prompt``."""
        return await aio.to_thread(lambda: self._execute(session))

    def _execute(self, session: Session) -> dict[str, Any]:
        proxies.install()
        proxies.CURRENT.set(session.capture)
        try:
            code = run_cli(
                session.request.argv, prog_name=session.request.prog_name, command=self._command
            )
        except proxies.PromptRequired as stop:
            return {
                "kind": "prompt",
                "output": stop.before,
                "text": stop.text,
                "stream": stop.stream,
                "digest": stop.digest,
            }
        except Exception:  # the daemon survives anything a command does
            _log.exception("a served command failed")
            session.capture.write(proxies.STDERR, INTERNAL_ERROR)
            code = 1
        return {"kind": "done", "output": session.capture.chunks(), "exit_code": code}
