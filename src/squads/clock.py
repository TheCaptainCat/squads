"""Single source of 'now' so tests can freeze time deterministically."""

from datetime import UTC, datetime


def now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def iso(dt: datetime) -> str:
    """ISO 8601 with a trailing Z (UTC)."""
    dt = dt.astimezone(UTC).replace(microsecond=0)
    return dt.isoformat().replace("+00:00", "Z")
