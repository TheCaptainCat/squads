"""`_clock.set_now`/`now`/`parse_iso`: the process-global override the `frozen_time` fixture
and the CLI's `--at` flag both ride on. Setting a forged time makes `now()` return it until
explicitly cleared, and `parse_iso` accepts a bare date or a full ISO-8601 timestamp while
rejecting nonsense.
"""

from datetime import UTC, datetime

import pytest

from squads import _clock as clock


def test_set_now_overrides_now_until_explicitly_cleared() -> None:
    forged = datetime(2020, 1, 2, 3, 4, 5, tzinfo=UTC)
    clock.set_now(forged)
    assert clock.now() == forged
    clock.set_now(None)
    assert clock.now() != forged


def test_parse_iso_accepts_a_bare_date_and_a_full_timestamp_but_rejects_nonsense() -> None:
    assert clock.parse_iso("2024-01-15") == datetime(2024, 1, 15, tzinfo=UTC)
    assert clock.parse_iso("2024-01-15T09:30:00Z") == datetime(2024, 1, 15, 9, 30, tzinfo=UTC)
    with pytest.raises(ValueError):
        clock.parse_iso("not-a-date")
