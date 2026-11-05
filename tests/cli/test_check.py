"""`sq check`: the lint report of a clean and of a damaged squad, in text and as JSON, and the
exit code each earns."""

import json
from pathlib import Path

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
@pytest.mark.bundled_only("the damaged squad and its messages are the bundled task type's")
async def test_check_names_each_issue_and_exits_3_on_an_error(damaged_project, invoke) -> None:
    result = await invoke(["check"])
    assert (result.exit_code, result.output) == (
        3,
        f"warn: {NO_AUTHOR}\nerror TASK-2: dangling parent FEAT-99\n",
    )


@pytest.mark.covers("check", "--json")
@pytest.mark.bundled_only("the damaged squad and its messages are the bundled task type's")
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
@pytest.mark.covers("<type> <kind>", "local-id")
async def test_a_mapping_to_a_missing_sub_entity_names_the_target_kind(
    override_project, invoke
) -> None:
    mapped = await invoke(["job", "6", "action", "1", "update", "--outcome", "1"])
    assert mapped.exit_code == 0, mapped.output
    job = next((override_project.squad_dir / "jobs").glob("JOB-*.md"))
    job.write_text(job.read_text("utf-8").replace("maps_to: OC1", "maps_to: OC9"), "utf-8")
    assert (await invoke(["repair"])).exit_code == 0

    assert await _check_issues(invoke) == [
        {
            "level": "error",
            "item": "JOB-6",
            "message": "action AC1 maps to outcome OC9, missing from INI-5",
            "rule": "subentity_mapping",
        }
    ]


@pytest.mark.covers("check", "--json")
@pytest.mark.covers("<type> status", "status")
async def test_a_superseded_record_names_the_declared_supersession_kind(
    override_project, invoke
) -> None:
    moved = await invoke(["record", "7", "status", "Superseded", "--force"])
    assert moved.exit_code == 0, moved.output

    assert await _check_issues(invoke) == [
        {
            "level": "warn",
            "item": "REC-7",
            "message": "status is Superseded but no incoming replaces edge found",
            "rule": "supersedes_incoming",
        }
    ]


RECORD = {
    "name": "platform",
    "id": "48211",
    "key": "platform/api#12",
    "state": "open",
    "updated_at": "2026-11-03T20:41:07Z",
    "author_id": "4567",
}


async def _mirror(invoke, project, profile, title: str, record: dict[str, str]) -> Path:
    """An item of the host type whose file carries *record* as its `source`; no command writes a
    record that lacks a field."""
    created = await invoke(["create", profile.host, title, "--author", "manager"])
    assert created.exit_code == 0, created.output
    path = next(
        p
        for p in (project.squad_dir / profile.host_folder).glob(f"{profile.host_prefix}-*.md")
        if title.lower() in p.name
    )
    lines = "source:\n" + "".join(f"  {key}: '{value}'\n" for key, value in record.items())
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("\nstatus:", f"\n{lines}status:", 1), encoding="utf-8")
    return path


@pytest.mark.covers("check")
async def test_an_item_whose_source_record_is_malformed_is_refused_naming_its_file(
    project, invoke, profile
) -> None:
    await _mirror(invoke, project, profile, "Mirror", RECORD)

    result = await invoke(["check"])

    assert (result.exit_code, result.output) == (
        3,
        f"error {profile.host_prefix}-000002-mirror.md: invalid item data in "
        f"{profile.host_path(2, 'mirror')}: source.author_handle: Field required\n"
        f"{profile.host_author_warning}",
    )
