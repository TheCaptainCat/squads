"""The CLI surfaces the same status-vocabulary rejection and the same force-bypasses-edge-
not-vocabulary distinction the service enforces (tests/service/test_status_vocabulary_
enforcement.py) — this only proves the CLI wiring reaches it, not the rule itself again.
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_cli_rejects_a_status_outside_the_declared_vocabulary(project, invoke):
    await invoke(["create", "bug", "Crash", "--author", "manager"])
    result = await invoke(["bug", "2", "status", "Done"])
    assert result.exit_code == 1
    assert "not a valid status for bug" in result.output


async def test_cli_force_does_not_bypass_the_vocabulary_check(project, invoke):
    await invoke(["create", "bug", "Crash", "--author", "manager"])
    result = await invoke(["bug", "2", "status", "Done", "--force"])
    assert result.exit_code == 1
    assert "not a valid status for bug" in result.output


async def test_cli_drives_the_full_bug_lifecycle_from_open_to_verified(project, invoke):
    await invoke(["create", "bug", "Null pointer", "--author", "manager"])
    in_progress = await invoke(["bug", "2", "status", "InProgress"])
    assert in_progress.exit_code == 0 and "InProgress" in in_progress.output
    fixed = await invoke(["bug", "2", "status", "Fixed"])
    assert fixed.exit_code == 0 and "Fixed" in fixed.output
    verified = await invoke(["bug", "2", "status", "Verified"])
    assert verified.exit_code == 0 and "Verified" in verified.output
