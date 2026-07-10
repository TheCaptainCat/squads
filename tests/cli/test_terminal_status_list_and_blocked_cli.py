"""``sq list``/``sq blocked`` honor Accepted/Published as terminal on the real CLI surface: an
Accepted decision or Published guide is hidden from the default list, visible with --all, still
found by search, and no longer counted as a blocker.
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_cli_accepted_decision_hidden_then_visible_and_searchable(project, invoke):
    await invoke(["create", "decision", "Use Redis", "--author", "manager"])
    await invoke(["decision", "2", "status", "Accepted"])

    default = await invoke(["list", "--type", "decision"])
    assert "ADR-2" not in default.output
    with_all = await invoke(["list", "--type", "decision", "--all"])
    assert "ADR-2" in with_all.output
    found = await invoke(["search", "Redis"])
    assert "ADR-2" in found.output


async def test_cli_published_guide_hidden_then_visible_and_searchable(project, invoke):
    await invoke(["create", "guide", "Ops runbook", "--author", "manager"])
    await invoke(["guide", "2", "status", "Published"])

    default = await invoke(["list", "--type", "guide"])
    assert "GUIDE-2" not in default.output
    with_all = await invoke(["list", "--type", "guide", "--all"])
    assert "GUIDE-2" in with_all.output
    found = await invoke(["search", "runbook"])
    assert "GUIDE-2" in found.output


async def test_cli_accepted_adr_unblocks_a_dependent_task(project, invoke):
    await invoke(["create", "decision", "API contract", "--author", "manager"])
    await invoke(["create", "task", "Implement API", "--author", "manager"])
    await invoke(["task", "3", "ref", "add", "ADR-000002", "--kind", "depends-on"])

    before = await invoke(["blocked"])
    assert "TASK-3" in before.output
    await invoke(["decision", "2", "status", "Accepted"])
    after = await invoke(["blocked"])
    assert "TASK-3" not in after.output
