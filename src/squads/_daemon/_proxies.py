"""The process-wide proxies a served command runs behind.

``sys.stdout``, ``sys.stderr``, ``sys.stdin`` and ``os.environ`` are replaced once by objects that
resolve, per call, to the request running on the calling thread, and are what they replaced
outside one.
"""

import codecs
import collections.abc
import contextvars
import hashlib
import io
import json
import os
import sys
from dataclasses import dataclass
from typing import TextIO

from rich.console import Console

from squads._shim import SENT_ENVIRONMENT

STDOUT = "stdout"
STDERR = "stderr"
STDIN = "stdin"

#: One piece of output: the stream it was written to and its text.
type Chunk = tuple[str, str]

SENT = frozenset(SENT_ENVIRONMENT)


@dataclass(frozen=True)
class Answer:
    """The reply to a prompt: the digest of the screen it was given on and the line, ``None`` for
    end of input."""

    digest: str
    line: str | None


class PromptRequired(BaseException):
    """A served command reached a prompt with no answer. It is a ``BaseException`` so that no
    handler of the command swallows it."""

    def __init__(self, before: list[Chunk], stream: str, text: str, digest: str) -> None:
        super().__init__(text)
        self.before = before
        self.stream = stream
        self.text = text
        self.digest = digest


class Capture:
    """What one served command writes, in order, and the answers it may read.

    A prompt is the writes between :meth:`begin_prompt`, or the previous answer, and the next read
    of stdin; the command stops at a read whose screen has no answer.
    """

    def __init__(
        self,
        env: collections.abc.Mapping[str, str],
        ttys: collections.abc.Mapping[str, bool],
        encodings: collections.abc.Mapping[str, str],
        answers: list[Answer],
    ) -> None:
        self.env = env
        self._ttys = ttys
        self._encodings = encodings
        self._answers = answers
        self._chunks: list[list[str]] = []
        self._decoders: dict[str, codecs.IncrementalDecoder] = {}
        #: Index of the chunk that starts the prompt being asked, ``None`` when none is.
        self._mark: int | None = None
        #: The digest of the last prompt answered, which every later digest builds on.
        self._chain = ""

    def tty(self, stream: str) -> bool:
        return self._ttys.get(stream, False)

    def encoding(self, stream: str) -> str:
        return self._encodings.get(stream, "utf-8")

    def write(self, stream: str, text: str) -> None:
        """Append *text*, joining it to the chunk before it when that went to the same stream and
        no prompt starts here."""
        if not text:
            return
        last = self._chunks[-1] if self._chunks else None
        if last is not None and last[0] == stream and self._mark != len(self._chunks):
            last[1] += text
        else:
            self._chunks.append([stream, text])

    def write_bytes(self, stream: str, data: bytes) -> None:
        """Append *data* as *stream*'s encoding reads it, a character split across two writes
        joined."""
        decoder = self._decoders.get(stream)
        if decoder is None:
            decoder = codecs.getincrementaldecoder(self.encoding(stream))(errors="replace")
            self._decoders[stream] = decoder
        self.write(stream, decoder.decode(data))

    def chunks(self) -> list[Chunk]:
        """Everything written and not yet shown to the user."""
        return [(stream, text) for stream, text in self._chunks]

    def begin_prompt(self) -> None:
        """The next write is a prompt's text."""
        self._mark = len(self._chunks)

    def _digest(self, before: list[Chunk], stream: str, text: str) -> str:
        screen = json.dumps([self._chain, before, stream, text])
        return hashlib.blake2b(screen.encode("ascii"), digest_size=16).hexdigest()

    def read_line(self) -> str:
        """The next line of stdin: the answer given to the prompt just asked, or end of input when
        no prompt is. A prompt with no answer for its screen stops the command."""
        if self._mark is None:
            return ""
        shown = self.chunks()
        before, asked = shown[: self._mark], shown[self._mark :]
        stream = asked[0][0] if asked else STDOUT
        text = "".join(piece for _, piece in asked)
        digest = self._digest(before, stream, text)
        for answer in self._answers:
            if answer.digest == digest:
                self._chain = digest
                self._chunks.clear()
                # What the command writes next is shown before it reads again, so a read that
                # follows is a prompt too: Click asks again after a line that is not an answer.
                self._mark = 0
                return "" if answer.line is None else answer.line + "\n"
        raise PromptRequired(before, stream, text, digest)


#: The request running on the calling thread; ``None`` outside one.
CURRENT: contextvars.ContextVar[Capture | None] = contextvars.ContextVar(
    "served_capture", default=None
)


class StandardStream(io.TextIOBase):
    """A standard stream: the request's capture while one runs, the stream it replaced otherwise.
    It also takes ``bytes``, which Click and Typer write on the completion path."""

    def __init__(self, name: str, fallback: TextIO) -> None:
        self._name = name
        self._fallback = fallback

    @property
    def encoding(self) -> str:  # pyright: ignore[reportIncompatibleVariableOverride]
        capture = CURRENT.get()
        return self._fallback.encoding if capture is None else capture.encoding(self._name)

    @property
    def errors(self) -> str:  # pyright: ignore[reportIncompatibleVariableOverride]
        capture = CURRENT.get()
        return (self._fallback.errors or "strict") if capture is None else "strict"

    def writable(self) -> bool:
        return self._name != STDIN

    def readable(self) -> bool:
        return self._name == STDIN

    def isatty(self) -> bool:
        capture = CURRENT.get()
        return self._fallback.isatty() if capture is None else capture.tty(self._name)

    def fileno(self) -> int:
        if CURRENT.get() is None:
            return self._fallback.fileno()
        return super().fileno()

    def flush(self) -> None:
        if CURRENT.get() is None and self.writable():
            self._fallback.flush()

    def close(self) -> None:
        """A standard stream is not the proxy's to close."""

    def write(self, s: str | bytes | bytearray) -> int:  # pyright: ignore[reportIncompatibleMethodOverride]
        capture = CURRENT.get()
        if capture is None:
            if isinstance(s, str):
                return self._fallback.write(s)
            return self._fallback.buffer.write(s)
        if isinstance(s, str):
            capture.write(self._name, s)
        else:
            capture.write_bytes(self._name, bytes(s))
        return len(s)

    def read(self, size: int | None = -1) -> str:
        capture = CURRENT.get()
        return self._fallback.read(size or -1) if capture is None else ""

    def readline(self, size: int | None = -1) -> str:
        capture = CURRENT.get()
        if capture is None:
            return self._fallback.readline(size or -1)
        return capture.read_line()


class Environment(collections.abc.MutableMapping[str, str]):
    """``os.environ`` for a served command: a name of the fixed list reads the request's ``env``,
    any other name the daemon's own."""

    def __init__(self, real: collections.abc.MutableMapping[str, str]) -> None:
        self._real = real

    def __getitem__(self, key: str) -> str:
        capture = CURRENT.get()
        if capture is not None and key in SENT:
            return capture.env[key]
        return self._real[key]

    def __setitem__(self, key: str, value: str) -> None:
        self._real[key] = value

    def __delitem__(self, key: str) -> None:
        del self._real[key]

    def __iter__(self) -> collections.abc.Iterator[str]:
        capture = CURRENT.get()
        if capture is None:
            return iter(self._real)
        kept = (name for name in self._real if name not in SENT)
        return iter([*kept, *capture.env])

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def copy(self) -> dict[str, str]:
        return dict(self)


def install() -> None:
    """Replace the standard streams and ``os.environ`` by proxies, those that are not already.

    A harness that shares its process with a test runner calls it before each request, because
    the runner puts its own streams back between tests.
    """
    if not isinstance(sys.stdout, StandardStream):
        sys.stdout = StandardStream(STDOUT, sys.stdout)
    if not isinstance(sys.stderr, StandardStream):
        sys.stderr = StandardStream(STDERR, sys.stderr)
    if not isinstance(sys.stdin, StandardStream):
        sys.stdin = StandardStream(STDIN, sys.stdin)
    if not isinstance(os.environ, Environment):
        os.environ = Environment(os.environ)  # noqa: B003  # pyright: ignore[reportAttributeAccessIssue]
        # Rich binds the process environment when it is imported, which is the one replaced here.
        Console._environ = os.environ  # pyright: ignore[reportPrivateUsage]
