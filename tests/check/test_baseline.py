"""The starting point every `sq check` rule test builds on: the `minimal` squad under the bundled
spec has nothing to report."""

import pytest

pytestmark = pytest.mark.anyio


async def test_the_baseline_squad_reports_no_issue(project, check_json) -> None:
    run = await check_json()
    assert (run.issues, run.exit_code) == ([], 0)
