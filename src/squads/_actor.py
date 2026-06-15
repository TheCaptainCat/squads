"""Ambient per-invocation actor identity.

Mirrors :mod:`squads._clock`: one module-global override, set once at the CLI
root callback (from ``--as`` / ``--author`` or the invoking agent's slug) and
cleared by a ``try/finally`` so it never leaks between invocations or tests.

Default: ``"system"`` — the machine itself, when no human or agent set a slug.
"""

_override: str | None = None


def set_actor(slug: str | None) -> None:
    """Force :func:`current_actor` to return *slug*, or clear the override with ``None``."""
    global _override
    _override = slug


def current_actor() -> str:
    """Return the ambient actor slug for this invocation (default: ``"system"``)."""
    if _override is not None:
        return _override
    return "system"
