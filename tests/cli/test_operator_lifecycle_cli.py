"""``sq operator add`` / ``sq list -t operator`` / ``sq operator <slug> show`` end to end,
plus assigning a task to a registered human operator through the ordinary update surface.
"""

import json

import pytest

pytestmark = pytest.mark.anyio


async def test_add_list_show_and_assign_an_operator(project, invoke):
    added = await invoke(["operator", "add", "Pierre Chat"])
    assert added.exit_code == 0 and "op-pierre" in added.output

    listed = await invoke(["list", "-t", "operator"])
    assert "Pierre Chat" in listed.output

    shown = await invoke(["operator", "op-pierre", "show"])
    assert shown.exit_code == 0 and "Pierre Chat" in shown.output

    await invoke(["create", "task", "Manual step", "--author", "manager"])
    updated = await invoke(["task", "3", "update", "--assignee", "op-pierre"])
    assert updated.exit_code == 0

    result = await invoke(["task", "3", "show", "--json"])
    assert json.loads(result.output)["assignee"] == "op-pierre"
