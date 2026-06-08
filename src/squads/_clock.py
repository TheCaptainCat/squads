"""Single source of 'now'.

Tests freeze it by monkeypatching ``now``. The ``--at`` CLI option freezes it for one invocation
via :func:`set_now`, so a migration (human- or LLM-driven) can forge historical timestamps.
"""

from datetime import UTC, datetime

_override: datetime | None = None


def set_now(dt: datetime | None) -> None:
    """Force :func:`now` to return ``dt`` (or clear the override with ``None``)."""
    global _override
    _override = dt


def now() -> datetime:
    if _override is not None:
        return _override
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
