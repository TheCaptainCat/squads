"""The title-length advisory surfaces on the CLI: a warn message on the human path, the same
text carried in --json, and `sq check` reporting it as a warn-level (exit-0) issue — the CLI's
half of the wiring, with the threshold math itself proven once at the service layer.
"""

import json

import pytest

from squads._interactions import TITLE_ADVISORY_MAX

pytestmark = pytest.mark.anyio

LONG_TITLE = "A" * (TITLE_ADVISORY_MAX + 1)
SHORT_TITLE = "Short title"


async def test_add_story_over_threshold_warns_and_exits_0(project, invoke):
    await invoke(["create", "feature", "My feature", "--author", "manager"])
    result = await invoke(["feature", "2", "add-story", LONG_TITLE])
    assert result.exit_code == 0, result.output
    assert str(len(LONG_TITLE)) in result.output
    assert "body" in result.output.lower()


async def test_add_story_short_title_carries_no_advisory_in_json(project, invoke):
    await invoke(["create", "feature", "My feature", "--author", "manager"])
    result = await invoke(["feature", "2", "add-story", SHORT_TITLE, "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output).get("title_advisory") is None


async def test_add_story_over_threshold_carries_advisory_in_json(project, invoke):
    await invoke(["create", "feature", "My feature", "--author", "manager"])
    result = await invoke(["feature", "2", "add-story", LONG_TITLE, "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["title_advisory"] is not None
    assert str(len(LONG_TITLE)) in data["title_advisory"]


async def test_check_reports_the_advisory_as_warn_and_still_exits_0(project, invoke):
    await invoke(["create", "feature", "My feature", "--author", "manager"])
    await invoke(["feature", "2", "add-story", LONG_TITLE])
    result = await invoke(["check"])
    assert result.exit_code == 0, result.output
    assert "warn" in result.output.lower() and "advisory" in result.output.lower()


async def test_check_json_advisory_is_warn_level_never_error(project, invoke):
    await invoke(["create", "feature", "My feature", "--author", "manager"])
    await invoke(["feature", "2", "add-story", LONG_TITLE])
    result = await invoke(["check", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert not [i for i in data if i.get("level") == "error"]
    assert [i for i in data if i.get("level") == "warn" and "advisory" in i.get("message", "")]
