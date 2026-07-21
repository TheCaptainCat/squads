"""Single source of 'now'.

The frozen-time test fixture and the ``--at`` CLI option both freeze it for one
request via :func:`set_now`, so a migration (human- or LLM-driven) can forge historical
timestamps. The override lives in the ambient :class:`~squads._context.RequestContext`
(per request), not a module global — see :mod:`squads._context` for why.
"""

from datetime import UTC, datetime

from squads._context import get_context, rebind


def set_now(dt: datetime | None) -> None:
    """Force :func:`now` to return ``dt`` (or clear the override with ``None``)."""
    rebind(clock_override=dt)


def now() -> datetime:
    override = get_context().clock_override
    if override is not None:
        return override
    return datetime.now(UTC).replace(microsecond=0)


def iso(dt: datetime) -> str:
    """ISO 8601 with a trailing Z (UTC)."""
    dt = dt.astimezone(UTC).replace(microsecond=0)
    return dt.isoformat().replace("+00:00", "Z")


def parse_iso(value: str) -> datetime:
    """Parse an ISO-8601 date/datetime (``2024-01-15`` or ``2024-01-15T09:30:00Z``).

    A bare date becomes midnight; a naive value is assumed UTC. Raises ``ValueError`` on bad input.
    """
    dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).replace(microsecond=0)
