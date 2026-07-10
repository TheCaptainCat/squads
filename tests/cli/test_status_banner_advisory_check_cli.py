"""The status/lifecycle-banner advisory at the CLI surface: `sq check` prints it (exit 0,
advisory only), stays silent on a topical lifecycle mention, and `--json` carries the warn
issue. Detector-logic facts live in tests/service/test_status_banner_advisory_check.py.
"""

import json

import pytest

pytestmark = pytest.mark.anyio


async def test_check_prints_the_status_banner_issue_and_exits_0(project, invoke) -> None:
    await invoke(["create", "feature", "My feature", "--author", "manager"])
    await invoke(["feature", "2", "body", "-m", "STATUS: Proposed"])
    result = await invoke(["check"])
    assert result.exit_code == 0, result.output
    assert "status/lifecycle banner" in result.output


async def test_check_stays_silent_on_a_topical_lifecycle_mention(project, invoke) -> None:
    await invoke(["create", "feature", "My feature", "--author", "manager"])
    await invoke(
        [
            "feature",
            "2",
            "body",
            "-m",
            "Describes the Draft→Ready transition this feature builds.",
        ]
    )
    result = await invoke(["check"])
    assert "status/lifecycle banner" not in result.output


async def test_check_json_includes_the_status_banner_issue_at_warn_level(project, invoke) -> None:
    await invoke(["create", "feature", "My feature", "--author", "manager"])
    await invoke(["feature", "2", "body", "-m", "STATUS: Proposed"])
    result = await invoke(["check", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    matches = [i for i in data if "status/lifecycle banner" in i.get("message", "")]
    assert matches
    assert matches[0]["level"] == "warn"
