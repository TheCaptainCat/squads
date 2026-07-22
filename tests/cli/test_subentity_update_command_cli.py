"""``sq <type> <n> <kind> <n> update``: the sub-entity metadata entry point shares the item-
level update's mutual-exclusion guards (``--assignee``/``--clear-assignee``, at-least-one-field)
plus its own kind-specific ``--story``/``--no-story`` pair (only on kinds that map to a parent
story, e.g. subtask), and ``--clear-assignee`` actually clears the stored assignee. Also covers
the one declared-field CLI update (``finding``'s ``--severity``) alongside a call that touches
only the title — proving the per-field loop skips an omitted flag rather than clearing it.
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_update_rejects_assignee_and_clear_assignee_together(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    await invoke(["task", "2", "add-subtask", "Wire API"])

    r = await invoke(
        ["task", "2", "subtask", "1", "update", "--assignee", "manager", "--clear-assignee"]
    )
    assert r.exit_code == 1
    assert "not both" in r.output


async def test_update_with_no_fields_at_all_is_rejected(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    await invoke(["task", "2", "add-subtask", "Wire API"])

    r = await invoke(["task", "2", "subtask", "1", "update"])
    assert r.exit_code == 1
    assert "nothing to update" in r.output


async def test_clear_assignee_unassigns_a_previously_assigned_subtask(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    await invoke(["task", "2", "add-subtask", "Wire API", "--assignee", "manager"])

    r = await invoke(["task", "2", "subtask", "1", "update", "--clear-assignee"])
    assert r.exit_code == 0, r.output

    listed = await invoke(["task", "2", "subtasks", "--json"])
    import json

    data = json.loads(listed.output)
    assert data[0]["assignee"] is None


async def test_update_rejects_story_and_no_story_together(project, invoke) -> None:
    await invoke(["create", "feature", "F", "--author", "manager"])
    await invoke(["feature", "2", "add-story", "reset password"])
    await invoke(["create", "task", "T", "--author", "manager", "--parent", "FEAT-2"])
    await invoke(["task", "3", "add-subtask", "Validate expiry", "--story", "US1"])

    r = await invoke(["task", "3", "subtask", "1", "update", "--story", "US1", "--no-story"])
    assert r.exit_code == 1
    assert "not both" in r.output


async def test_no_story_clears_the_stored_story_mapping(project, invoke) -> None:
    await invoke(["create", "feature", "F", "--author", "manager"])
    await invoke(["feature", "2", "add-story", "reset password"])
    await invoke(["create", "task", "T", "--author", "manager", "--parent", "FEAT-2"])
    await invoke(["task", "3", "add-subtask", "Validate expiry", "--story", "US1"])

    r = await invoke(["task", "3", "subtask", "1", "update", "--no-story"])
    assert r.exit_code == 0, r.output

    listed = await invoke(["task", "3", "subtasks", "--json"])
    import json

    data = json.loads(listed.output)
    assert data[0]["story"] is None


async def test_finding_update_sets_the_severity_and_a_title_only_call_leaves_it_untouched(
    project, invoke
) -> None:
    await invoke(["create", "review", "R", "--author", "manager"])
    await invoke(["review", "2", "add-finding", "Off-by-one", "--severity", "low"])

    r = await invoke(["review", "2", "finding", "1", "update", "--severity", "high"])
    assert r.exit_code == 0, r.output

    import json

    findings = json.loads((await invoke(["review", "2", "findings", "--json"])).output)
    assert findings[0]["severity"] == "high"

    # a title-only update omits --severity entirely — the field loop must skip it, not clear it.
    await invoke(["review", "2", "finding", "1", "update", "--title", "Off-by-one, revisited"])
    findings_after = json.loads((await invoke(["review", "2", "findings", "--json"])).output)
    assert findings_after[0]["severity"] == "high"
    assert findings_after[0]["title"] == "Off-by-one, revisited"
