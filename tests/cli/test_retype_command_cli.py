"""``sq <type> <n> retype <new_type>`` driven through the real CLI: rejects an undeclared
target type, reports whether the status was carried or reset, and reports how many files had
their refs rewritten. The service-level mechanics (file move, ref rewrite, body preservation,
container scaffolding, retype guardrails) are proven at tests/service/test_retype.py — this is
the command's own messaging and argument validation.
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_retype_to_an_undeclared_type_is_rejected(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    r = await invoke(["task", "2", "retype", "bogustype"])
    assert r.exit_code == 1
    assert "bogustype" in r.output


async def test_retype_reports_status_carried_when_the_target_status_exists(project, invoke) -> None:
    """feature -> epic: both share the generic work lifecycle's states, so the same status
    name carries over unchanged."""
    await invoke(["create", "feature", "F", "--author", "manager"])
    r = await invoke(["feature", "2", "retype", "epic"])
    assert r.exit_code == 0, r.output
    assert "EPIC-2" in r.output
    assert "status carried" in r.output


async def test_retype_reports_status_reset_when_the_target_uses_a_different_lifecycle(
    project, invoke
) -> None:
    """task -> bug: distinct lifecycles, so the status can't carry and is reset to the
    target type's initial status instead."""
    await invoke(["create", "task", "T", "--author", "manager"])
    r = await invoke(["task", "2", "retype", "bug"])
    assert r.exit_code == 0, r.output
    assert "BUG-2" in r.output
    assert "status reset" in r.output


async def test_retype_names_the_new_id_and_the_number_of_files_with_rewritten_refs(
    project, invoke
) -> None:
    await invoke(["create", "feature", "F", "--author", "manager"])
    await invoke(["create", "task", "T", "--author", "manager", "--ref", "FEAT-2"])

    r = await invoke(["feature", "2", "retype", "epic"])
    assert r.exit_code == 0, r.output
    assert "EPIC-2" in r.output
    assert "rewritten refs in 1 file" in r.output
