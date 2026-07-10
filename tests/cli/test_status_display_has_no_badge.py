"""Top-level item status renders as a plain string, never a badge glyph, in either
human-facing (`sq show`, `sq list`) or machine-facing (`sq list --json`) output.

Badge resolution runs only for sub-entity "head" regions today — this pins the absence of
a *new* badge display surface on top-level status, so generalizing badge support elsewhere
cannot silently add one here.
"""

import json

import pytest

from _helpers import EXPECTED_BUILTIN_STATUS_BADGES

pytestmark = pytest.mark.anyio


async def test_show_panel_status_line_has_no_badge(project, invoke) -> None:
    await invoke(["create", "task", "Plain task", "--author", "manager"])
    r = await invoke(["task", "2", "show"])
    assert r.exit_code == 0, r.output
    assert "status: Draft" in r.output
    for emoji in EXPECTED_BUILTIN_STATUS_BADGES.values():
        assert emoji not in r.output


async def test_list_status_column_has_no_badge(project, invoke) -> None:
    await invoke(["create", "task", "Plain task", "--author", "manager"])
    r = await invoke(["list"])
    assert r.exit_code == 0, r.output
    assert "Draft" in r.output
    for emoji in EXPECTED_BUILTIN_STATUS_BADGES.values():
        assert emoji not in r.output


async def test_list_json_status_is_a_plain_string(project, invoke) -> None:
    await invoke(["create", "task", "Plain task", "--author", "manager"])
    r = await invoke(["list", "--json"])
    data = json.loads(r.output)
    by_id = {row["id"]: row for row in data}
    assert by_id["TASK-2"]["status"] == "Draft"
