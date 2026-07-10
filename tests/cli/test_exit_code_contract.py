"""The CLI's exit-code contract as its own tested surface: 0 = success (including `sq check`
with no issues, or warnings only), 1 = a runtime error (an unknown item, or a schema-version
mismatch), 2 = a usage error (a malformed global option), 3 = `sq check` found at least one
error-level issue. Individual codes are hit incidentally elsewhere; this file proves the
contract itself — these are exactly the four codes, and this is what triggers each.
"""

import json

import pytest

from squads._models._schema import SCHEMA_VERSION

pytestmark = pytest.mark.anyio


async def test_exit_code_0_on_a_successful_read_command(project, invoke):
    result = await invoke(["list"])
    assert result.exit_code == 0, result.output


async def test_exit_code_0_when_check_finds_no_issues(project, invoke):
    result = await invoke(["check"])
    assert result.exit_code == 0, result.output
    assert "no issues" in result.output


async def test_exit_code_0_when_check_finds_only_warnings(project, invoke):
    # A Superseded decision with no incoming supersedes edge is a warn, not an error.
    await invoke(["create", "decision", "Old ADR", "--author", "manager"])
    await invoke(["decision", "2", "status", "Proposed"])
    await invoke(["decision", "2", "update", "--status", "Superseded", "--force"])
    await invoke(["repair"])

    result = await invoke(["check"])
    assert result.exit_code == 0, result.output
    assert "warn" in result.output


async def test_exit_code_1_on_a_squads_runtime_error(project, invoke):
    result = await invoke(["task", "999", "show"])
    assert result.exit_code == 1, result.output


async def test_exit_code_1_on_a_schema_version_mismatch(project, invoke):
    cfg = project.config_path
    cfg.write_text(
        cfg.read_text(encoding="utf-8").replace(
            f'schema_version = "{SCHEMA_VERSION}"', 'schema_version = "0.1"'
        ),
        encoding="utf-8",
    )
    result = await invoke(["list"])
    assert result.exit_code == 1, result.output
    assert "migrate" in result.output.lower()


async def test_exit_code_2_on_an_invalid_at_timestamp(project, invoke):
    result = await invoke(["--at", "not-a-date", "list"])
    assert result.exit_code == 2, result.output


async def _inject_ghost_item(svc) -> None:
    raw = json.loads(svc.store.index_path.read_text(encoding="utf-8"))
    raw["items"]["99"] = {
        "id": "TASK-99",
        "sequence_id": 99,
        "type": "task",
        "title": "ghost",
        "slug": "ghost",
        "status": "Draft",
        "path": "tasks/TASK-000099-ghost.md",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    raw["counter"] = 99
    svc.store.index_path.write_text(json.dumps(raw), encoding="utf-8")


async def test_exit_code_3_when_check_finds_an_error_level_issue(project, invoke):
    from squads._services._service import Service

    await _inject_ghost_item(Service(project))
    result = await invoke(["check"])
    assert result.exit_code == 3, result.output
    assert "TASK-99" in result.output


async def test_exit_code_3_when_check_json_finds_an_error_level_issue(project, invoke):
    from squads._services._service import Service

    await _inject_ghost_item(Service(project))
    result = await invoke(["check", "--json"])
    assert result.exit_code == 3, result.output
    data = json.loads(result.output)
    assert any(issue["level"] == "error" for issue in data)
