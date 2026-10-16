"""``sq operator list`` enumerates registered human operators (+ ``--json``) — CLI-only wiring
over the existing ``Service.list_operators``.
"""

import json

import pytest

pytestmark = pytest.mark.anyio


async def test_plain_output_lists_registered_operators(project, invoke) -> None:
    await invoke(["operator", "add", "Alice Tester"])
    r = await invoke(["operator", "list"])
    assert r.exit_code == 0, r.output
    assert "Alice Tester" in r.output
    assert "op-alice" in r.output


async def test_json_output_field_set_matches_operator_show(project, invoke) -> None:
    await invoke(["operator", "add", "Alice Tester"])
    listed = json.loads((await invoke(["operator", "list", "--json"])).output)
    assert len(listed) == 1
    row = listed[0]
    shown = json.loads((await invoke(["operator", "op-alice", "show", "--json"])).output)
    assert set(row) == {"id", "slug", "full_name", "status"}
    assert row["id"] == shown["id"]
    assert row["slug"] == shown["slug"] == "op-alice"
    assert row["full_name"] == shown["full_name"] == "Alice Tester"


async def test_empty_roster_lists_cleanly(project, invoke) -> None:
    r = await invoke(["operator", "list"])
    assert r.exit_code == 0, r.output
    assert json.loads((await invoke(["operator", "list", "--json"])).output) == []


async def test_no_operator_slug_can_collide_with_a_group_verb(project, invoke) -> None:
    refused = await invoke(["operator", "add", "List", "--slug", "list"])
    assert refused.exit_code == 1, refused.output

    added = await invoke(["operator", "add", "List"])
    assert added.exit_code == 0, added.output
    shown = await invoke(["operator", "op-list", "show"])
    assert shown.exit_code == 0 and "List" in shown.output
