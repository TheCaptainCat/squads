"""Shared test-only constants and helpers with no production analogue.

Kept separate from `conftest.py` (fixtures/autouse hooks) since these are plain importable
values, not pytest fixtures.
"""

#: The exact badge glyph for each of the 9 built-in sub-entity statuses (subtask/story:
#: Todo/InProgress/Blocked/Done/Cancelled; review finding: Open/Fixed/Verified/WontFix).
#:
#: This is the test-layer's own golden reference — it has no production counterpart. Production
#: badge resolution is spec-driven (`WorkflowSpec.status_badge`, backed by the workflow TOML's
#: per-status `badge` field), which also covers custom statuses with a graceful default. This
#: dict exists purely so tests can pin the 9 built-in glyphs and catch accidental drift in the
#: spec's declared badges; update it deliberately if a built-in badge is ever meant to change.
EXPECTED_BUILTIN_STATUS_BADGES: dict[str, str] = {
    "Todo": "⚪",
    "InProgress": "🟡",
    "Blocked": "🔴",
    "Done": "🟢",
    "Cancelled": "⚫",
    "Open": "🔴",
    "Fixed": "🟡",
    "Verified": "🟢",
    "WontFix": "⚫",
}
