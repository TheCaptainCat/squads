"""Pins the exact badge glyph for every one of the 9 built-in sub-entity/finding statuses
(Todo/InProgress/Blocked/Done/Cancelled for subtask+story, Open/Fixed/Verified/WontFix for a
review finding) — the drift guard behind ``tests/_helpers.py::EXPECTED_BUILTIN_STATUS_BADGES``.
A change to any of these, or to the "InProgress" -> "In Progress" label-spacing rule, is a
display regression on the one surface that shows a badge at all (top-level item status is
always plain text, with no badge — a separate CLI-layer contract).
"""

import pytest

from _helpers import EXPECTED_BUILTIN_STATUS_BADGES
from squads import _badges as badges

_EXPECTED_TEXT: dict[str, str] = {
    "Todo": "⚪ Todo",
    "InProgress": "🟡 In Progress",
    "Blocked": "🔴 Blocked",
    "Done": "🟢 Done",
    "Cancelled": "⚫ Cancelled",
    "Open": "🔴 Open",
    "Fixed": "🟡 Fixed",
    "Verified": "🟢 Verified",
    "WontFix": "⚫ Wont Fix",
}


def test_the_badge_domain_is_exactly_the_nine_subentity_statuses() -> None:
    assert set(EXPECTED_BUILTIN_STATUS_BADGES) == set(_EXPECTED_TEXT), (
        "EXPECTED_BUILTIN_STATUS_BADGES's domain changed from the 9 known sub-entity statuses; "
        "extend _EXPECTED_TEXT deliberately if this is correct."
    )


@pytest.mark.parametrize("status_value", sorted(_EXPECTED_TEXT))
def test_status_badge_exact_text_for_every_builtin_subentity_status(status_value: str) -> None:
    assert badges.status_badge(status_value) == _EXPECTED_TEXT[status_value]
