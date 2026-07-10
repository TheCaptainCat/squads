"""The unwritten-subentity-body advisory at the CLI surface: `sq check` prints it (exit 0),
clears once a real body is written, and `--json` carries the warn issue. Detector-logic facts
live in tests/service/test_unwritten_subentity_body_advisory_check.py.
"""

import json

import pytest

pytestmark = pytest.mark.anyio


async def test_check_prints_the_unwritten_body_issue_and_exits_0(project, invoke) -> None:
    await invoke(["create", "feature", "My feature", "--author", "manager"])
    await invoke(["feature", "2", "add-story", "A story"])
    result = await invoke(["check"])
    assert result.exit_code == 0, result.output
    assert "body is unwritten" in result.output


async def test_check_clears_the_issue_once_a_real_body_is_written(project, invoke) -> None:
    await invoke(["create", "feature", "My feature", "--author", "manager"])
    await invoke(["feature", "2", "add-story", "A story"])
    await invoke(["feature", "2", "story", "1", "body", "-m", "Real acceptance criteria."])
    result = await invoke(["check"])
    assert "body is unwritten" not in result.output


async def test_check_json_includes_the_unwritten_body_issue_at_warn_level(project, invoke) -> None:
    await invoke(["create", "feature", "My feature", "--author", "manager"])
    await invoke(["feature", "2", "add-story", "A story"])
    result = await invoke(["check", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    matches = [i for i in data if "body is unwritten" in i.get("message", "")]
    assert matches
    assert matches[0]["level"] == "warn"
