"""Thin CLI smoke for the three read-only views: ``sq blocked`` names the blocker, ``sq workload``
counts open work per assignee (human and ``--json``), and ``sq search`` finds a matching item.
"""

import json

import pytest

pytestmark = pytest.mark.anyio


async def test_blocked_cli_names_the_blocked_item_and_its_blocker(project, invoke):
    await invoke(["create", "task", "A", "--author", "manager", "--assignee", "manager"])
    await invoke(["create", "task", "B", "--author", "manager"])
    await invoke(["task", "3", "ref", "add", "TASK-000002", "--kind", "blocks"])

    result = await invoke(["blocked"])
    assert result.exit_code == 0
    assert "TASK-2" in result.output and "blocked by" in result.output


async def test_workload_cli_json_counts_open_items_per_assignee(project, invoke):
    await invoke(["create", "task", "A", "--author", "manager", "--assignee", "manager"])
    await invoke(["create", "task", "B", "--author", "manager"])

    result = await invoke(["workload", "--json"])
    assert result.exit_code == 0
    rows = {r["assignee"]: r for r in json.loads(result.output)}
    assert rows["manager"]["open"] == 1


async def test_search_cli_finds_a_matching_item_and_json_matches_human_output(project, invoke):
    await invoke(["create", "task", "Token validation", "--author", "manager"])

    human = await invoke(["search", "token"])
    assert human.exit_code == 0 and "TASK-2" in human.output

    as_json = await invoke(["search", "token", "--json"])
    assert json.loads(as_json.output)[0]["id"] == "TASK-2"
