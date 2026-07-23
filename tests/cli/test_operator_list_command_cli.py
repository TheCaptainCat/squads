"""``sq operator list`` enumerates registered human operators (+ ``--json``) — CLI-only wiring
over the existing ``Service.list_operators``.
"""

import json

import pytest

pytestmark = pytest.mark.anyio


async def test_plain_output_lists_registered_operators(project, invoke) -> None:
    await invoke(["operator", "add", "Pierre Chat"])
    r = await invoke(["operator", "list"])
    assert r.exit_code == 0, r.output
    assert "Pierre Chat" in r.output
    assert "op-pierre" in r.output


async def test_json_output_field_set_matches_operator_show(project, invoke) -> None:
    await invoke(["operator", "add", "Pierre Chat"])
    listed = json.loads((await invoke(["operator", "list", "--json"])).output)
    assert len(listed) == 1
    row = listed[0]
    shown = json.loads((await invoke(["operator", "op-pierre", "show", "--json"])).output)
    assert set(row) == {"id", "slug", "full_name", "status"}
    assert row["id"] == shown["id"]
    assert row["slug"] == shown["slug"] == "op-pierre"
    assert row["full_name"] == shown["full_name"] == "Pierre Chat"


async def test_empty_roster_lists_cleanly(project, invoke) -> None:
    r = await invoke(["operator", "list"])
    assert r.exit_code == 0, r.output
    assert json.loads((await invoke(["operator", "list", "--json"])).output) == []


async def test_a_slug_literally_list_is_unaddressable_by_slug(project, invoke) -> None:
    added = await invoke(["operator", "add", "List", "--slug", "list"])
    assert added.exit_code == 0, added.output

    # `sq operator list` dispatches to the group verb (the listing), not `show` on the
    # operator whose slug happens to be "list" — addressing that operator needs its full ID.
    listing = await invoke(["operator", "list"])
    assert listing.exit_code == 0
    assert "List" in listing.output

    shown = await invoke(["operator", "OP-000002", "show"])
    assert shown.exit_code == 0
    assert "List" in shown.output
