"""`sq check`: the lint report of a clean and of a damaged squad, in text and as JSON, and the
exit code each earns."""

import json

import pytest

pytestmark = pytest.mark.anyio

NO_AUTHOR = (
    "type 'task' has 1 open item but no live role authors it — activate `tech-lead` "
    "(`sq role activate tech-lead`)"
)
NO_AUTHOR_ISSUE = {
    "level": "warn",
    "item": "",
    "message": NO_AUTHOR,
    "rule": "type_has_live_author",
}
DANGLING_ISSUE = {
    "level": "error",
    "item": "TASK-2",
    "message": "dangling parent FEAT-99",
    "rule": "parent_in",
}


@pytest.fixture
async def damaged_project(project, invoke):
    """The `minimal` squad with a task whose parent does not exist."""
    created = await invoke(["create", "task", "Orphan", "--author", "manager"])
    assert created.exit_code == 0, created.output
    path = project.squad_dir / "tasks/TASK-000002-orphan.md"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("author: manager", "author: manager\nparent: FEAT-99"), "utf-8")
    repaired = await invoke(["repair"])
    assert repaired.exit_code == 0, repaired.output
    return project


@pytest.mark.covers("check")
async def test_check_reports_a_clean_squad(project, invoke) -> None:
    result = await invoke(["check"])
    assert (result.exit_code, result.output) == (0, "✓ no issues\n")


@pytest.mark.covers("check", "--json")
async def test_json_prints_an_empty_array_for_a_clean_squad(project, invoke) -> None:
    result = await invoke(["check", "--json"])
    assert (result.exit_code, result.output) == (0, "[]\n")


@pytest.mark.covers("check")
async def test_check_names_each_issue_and_exits_3_on_an_error(damaged_project, invoke) -> None:
    result = await invoke(["check"])
    assert (result.exit_code, result.output) == (
        3,
        f"warn: {NO_AUTHOR}\nerror TASK-2: dangling parent FEAT-99\n",
    )


@pytest.mark.covers("check", "--json")
async def test_json_prints_one_object_per_issue_and_exits_3_on_an_error(
    damaged_project, invoke
) -> None:
    result = await invoke(["check", "--json"])
    assert result.exit_code == 3
    assert result.output == json.dumps([NO_AUTHOR_ISSUE, DANGLING_ISSUE], indent=2) + "\n"


@pytest.mark.covers("check", "--json")
async def test_check_exits_0_when_the_issues_are_warnings(populated_project, invoke) -> None:
    result = await invoke(["check", "--json"])
    assert result.exit_code == 0
    assert {issue["level"] for issue in json.loads(result.output)} == {"warn"}


async def _check_issues(invoke) -> list[dict[str, str]]:
    return json.loads((await invoke(["check", "--json"])).output)


@pytest.mark.covers("check", "--json")
@pytest.mark.covers("repair")
@pytest.mark.covers("<type> <kind> update")
async def test_a_mapping_to_a_missing_sub_entity_names_the_target_kind(
    override_project, invoke
) -> None:
    mapped = await invoke(["job", "9", "action", "1", "update", "--outcome", "1"])
    assert mapped.exit_code == 0, mapped.output
    job = next((override_project.squad_dir / "jobs").glob("JOB-*.md"))
    job.write_text(job.read_text("utf-8").replace("maps_to: OC1", "maps_to: OC9"), "utf-8")
    assert (await invoke(["repair"])).exit_code == 0

    assert await _check_issues(invoke) == [
        {
            "level": "error",
            "item": "JOB-9",
            "message": "action AC1 maps to outcome OC9, missing from INI-8",
            "rule": "subentity_mapping",
        }
    ]


@pytest.mark.covers("check", "--json")
@pytest.mark.covers("<type> status", "STATUS")
async def test_a_superseded_record_names_the_declared_supersession_kind(
    override_project, invoke
) -> None:
    moved = await invoke(["record", "10", "status", "Superseded", "--force"])
    assert moved.exit_code == 0, moved.output

    assert await _check_issues(invoke) == [
        {
            "level": "warn",
            "item": "REC-10",
            "message": "status is Superseded but no incoming replaces edge found",
            "rule": "supersedes_incoming",
        }
    ]
