"""Ambient per-invocation actor identity.

Like :mod:`squads._clock`, one ambient override set once at the CLI root callback (from
``--as``/``--author`` or the invoking agent's slug). It lives in the ambient
:class:`~squads._context.RequestContext`, not a module global (see :mod:`squads._context`), so
it never leaks between requests. Default: ``"system"``, when no human or agent set a slug.

Session lineage
---------------
An optional session pair is read once at the CLI root callback from ``SQUADS_SESSION_ID`` and
``SQUADS_PARENT_SESSION_ID`` and carried with the slug for the invocation.

It is best-effort, untrusted and observability-only. squads only reads whatever its
environment carries and records it; it does not mint, inject, spawn or verify, so a copied,
forged or absent id is indistinguishable from a real one. The pair is not tamper-evident or
signed and must never be an authorisation input; its value is forensic visibility of declared
lineage.
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


def session_from_env() -> tuple[str | None, str | None]:
    """Read the ``(session_id, parent_session_id)`` pair from the env vars (or ``(None, None)``).

    A pure lookup — shared by :func:`seed_session`'s ``from_env=True`` path and the CLI root
    callback, which folds the pair straight into its single ``RequestContext`` bind rather
    than seeding it via a separate rebind.
    """
    return (
        os.environ.get("SQUADS_SESSION_ID") or None,
        os.environ.get("SQUADS_PARENT_SESSION_ID") or None,
    )


def seed_session(
    session_id: str | None = None,
    parent_session_id: str | None = None,
    *,
    from_env: bool = False,
) -> None:
    """Seed the ambient session pair for this invocation.

    With ``from_env=True`` the values come from ``SQUADS_SESSION_ID``/
    ``SQUADS_PARENT_SESSION_ID``; otherwise the caller passes explicit ones (tests simulate env-set
    ids this way). ``--as``/``--author`` never set session fields; that path calls
    :func:`set_actor` only. Passing both as ``None`` (the default) clears the session state between
    invocations or tests.
    """
    if from_env:
        session_id, parent_session_id = session_from_env()
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
