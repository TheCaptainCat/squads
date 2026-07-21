"""Ambient per-invocation actor identity.

Mirrors :mod:`squads._clock`: one ambient override, set once at the CLI root
callback (from ``--as`` / ``--author`` or the invoking agent's slug). The
override lives in the ambient :class:`~squads._context.RequestContext` (per
request), not a module global — see :mod:`squads._context` for why — so it
never leaks between requests without needing a ``try/finally``.

Default: ``"system"`` — the machine itself, when no human or agent set a slug.

Session lineage
---------------
An optional session pair is read **once** at the CLI root callback from two
environment variables, ``SQUADS_SESSION_ID`` and ``SQUADS_PARENT_SESSION_ID``,
and carried alongside the slug for the duration of the invocation.

**Guarantee: best-effort, untrusted, observability-only.**  squads is a passive
tool, never in the spawn path.  It only *reads* whatever its own invocation
environment happens to carry and *records* it.  It does not mint, inject,
spawn, or verify.  A copied, forged, or absent session id is indistinguishable
from a real one.  The recorded session pair is **not tamper-evident**, **not
signed**, and must never be used as an authorisation input.  Its sole value is
forensic visibility of declared lineage.
"""

import os

from squads._context import get_context, rebind


def set_actor(slug: str | None) -> None:
    """Force :func:`current_actor` to return *slug*, or clear the override with ``None``."""
    rebind(actor_override=slug)


def current_actor() -> str:
    """Return the ambient actor slug for this invocation (default: ``"system"``)."""
    override = get_context().actor_override
    if override is not None:
        return override
    return "system"


def seed_session(
    session_id: str | None = None,
    parent_session_id: str | None = None,
    *,
    from_env: bool = False,
) -> None:
    """Seed the ambient session pair for this invocation.

    Called **once** from the CLI root callback (``main_callback``).  With
    ``from_env=True`` the values are read from ``SQUADS_SESSION_ID`` /
    ``SQUADS_PARENT_SESSION_ID``; otherwise the caller may pass explicit values
    (used in tests to simulate env-set ids without actually setting env vars).

    Session fields are **not** settable by ``--as`` / ``--author`` or any later
    CLI flag — that slug-override path calls :func:`set_actor` only.

    Pass both arguments as ``None`` (the default) to clear the session state
    between invocations / tests.
    """
    if from_env:
        session_id = os.environ.get("SQUADS_SESSION_ID") or None
        parent_session_id = os.environ.get("SQUADS_PARENT_SESSION_ID") or None
    else:
        session_id = session_id or None
        parent_session_id = parent_session_id or None
    rebind(session_id=session_id, parent_session_id=parent_session_id)


def current_session() -> tuple[str | None, str | None]:
    """Return the ambient ``(session_id, parent_session_id)`` pair.

    Both fields are ``None`` when no session env vars were present — the common
    case when no orchestrator skill has been written to propagate them.

    **Untrusted / best-effort:** these values are self-declarations from the
    invocation environment; squads cannot verify them.
    """
    ctx = get_context()
    return ctx.session_id, ctx.parent_session_id
