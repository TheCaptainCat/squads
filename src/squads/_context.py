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

from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console

    from squads._api._api import Api

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
