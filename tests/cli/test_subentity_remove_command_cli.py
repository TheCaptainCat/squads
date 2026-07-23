"""``sq <type> <n> <kind> <local> remove`` — guarded hard-delete for a story/subtask/finding
sub-entity, mirroring `sq <type> <n> remove`'s ``--yes`` confirmation contract at the sub-entity
scope.
"""

import json

import pytest

pytestmark = pytest.mark.anyio


async def test_yes_bypasses_the_confirmation_prompt(project, invoke) -> None:
    await invoke(["create", "feature", "F", "--author", "manager"])
    await invoke(["feature", "2", "add-story", "Doomed"])

    r = await invoke(["feature", "2", "story", "1", "remove", "--yes"])
    assert r.exit_code == 0, r.output
    assert "removed" in r.output

    listed = json.loads((await invoke(["feature", "2", "stories", "--json"])).output)
    assert listed == []


async def test_without_yes_the_prompt_aborts_on_no(project, invoke) -> None:
    await invoke(["create", "feature", "F", "--author", "manager"])
    await invoke(["feature", "2", "add-story", "Doomed"])

    r = await invoke(["feature", "2", "story", "1", "remove"], input="n\n")
    assert r.exit_code != 0

    listed = json.loads((await invoke(["feature", "2", "stories", "--json"])).output)
    assert len(listed) == 1


async def test_json_result_shape(project, invoke) -> None:
    await invoke(["create", "review", "R", "--author", "manager"])
    await invoke(["review", "2", "add-finding", "Doomed", "--severity", "high"])

    r = await invoke(["review", "2", "finding", "1", "remove", "--yes", "--json"])
    assert r.exit_code == 0, r.output
    assert json.loads(r.output) == {"removed": "finding F1"}


async def test_removing_a_nonexistent_local_id_fails_cleanly(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    r = await invoke(["task", "2", "subtask", "9", "remove", "--yes"])
    assert r.exit_code == 1
    assert "Traceback" not in r.output


async def test_removing_a_story_mapped_by_a_subtask_is_refused(project, invoke) -> None:
    await invoke(["create", "feature", "F", "--author", "manager"])
    await invoke(["feature", "2", "add-story", "Login"])
    await invoke(["create", "task", "T", "--author", "manager", "--parent", "FEAT-000002"])
    await invoke(["task", "3", "add-subtask", "Wire it up", "--story", "US1"])

    r = await invoke(["feature", "2", "story", "1", "remove", "--yes"])
    assert r.exit_code == 1
    assert "TASK-3" in r.output or "TASK-000003" in r.output

    listed = json.loads((await invoke(["feature", "2", "stories", "--json"])).output)
    assert len(listed) == 1


async def test_sibling_sub_entities_and_the_summary_table_survive_a_removal(
    project, invoke
) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    await invoke(["task", "2", "add-subtask", "Keep me"])
    await invoke(["task", "2", "add-subtask", "Remove me"])

    r = await invoke(["task", "2", "subtask", "2", "remove", "--yes"])
    assert r.exit_code == 0, r.output

    listed = json.loads((await invoke(["task", "2", "subtasks", "--json"])).output)
    assert [b["title"] for b in listed] == ["Keep me"]

    kept = await invoke(["task", "2", "subtask", "1", "show"])
    assert kept.exit_code == 0
    assert "Keep me" in kept.output
