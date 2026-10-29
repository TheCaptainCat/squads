"""Request-scoped ambient context: the one seam ambient values live in.

Triage rule for a module-level binding (the engine's static-state inventory proves against
it): DATA varies per request, per squad or per test (forged time, acting actor and session
lineage, the active spec and dir, the client cwd) and lives in ``RequestContext``, never a
module global; CODE is an immutable definition loaded once and safe to share (the bundled
workflow spec, the role catalog, backend classes, compiled template environments) and may stay
module-level and be cached process-wide.

It is one task-local value, seeded or rebound only at the CLI edge and read only through the
accessors below; nothing below ``open_service`` reads the ``ContextVar`` directly. New ambient
fields are added with a default, so existing call sites and fields are untouched.
"""

from collections.abc import Mapping
from contextvars import ContextVar
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console

    # _context sits below _clock/_actor; _workflow._models and _spec_documents sit above them,
    # and a runtime import here would cycle back to this module mid-init, so they are type-only.
    from squads._spec_documents import SpecDocuments
    from squads._workflow._models import WorkflowSpec


@dataclass(frozen=True)
class TerminalFacts:
    """What the client's terminal looks like: which standard streams are terminals, and its size."""

    stdin_tty: bool = False
    stdout_tty: bool = False
    stderr_tty: bool = False
    columns: int | None = None
    lines: int | None = None


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
    #: The files a request carries, by the name the command line gives them (``-`` is stdin);
    #: ``None`` means files are read from the filesystem and stdin from the process.
    attachments: Mapping[str, bytes] | None = None
    #: The client's terminal; ``None`` outside a served request.
    terminal: TerminalFacts | None = None
    #: The spec documents a long-lived process loaded once.
    documents: SpecDocuments | None = None
    #: The stdout and stderr consoles built for this invocation, in that order.
    consoles: tuple[Console, Console] | None = None


_DEFAULT_CONTEXT = RequestContext()

_context_var: ContextVar[RequestContext] = ContextVar("_context", default=_DEFAULT_CONTEXT)


def bind_context(ctx: RequestContext) -> None:
    """Bind *ctx* as the ambient context for the current task/thread."""
    _context_var.set(ctx)


def get_context() -> RequestContext:
    """Return the ambient context for the current task/thread (the default when unset)."""
    return _context_var.get()


def rebind(**changes: object) -> RequestContext:
    """Replace one or more fields of the current context in place; return the new context.

    Used by the small per-field setters (``clock.set_now``, ``actor.set_actor``, …) so each
    keeps rebinding just its own field without every caller needing ``dataclasses.replace``.
    """
    new_ctx = replace(get_context(), **changes)  # pyright: ignore[reportArgumentType]
    bind_context(new_ctx)
    return new_ctx
