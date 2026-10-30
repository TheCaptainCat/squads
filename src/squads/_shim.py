"""The CLI's entry point: a client of the daemon's command endpoint on the standard library alone.

``squads.__main__:main`` calls :func:`main`. It sends the command line to the squad's daemon and
writes the answer, or runs the command in this process (by importing ``squads._cli``) when the
command is local-only or no daemon can be had before anything is sent. It parses nothing of the
command line beyond the root options and the first command words, and it imports no other
``squads`` module on the way to a daemon: only this one, ``squads._endpoint`` and, to start a
daemon, ``squads._daemon_start`` and ``squads._daemon_link``. It also holds the environment
variables a served command can see, which the daemon reads as well.
"""

import contextlib
import gc
import io
import json
import os
import socket
import sys
import time
from pathlib import Path

from squads._endpoint import ChangeDirError, Endpoint, change_directory, endpoint_for, read_record

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any

#: The variables the client sends with a command, absent ones left out. A variable outside this
#: list does not exist for a served command; the daemon's diagnostic variables are never on it.
SENT_ENVIRONMENT: tuple[str, ...] = (
    "SQUADS_SESSION_ID",
    "SQUADS_PARENT_SESSION_ID",
    "SQUADS_SPANS",
    "PY_COLORS",
    "GITHUB_ACTIONS",
    "TERMINAL_WIDTH",
    "_TYPER_FORCE_DISABLE_TERMINAL",
    "NO_COLOR",
    "FORCE_COLOR",
    "CLICOLOR_FORCE",
    "TTY_COMPATIBLE",
    "TTY_INTERACTIVE",
    "COLUMNS",
    "LINES",
    "TERM",
    "COLORTERM",
    "_SQ_COMPLETE",
    "_SQUADS_COMPLETE",
    "COMP_WORDS",
    "COMP_CWORD",
    "_TYPER_COMPLETE_ARGS",
    "_TYPER_COMPLETE_WORD_TO_COMPLETE",
    "_TYPER_COMPLETE_FISH_ACTION",
)

#: The root commands that run in this process without contacting a daemon.
LOCAL_ONLY: frozenset[str] = frozenset({"init", "adopt", "daemon", "ui"})

#: The root options that act on the client's own machine, so they run here.
LOCAL_ROOT_OPTIONS: frozenset[str] = frozenset({"--install-completion", "--show-completion"})

#: The options whose value names a client file.
FILE_OPTIONS: tuple[str, ...] = ("--file",)

#: The root commands whose first argument names a client file.
FILE_ARGUMENT_COMMANDS: tuple[str, ...] = ("import",)

#: The command paths whose operation has no answer deadline, with that operation's name.
LONG_COMMANDS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("repair",), "squad.repair"),
    (("renumber",), "squad.renumber"),
    (("import",), "squad.import"),
    (("migrate", "up"), "squad.migrate"),
    (("migrate", "repad"), "squad.repad"),
    (("migrate", "rename-type"), "squad.rename-type"),
    (("migrate", "rename-status"), "squad.rename-status"),
    (("migrate", "rename-field"), "squad.rename-field"),
    (("migrate", "rename-kind"), "squad.rename-kind"),
)

#: The root options that take a value in the next argument.
_VALUE_OPTIONS = ("-C", "--at", "--dir")

#: Seconds a connection may take to open.
CONNECT_TIMEOUT = 5.0
#: Seconds a command may take to answer, unless it is a long one.
ANSWER_TIMEOUT = 300.0
#: Seconds a long command waits before it says it is waiting.
WAIT_NOTICE_AFTER = 10.0
#: Seconds between the looks a Windows client takes at its socket while it waits.
_POLL_SECONDS = 0.25

_MAY_STILL_COMPLETE = "the operation may still complete. Check its result before running it again."


class Leading:
    """The part of a command line the root command reads: its ``-C`` values, its options, and
    where the command words begin."""

    __slots__ = ("at", "dirs", "options", "words")

    def __init__(self, dirs: list[str], options: list[str], words: list[str], at: int) -> None:
        #: The ``-C`` values, in order.
        self.dirs = dirs
        #: The root options that take no value, as written.
        self.options = options
        #: The command words that follow the root options, up to the first option.
        self.words = words
        #: The index in the command line of the first command word (its length when there is none).
        self.at = at


def leading(argv: list[str]) -> Leading:
    """What the root command reads of *argv*: options before the first command word, a value
    option taking the next argument whatever it looks like."""
    dirs: list[str] = []
    options: list[str] = []
    i = 0
    while i < len(argv):
        word = argv[i]
        if word == "--":
            i += 1
            break
        if word in _VALUE_OPTIONS:
            if word == "-C" and i + 1 < len(argv):
                dirs.append(argv[i + 1])
            i += 2
        elif word.startswith("-C"):
            dirs.append(word[2:])
            i += 1
        elif word.startswith(("--at=", "--dir=")):
            i += 1
        elif word.startswith("-") and word != "-":
            options.append(word)
            i += 1
        else:
            break
    at = min(i, len(argv))
    words: list[str] = []
    while i < len(argv) and not (argv[i].startswith("-") and argv[i] != "-"):
        words.append(argv[i])
        i += 1
    return Leading(dirs, options, words, at)


def file_arguments(argv: list[str], lead: Leading) -> list[str]:
    """The arguments of *argv* that name a client file: the value of ``--file`` wherever it
    appears, and the first argument of ``import``."""
    named: list[str] = []
    for i, word in enumerate(argv):
        if word in FILE_OPTIONS:
            if i + 1 < len(argv):
                named.append(argv[i + 1])
        else:
            named.extend(
                word[len(option) + 1 :] for option in FILE_OPTIONS if word.startswith(option + "=")
            )
    if lead.words and lead.words[0] in FILE_ARGUMENT_COMMANDS:
        after = argv[lead.at + 1 :]
        skip = False
        for i, word in enumerate(after):
            if skip:
                skip = False
            elif word == "--":
                named.extend(after[i + 1 : i + 2])
                break
            elif word in ("--as", "--at"):
                skip = True
            elif word == "-" or not word.startswith("-"):
                named.append(word)
                break
    return named


def long_command(lead: Leading) -> tuple[str, ...] | None:
    """The command path of *lead* when its operation has no answer deadline, else ``None``."""
    for path, _ in LONG_COMMANDS:
        if tuple(lead.words[: len(path)]) == path:
            return path
    return None


def program_name() -> str:
    """The name this process was invoked as, which the usage text and the completion variable
    derive from, detected as the command-line library detects it."""
    main = sys.modules["__main__"]
    path = sys.argv[0]
    package = getattr(main, "__package__", None)
    if package in (None, "") or (
        os.name == "nt"
        and package == ""
        and not Path(path).exists()
        and Path(path + ".exe").exists()
    ):
        return Path(path).name
    assert package is not None
    module = package
    name = Path(path).stem
    if name != "__main__":
        module = f"{module}.{name}"
    return f"python -m {module.lstrip('.')}"


def _windows_console_setup() -> None:  # pragma: no cover
    """The command output has arrows and box-drawing characters a legacy Windows console cannot
    encode, so the streams are UTF-8 with replacement."""
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _windows_vt() -> bool | None:  # pragma: no cover
    """Whether the console has virtual-terminal processing on, as Rich reads it."""
    try:
        import ctypes

        kernel = ctypes.WinDLL("kernel32")  # pyright: ignore[reportAttributeAccessIssue,reportUnknownVariableType,reportUnknownMemberType]
        handle = kernel.GetStdHandle(-11)  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
        mode = ctypes.c_ulong()
        if not kernel.GetConsoleMode(handle, ctypes.byref(mode)):  # pyright: ignore[reportUnknownMemberType]
            return False
        return bool(mode.value & 0x0004)
    except AttributeError, OSError:
        return None


def _windows_truecolor(vt: bool | None) -> bool | None:  # pragma: no cover
    """Whether the console shows 24-bit colour, as Rich reads it: virtual-terminal processing on a
    Windows build new enough for it."""
    if vt is None:
        return None
    if not vt:
        return False
    version = sys.getwindowsversion()  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType,reportUnknownVariableType]
    return version.major > 10 or (version.major == 10 and version.build >= 15063)  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]


def _stream_facts(stream: Any) -> dict[str, Any]:
    try:
        tty = bool(stream.isatty())
    except AttributeError, ValueError:
        tty = False
    return {"tty": tty, "encoding": getattr(stream, "encoding", None) or "utf-8"}


def _terminal_size() -> list[int] | None:
    for fd in (1, 2) if sys.platform == "win32" else (0, 1, 2):
        try:
            size = os.get_terminal_size(fd)
        except OSError:
            continue
        return [size.columns, size.lines]
    return None


def terminal_facts() -> dict[str, Any]:
    """Whether each standard stream is a terminal and its encoding; the terminal's size; on
    Windows, whether the console has virtual-terminal processing."""
    vt = _windows_vt() if sys.platform == "win32" else None
    return {
        "stdin": _stream_facts(sys.stdin),
        "stdout": _stream_facts(sys.stdout),
        "stderr": _stream_facts(sys.stderr),
        "size": _terminal_size(),
        "windows_vt": vt,
        "windows_truecolor": _windows_truecolor(vt),
    }


def build_request(
    argv: list[str],
    *,
    cwd: str,
    client_dir: str,
    attachments: dict[str, str],
    terminal: dict[str, Any],
    environ: Mapping[str, str],
    prog_name: str,
) -> dict[str, Any]:
    """The first request that sends *argv*, with the fixed list of variables read from *environ*."""
    return {
        "argv": argv,
        "cwd": cwd,
        "client_dir": client_dir,
        "env": {name: environ[name] for name in SENT_ENVIRONMENT if name in environ},
        "prog_name": prog_name,
        "terminal": terminal,
        "attachments": attachments,
        "answers": [],
    }


class Unreadable(Exception):
    """A client file the command line names cannot be read."""


def read_attachments(names: list[str], client_dir: str) -> tuple[dict[str, str], bytes | None]:
    """Each of *names* as base64 of its bytes, and the bytes of stdin when ``-`` is among them.
    Raises :class:`Unreadable` for a file that cannot be read."""
    import base64

    attached: dict[str, str] = {}
    stdin: bytes | None = None
    # stdin last, so a file that cannot be read leaves it for the command that runs here
    for name in sorted(names, key=lambda name: name == "-"):
        if name in attached:
            continue
        if name == "-":
            stdin = _read_stdin()
            raw = stdin
        else:
            try:
                raw = Path(client_dir, name).read_bytes()
            except OSError as exc:
                raise Unreadable(name) from exc
        attached[name] = base64.b64encode(raw).decode("ascii")
    return attached, stdin


def _read_stdin() -> bytes:
    stream = sys.stdin
    buffer = getattr(stream, "buffer", None)
    try:
        return buffer.read() if buffer is not None else b""
    except OSError, ValueError:
        return b""


def _restore_stdin(raw: bytes) -> None:
    """Hand a command that runs here the stdin this process already read."""
    encoding = getattr(sys.stdin, "encoding", None) or "utf-8"
    sys.stdin = io.TextIOWrapper(io.BytesIO(raw), encoding=encoding)


class Unsent(Exception):
    """The request did not leave: nothing ran."""


class Lost(Exception):
    """The connection failed after the request was sent: the command may still have run."""


class Reply:
    """An HTTP answer: its status, the handler time the daemon reported and its body."""

    __slots__ = ("body", "handler_ms", "status")

    def __init__(self, status: int, handler_ms: float | None, body: bytes) -> None:
        self.status = status
        self.handler_ms = handler_ms
        self.body = body


def _address(endpoint: Endpoint) -> tuple[str, str]:
    """The Host header and the address (a socket path, or ``host:port``) of the CLI listener;
    raises :class:`Unsent` when there is none."""
    if endpoint.transport == "unix":
        return "localhost", str(endpoint.files.socket)
    record = read_record(endpoint)
    address = record.address("tcp", "cli") if record is not None else None
    if address is None:
        raise Unsent("no listener")
    return address, address


def _open(endpoint: Endpoint) -> tuple[socket.socket, str]:
    """A connection to the daemon's CLI listener, and the Host header to send on it. Over a port,
    which an unrelated process may have reused, the answerer must be the daemon the record names
    before anything is sent to it."""
    host, address = _address(endpoint)
    # asked on a connection of its own and before the one the command line travels on: a daemon
    # that answers one connection at a time would otherwise wait on the idle one for ever
    if endpoint.identity_check == "pid-and-path" and not _is_recorded_daemon(endpoint, host):
        raise Unsent("the listener is not the recorded daemon")
    try:
        if endpoint.transport == "unix":
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(CONNECT_TIMEOUT)
            try:
                sock.connect(address)
            except OSError:
                sock.close()
                raise
        else:
            name, _, port = address.rpartition(":")
            sock = socket.create_connection((name, int(port)), CONNECT_TIMEOUT)
    except (OSError, ValueError) as exc:
        raise Unsent(str(exc)) from exc
    return sock, host


def _is_recorded_daemon(endpoint: Endpoint, host: str) -> bool:
    """Whether the process answering on the recorded port is the daemon the record names, asked
    within :data:`CONNECT_TIMEOUT` seconds."""
    record = read_record(endpoint)
    name, _, port = host.rpartition(":")
    if record is None:
        return False
    try:
        with socket.create_connection((name, int(port)), CONNECT_TIMEOUT) as probe:
            _send(probe, host, "GET", "/v1/daemon", None)
            reply = _receive(probe, CONNECT_TIMEOUT, None)
        identity = json.loads(reply.body)
    except OSError, ValueError, Unsent, Lost:
        return False
    return (
        reply.status == 200
        and identity.get("pid") == record.pid
        and identity.get("squad_dir") == record.squad_dir
    )


def _recv(sock: socket.socket, wait: float | None, notice: Notice | None) -> bytes:
    """The next bytes of the answer; raises ``TimeoutError`` after *wait* seconds without any. A
    long command that has waited a while says so once."""
    if notice is not None:
        sock.settimeout(WAIT_NOTICE_AFTER)
        try:
            return _readable(sock, WAIT_NOTICE_AFTER)
        except TimeoutError:
            notice.say()
    sock.settimeout(wait)
    return _readable(sock, wait)


def _readable(sock: socket.socket, wait: float | None) -> bytes:
    if sys.platform != "win32":
        return sock.recv(65536)
    # A blocking read on Windows cannot be interrupted, so the wait is taken in short looks.
    import select

    deadline = None if wait is None else time.monotonic() + wait
    while True:
        ready, _, _ = select.select([sock], [], [], _POLL_SECONDS)
        if ready:
            return sock.recv(65536)
        if deadline is not None and time.monotonic() >= deadline:
            raise TimeoutError


class Notice:
    """The line a long command prints once it has waited."""

    def __init__(self, text: str) -> None:
        self._text = text
        self._said = False

    def say(self) -> None:
        if not self._said:
            self._said = True
            sys.stderr.write(self._text + "\n")
            sys.stderr.flush()


def _split_chunked(payload: bytes) -> bytes:
    out: list[bytes] = []
    while payload:
        size_line, _, rest = payload.partition(b"\r\n")
        size = int(size_line.split(b";", 1)[0], 16)
        if size == 0:
            break
        out.append(rest[:size])
        payload = rest[size + 2 :]
    return b"".join(out)


def _parse_reply(raw: bytes) -> Reply:
    head, separator, payload = raw.partition(b"\r\n\r\n")
    if not separator:
        raise Lost("truncated answer")
    lines = head.decode("latin-1").split("\r\n")
    try:
        status = int(lines[0].split(" ", 2)[1])
    except (IndexError, ValueError) as exc:
        raise Lost("malformed answer") from exc
    headers: dict[str, str] = {}
    for line in lines[1:]:
        name, _, value = line.partition(":")
        headers[name.strip().lower()] = value.strip()
    if "chunked" in headers.get("transfer-encoding", "").lower():
        try:
            payload = _split_chunked(payload)
        except ValueError as exc:
            raise Lost("malformed answer") from exc
    elif "content-length" in headers and len(payload) < int(headers["content-length"]):
        raise Lost("truncated answer")
    return Reply(status, _handler_ms(headers.get("server-timing")), payload)


def _handler_ms(header: str | None) -> float | None:
    """The handler time of a ``Server-Timing: handler;dur=<ms>`` header."""
    if header is None:
        return None
    for part in header.split(","):
        fields = part.strip().split(";")
        if fields[0] == "handler":
            for field in fields[1:]:
                if field.startswith("dur="):
                    try:
                        return float(field[4:])
                    except ValueError:
                        return None
    return None


def _send(sock: socket.socket, host: str, method: str, target: str, body: bytes | None) -> None:
    """Write one request to *sock*; raises :class:`Unsent` when it did not fully leave."""
    head = [f"{method} {target} HTTP/1.1", f"Host: {host}", "Squads-Client: 1"]
    if body is not None:
        head += ["Content-Type: application/json", f"Content-Length: {len(body)}"]
    head += ["Connection: close", "", ""]
    try:
        sock.sendall("\r\n".join(head).encode("latin-1") + (body or b""))
    except OSError as exc:
        raise Unsent(str(exc)) from exc


def _receive(sock: socket.socket, wait: float | None, notice: Notice | None) -> Reply:
    """The whole answer on *sock*. Raises :class:`Lost` when the connection fails, and
    ``TimeoutError`` when *wait* seconds pass without a byte."""
    chunks: list[bytes] = []
    try:
        while True:
            data = _recv(sock, wait, notice)
            if not data:
                break
            chunks.append(data)
    except TimeoutError:  # a subclass of OSError, told apart from a lost connection
        raise
    except OSError as exc:
        raise Lost(str(exc)) from exc
    return _parse_reply(b"".join(chunks))


def endpoint_name(endpoint: Endpoint) -> str:
    """How a message names the squad's endpoint."""
    if endpoint.transport == "unix":
        return str(endpoint.files.socket)
    record = read_record(endpoint)
    address = record.address("tcp", "cli") if record is not None else None
    return address or str(endpoint.files.info)


class Stdio:
    """Writes the answer's chunks to their streams in order, flushing a stream when the other
    takes over so a terminal shows what local mode shows."""

    def __init__(self) -> None:
        self._last: str | None = None

    def write(self, stream: str, text: str) -> None:
        if self._last is not None and self._last != stream:
            self.flush(self._last)
        self._last = stream
        target = sys.stdout if stream == "stdout" else sys.stderr
        try:
            target.write(text)
        except UnicodeEncodeError:
            encoding = getattr(target, "encoding", None) or "utf-8"
            target.flush()
            buffer = getattr(target, "buffer", None)
            if buffer is None:
                raise
            buffer.write(text.encode(encoding, "replace"))

    def flush(self, stream: str | None = None) -> None:
        for name in ("stdout", "stderr") if stream is None else (stream,):
            target = sys.stdout if name == "stdout" else sys.stderr
            with contextlib.suppress(ValueError):
                target.flush()


def _error_message(reply: Reply) -> str:
    """The message of an error answer, from its body when it has one."""
    try:
        message = json.loads(reply.body)["error"]["message"]
    except ValueError, KeyError, TypeError:
        return f"the daemon answered {reply.status}"
    return str(message)


def _retiring(reply: Reply) -> bool:
    if reply.status != 503:
        return False
    try:
        return json.loads(reply.body).get("not_executed") is not None
    except ValueError, AttributeError:
        return False


class Fallback(Exception):
    """The command is to run in this process: nothing has run on a daemon."""


class Retiring(Fallback):
    """The daemon answered that it is retiring and ran nothing."""


class Session:
    """One command line sent to the daemon: its request, its answers and its output."""

    def __init__(self, endpoint: Endpoint, request: dict[str, Any], long: tuple[str, ...] | None):
        self.endpoint = endpoint
        self.request = request
        self.long = long
        self.out = Stdio()
        self.handler_ms: float | None = None
        #: Whether the daemon has answered, so one that is gone afterwards is not one that was
        #: never started.
        self.answered = False
        #: Whether a request has left, so the command may have run.
        self.sent = False

    def _post(self) -> Reply:
        """One send of the request; raises :class:`Fallback` when it did not leave or the daemon
        was retiring."""
        body = json.dumps(self.request).encode("ascii")
        try:
            sock, host = _open(self.endpoint)
        except Unsent as exc:
            raise Fallback from exc
        wait = None if self.long is not None else ANSWER_TIMEOUT
        notice = (
            Notice(f"waiting for the daemon ({' '.join(self.long)})…")
            if self.long is not None
            else None
        )
        try:
            _send(sock, host, "POST", "/v1/commands", body)
            self.sent = True
            reply = _receive(sock, wait, notice)
        except Unsent as exc:
            raise Fallback from exc
        except TimeoutError as exc:
            seconds = ANSWER_TIMEOUT
            raise SendFailed(
                f"no answer from the squad served at {endpoint_name(self.endpoint)} after "
                f"{seconds:g} s; {_MAY_STILL_COMPLETE}"
            ) from exc
        except Lost as exc:
            raise SendFailed(
                f"the connection to the squad served at {endpoint_name(self.endpoint)} was lost "
                f"after the request was sent; {_MAY_STILL_COMPLETE}"
            ) from exc
        finally:
            sock.close()
        self.sent = False
        if _retiring(reply):
            raise Retiring
        return reply

    def run(self) -> int:
        """Send the request until the command is done, answering its prompts; return its exit
        code. Raises :class:`Fallback` when nothing has run on the daemon."""
        while True:
            reply = self._post()
            self.handler_ms = reply.handler_ms
            if reply.status != 200:
                self.out.flush()
                sys.stderr.write(f"error: {_error_message(reply)}\n")
                return 1
            try:
                answer = json.loads(reply.body)
            except ValueError as exc:
                raise SendFailed(
                    f"the squad served at {endpoint_name(self.endpoint)} sent an answer that is "
                    f"not valid JSON; {_MAY_STILL_COMPLETE}"
                ) from exc
            for stream, text in answer["output"]:
                self.out.write(stream, text)
            if answer["kind"] == "done":
                self.out.flush()
                return int(answer["exit_code"])
            self.answered = True
            self.out.write(answer["stream"], answer["text"])
            self.out.flush()
            line = _read_line()
            self.request["answers"].append({"digest": answer["digest"], "line": line})


class SendFailed(Exception):
    """The command was sent and its outcome is unknown; the message says so."""


def _read_line() -> str | None:
    """One line of stdin without its line end, or ``None`` at the end of input. Ctrl-C at the
    prompt aborts the command as the prompt does."""
    try:
        line = sys.stdin.readline()
    except KeyboardInterrupt:
        sys.stderr.write("\nAborted!\n")
        sys.stderr.flush()
        raise SystemExit(1) from None
    except OSError, ValueError:
        return None
    if not line:
        return None
    return line.removesuffix("\n").removesuffix("\r")


def _spans(t0: float, resolved: float, sent: float, done: float, handler: float | None) -> None:
    """Print the shim's own spans, and the daemon's handler time, as the CLI's spans print."""
    switch = os.environ.get("SQUADS_SPANS", "")
    if not switch:
        return
    origin = t0
    if switch.startswith("t="):
        with contextlib.suppress(ValueError):
            origin = float(switch[2:])
    lines = [
        ("shim_start", (t0 - origin) * 1000),
        ("shim_resolve", (resolved - t0) * 1000),
        ("shim_roundtrip", (done - sent) * 1000),
    ]
    if handler is not None:
        lines.append(("handler", handler))
    lines.append(("shim_end", (time.perf_counter() - origin) * 1000))
    sys.stderr.write("".join(f"SQUADS_SPAN {name} {ms:.2f}\n" for name, ms in lines))


def _say(line: str) -> None:
    sys.stderr.write(line + "\n")
    sys.stderr.flush()


def _start(endpoint: Endpoint) -> bool:
    """Have a daemon of *endpoint* serve, starting one if none does; the reason it could not be
    had is said on stderr."""
    from squads._daemon_start import ensure, failure_line

    reason = ensure(endpoint)
    if reason is None:
        return True
    _say(failure_line(reason))
    return False


class Plan:
    """A command line to send: where, what, and the stdin already read for it."""

    __slots__ = ("endpoint", "long", "request", "stdin")

    def __init__(
        self,
        endpoint: Endpoint,
        request: dict[str, Any],
        long: tuple[str, ...] | None,
        stdin: bytes | None,
    ) -> None:
        self.endpoint = endpoint
        self.request = request
        self.long = long
        self.stdin = stdin


def runs_here(lead: Leading) -> bool:
    """Whether the command line is for this machine's own process: a local-only command, or a
    root option that acts on the client's shell."""
    return bool(lead.words and lead.words[0] in LOCAL_ONLY) or bool(
        LOCAL_ROOT_OPTIONS.intersection(lead.options)
    )


def _endpoint_of(lead: Leading, cwd: str) -> tuple[Endpoint, str] | None:
    """The endpoint of the squad *lead*'s ``-C`` values reach from *cwd*, and the directory they
    resolve to; ``None`` when the command runs here: no squad, the daemon unusable (an unusable
    setting says so on stderr), or a ``-C`` that local mode will refuse itself."""
    try:
        client_dir = str(change_directory(Path(cwd), lead.dirs))
    except (ChangeDirError, OSError):  # fmt: skip
        return None
    endpoint = endpoint_for(Path(client_dir))
    if endpoint is None:
        return None
    if not endpoint.enabled:
        for problem in endpoint.problems:
            _say(f"warning: {problem}")
        return None
    return endpoint, client_dir


def plan(argv: list[str]) -> Plan | None:
    """What to send for *argv*, or ``None`` when it runs in this process: it is local-only,
    there is no squad or no usable daemon, or a file it names cannot be read."""
    lead = leading(argv)
    if runs_here(lead):
        return None
    cwd = str(Path.cwd())
    found = _endpoint_of(lead, cwd)
    if found is None:
        return None
    endpoint, client_dir = found
    if sys.platform == "win32":  # pragma: no cover
        _windows_console_setup()
    try:
        attachments, stdin = read_attachments(file_arguments(argv, lead), client_dir)
    except Unreadable:
        return None
    request = build_request(
        argv,
        cwd=cwd,
        client_dir=client_dir,
        attachments=attachments,
        terminal=terminal_facts(),
        environ=os.environ,
        prog_name=program_name(),
    )
    return Plan(endpoint, request, long_command(lead), stdin)


def serve(argv: list[str]) -> int | None:
    """The exit code of *argv* run by the squad's daemon, or ``None`` when it is to run in this
    process: see :func:`plan`, or nothing could be sent."""
    t0 = time.perf_counter()
    planned = plan(argv)
    if planned is None:
        return None
    endpoint = planned.endpoint
    session = Session(endpoint, planned.request, planned.long)
    resolved = time.perf_counter()
    try:
        code = _run(session, endpoint)
    except Fallback:
        if planned.stdin is not None:
            _restore_stdin(planned.stdin)
        return None
    except SendFailed as exc:
        session.out.flush()
        _say(f"error: {exc}")
        return 1
    except KeyboardInterrupt:
        session.out.flush()
        if session.sent:
            _say(
                f"error: no answer from the squad served at {endpoint_name(endpoint)}; "
                f"{_MAY_STILL_COMPLETE}"
            )
        return 130
    _spans(t0, resolved, resolved, time.perf_counter(), session.handler_ms)
    return code


def _run(session: Session, endpoint: Endpoint) -> int:
    """Run the session, starting the daemon once if the first send finds none."""
    try:
        return session.run()
    except Retiring:
        raise
    except Fallback:
        if session.answered or not _start(endpoint):
            raise
    return session.run()


def local() -> None:
    """Run the command in this process: the CLI itself."""
    from squads._cli import main as cli_main

    cli_main()


def main() -> None:
    """Console-script entry point."""
    gc.disable()  # the imports build a large, long-lived object graph that no collection frees
    argv = sys.argv[1:]
    if argv == ["--version"]:
        from rich.console import Console

        from squads import version_line

        Console().print(version_line())
        return
    try:
        code = serve(argv)
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        raise SystemExit(1) from None
    if code is None:
        local()
        return
    raise SystemExit(code)
