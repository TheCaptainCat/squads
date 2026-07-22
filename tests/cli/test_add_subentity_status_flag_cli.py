"""``add-<kind>`` (add-story / add-subtask / add-finding) exposes ``--status`` inline, generated
uniformly by the shared add builder alongside the existing per-field flags. Additive: omitting
the flag behaves exactly as before, and an out-of-lifecycle value is refused cleanly (no
traceback), scoped to the kind's own machine rather than the spec's whole status vocabulary.
"""

import json

import pytest

pytestmark = pytest.mark.anyio


async def test_add_story_status_flag_seeds_a_non_initial_status(project, invoke) -> None:
    await invoke(["create", "feature", "F", "--author", "manager"])
    r = await invoke(["feature", "2", "add-story", "Reset password", "--status", "InProgress"])
    assert r.exit_code == 0, r.output

    listed = json.loads((await invoke(["feature", "2", "stories", "--json"])).output)
    assert listed[0]["status"] == "InProgress"


async def test_add_subtask_status_flag_seeds_a_non_initial_status(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    r = await invoke(["task", "2", "add-subtask", "Wire API", "--status", "Blocked"])
    assert r.exit_code == 0, r.output

    listed = json.loads((await invoke(["task", "2", "subtasks", "--json"])).output)
    assert listed[0]["status"] == "Blocked"


async def test_add_finding_status_flag_seeds_a_non_initial_status_alongside_severity(
    project, invoke
) -> None:
    await invoke(["create", "review", "R", "--author", "manager"])
    r = await invoke(
        ["review", "2", "add-finding", "Off-by-one", "--severity", "low", "--status", "Fixed"]
    )
    assert r.exit_code == 0, r.output

    listed = json.loads((await invoke(["review", "2", "findings", "--json"])).output)
    assert listed[0]["status"] == "Fixed"
    assert listed[0]["severity"] == "low"


async def test_add_finding_without_status_still_seeds_the_initial_status(project, invoke) -> None:
    await invoke(["create", "review", "R", "--author", "manager"])
    r = await invoke(["review", "2", "add-finding", "Off-by-one", "--severity", "high"])
    assert r.exit_code == 0, r.output

    listed = json.loads((await invoke(["review", "2", "findings", "--json"])).output)
    assert listed[0]["status"] == "Open"
    assert listed[0]["severity"] == "high"


async def test_flagless_add_calls_are_unaffected_additive_behaviour(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    r = await invoke(["task", "2", "add-subtask", "Wire API"])
    assert r.exit_code == 0, r.output

    listed = json.loads((await invoke(["task", "2", "subtasks", "--json"])).output)
    assert listed[0]["status"] == "Todo"


async def test_out_of_lifecycle_status_on_a_finding_is_refused_cleanly(project, invoke) -> None:
    await invoke(["create", "review", "R", "--author", "manager"])
    # "InProgress" is a story/subtask status, not a member of the finding lifecycle.
    r = await invoke(["review", "2", "add-finding", "Off-by-one", "--status", "InProgress"])
    assert r.exit_code == 1
    assert "Traceback" not in r.output
    assert "InProgress" in r.output

    findings = json.loads((await invoke(["review", "2", "findings", "--json"])).output)
    assert findings == []
