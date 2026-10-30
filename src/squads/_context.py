"""Request-scoped ambient context: the one seam ambient values live in.

Triage rule for a module-level binding (the engine's static-state inventory proves against
it): DATA varies per request, per squad or per test (forged time, acting actor and session
lineage, the active spec and dir, the client cwd) and lives in ``RequestContext``, never a
module global; CODE is an immutable definition loaded once and safe to share (the bundled
workflow spec, the role catalog, backend classes, compiled template environments) and may stay
module-level and be cached process-wide.

It is one task-local value, seeded or rebound only at the CLI edge and read only through the
accessors below; nothing below ``compose_service`` reads the ``ContextVar`` directly. New ambient
fields are added with a default, so existing call sites and fields are untouched.
"""

import hashlib
from collections.abc import Awaitable, Callable, Mapping
from contextvars import ContextVar
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rich.console import Console

    from squads._api._api import Api
    from squads._parse_cache import ParseCache

    # _context sits below _clock/_actor; _workflow._models and _spec_documents sit above them,
    # and a runtime import here would cycle back to this module mid-init, so they are type-only.
    from squads._spec_documents import SpecDocuments
    from squads._workflow._models import WorkflowSpec


class NoticeLog:
    """The notices the engine raised during one request, in order, and the sink that shows each
    one as it is raised (the CLI's notice printer; the daemon sets none)."""

    def __init__(self, sink: Callable[[str], None] | None = None) -> None:
        self._notices: list[str] = []
        self._sink = sink

    def record(self, text: str) -> None:
        """Keep *text*, and hand it to the sink when there is one."""
        self._notices.append(text)
        if self._sink is not None:
            self._sink(text)

    @property
    def notices(self) -> tuple[str, ...]:
        """Every notice recorded so far."""
        return tuple(self._notices)


def etag_of(text: str) -> str:
    """The strong ETag of an item file's *text*: the SHA-256 of its UTF-8 bytes with every line end
    a line feed, in quotes."""
    data = text.replace("\r\n", "\n").encode("utf-8")
    return f'"{hashlib.sha256(data).hexdigest()}"'


#: Reads the addressed item's file text as a ``SquadsDB`` (the transaction's, when one is open)
#: places it: the item's id and its text, ``None`` when the item or its file is gone.
type AddressedReader = Callable[[Any], Awaitable[tuple[str, str | None]]]


def if_match_allows(header: str, etag: str | None) -> bool:
    """Whether an ``If-Match`` *header* admits an item whose ETag is *etag* (``None`` when it is
    gone): ``*`` admits any item that exists, and a list of strong tags admits its members."""
    if etag is None:
        return False
    tags = [tag.strip() for tag in header.split(",")]
    return "*" in tags or etag in tags


class Preconditions:
    """The conditional-request state of one request: the ETag its ``If-Match`` names, how to read
    the item it addresses, and the ETag that item has when the operation is done."""

    def __init__(self, if_match: str | None = None) -> None:
        self.if_match = if_match
        #: The ETag of the addressed item once an operation read or wrote it.
        self.etag: str | None = None
        #: How to read the addressed item, set by the operation as it resolves the address.
        self.reader: AddressedReader | None = None
        #: The sequence number of the addressed item.
        self.sequence: int | None = None
        #: Whether the ``If-Match`` has been compared; it is compared once, in the first
        #: transaction that opens after the address is known.
        self.compared = False

    def address(self, sequence: int, reader: AddressedReader, *, replace: bool = False) -> None:
        """Make the item numbered *sequence*, read by *reader*, the addressed one, unless one is
        already set and *replace* is not."""
        if self.reader is None or replace:
            self.sequence = sequence
            self.reader = reader

    def note_read(self, sequence: int, text: str) -> None:
        """Take the ETag of the addressed item from *text* it was read as, unless one is already
        known: the first read of a request is the one its answer is built from."""
        if sequence == self.sequence and self.etag is None:
            self.etag = etag_of(text)


@dataclass(frozen=True)
class ServedCommand:
    """What a command the daemon runs takes from its request in place of the client's machine."""

    #: The bytes of each client file the command line names, by the argument as written.
    attachments: Mapping[str, bytes]
    stdin_encoding: str
    columns: int | None
    lines: int | None
    #: Whether a Windows client's console has virtual-terminal processing; ``None`` elsewhere.
    windows_vt: bool | None
    #: Marks that the output so far is what the user has seen and the next write is the prompt.
    begin_prompt: Callable[[], None]


@dataclass(frozen=True)
class RequestContext:
    """The ambient values for one request/invocation. Every field defaults to "unset"."""

    clock_override: datetime | None = None
    actor_override: str | None = None
    session_id: str | None = None
    parent_session_id: str | None = None
    active_spec: WorkflowSpec | None = None
    client_cwd: Path | None = None
    #: Whether the caller chose the working directory with ``-C`` (names it in errors).
    client_cwd_chosen: bool = False

    #: The refusal text when the squad's workflow override exists but failed to resolve; ``None``
    #: outside a squad or with no override. Its presence turns every spec-consuming surface into
    #: a refusal, since a spec that failed to load has no honest bundled substitute.
    spec_error: str | None = None

    #: The directory a request starts from; ``None`` means the process directory.
    start_dir: Path | None = None
    #: The spec documents a long-lived process loaded once.
    documents: SpecDocuments | None = None
    #: The stdout and stderr consoles built for this invocation, in that order.
    consoles: tuple[Console, Console] | None = None
    #: The API this invocation's commands call.
    api: Api | None = None
    #: The notices raised while the request's operation runs; ``LocalApi`` adds them to the
    #: response's ``warnings``.
    notices: NoticeLog | None = None
    #: The ``If-Match`` a write compares and the ETag it leaves; ``None`` outside a daemon request.
    preconditions: Preconditions | None = None
    #: The daemon's cache of parsed files; ``None`` in every other process.
    parse_cache: ParseCache | None = None

    #: Set on a command the daemon runs for its client; ``None`` for a command run by this
    #: process for itself.
    served: ServedCommand | None = None


_DEFAULT_CONTEXT = RequestContext()

_context_var: ContextVar[RequestContext] = ContextVar("_context", default=_DEFAULT_CONTEXT)


def bind_context(ctx: RequestContext) -> None:
    """Bind *ctx* as the ambient context for the current task/thread."""
    _context_var.set(ctx)


def get_context() -> RequestContext:
    """Return the ambient context for the current task/thread (the default when unset)."""
    return _context_var.get()


def record_notice(text: str) -> None:
    """Record *text* as a notice of the request now running; nothing below the CLI writes to the
    process's streams. A request with no log drops it."""
    log = get_context().notices
    if log is not None:
        log.record(text)


def rebind(**changes: object) -> RequestContext:
    """Replace one or more fields of the current context in place; return the new context.

    Used by the small per-field setters (``clock.set_now``, ``actor.set_actor``, …) so each
    keeps rebinding just its own field without every caller needing ``dataclasses.replace``.
    """
    new_ctx = replace(get_context(), **changes)  # pyright: ignore[reportArgumentType]
    bind_context(new_ctx)
    return new_ctx
