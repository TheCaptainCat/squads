"""Request-scoped ambient context: the one seam ambient values live in.

**Triage rule** (the durable classification the engine's static-state inventory proves
against, generalizing the workflow-spec threading decision to every ambient value): a
module-level binding is

- **DATA** — its value varies per request, per squad, or per test (forged time, acting
  actor + session lineage, the active spec/dir, the client cwd) — it must live here, in
  ``RequestContext``, never in a module global.
- **CODE/definition** — an immutable spec, class, or definition loaded once and safe to
  share across every request (the bundled workflow spec, the role catalog, backend
  classes, compiled template environments) — it may stay module-level, and caching it
  process-wide is fine.

Mirrors the ``_rendering/_engine.py::_active_squad_dir`` ``ContextVar`` precedent: one
task-local value, seeded/rebound only at the CLI edge (or a future server handler) and
read only through the accessor functions below — nothing below ``open_service`` reads
the ``ContextVar`` directly.

Additive by design: new ambient fields (the active spec/dir, the client cwd, …) are
added to ``RequestContext`` with a default, so adding one never touches existing call
sites or existing fields.
"""

from contextvars import ContextVar
from dataclasses import dataclass, replace
from datetime import datetime


@dataclass(frozen=True)
class RequestContext:
    """The ambient values for one request/invocation. Every field defaults to "unset"."""

    clock_override: datetime | None = None
    actor_override: str | None = None
    session_id: str | None = None
    parent_session_id: str | None = None


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
