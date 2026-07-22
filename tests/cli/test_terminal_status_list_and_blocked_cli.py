"""``sq list``/``sq blocked`` on the real CLI surface, for both terminal-status categories:

- ``decision``/``guide`` are ``records``-category — Accepted/Published is final-but-live, so the
  item stays visible in the default list (category-aware visibility: a durable record doesn't
  vanish from view the moment it's finalized). Both remain searchable regardless.
- Accepted still unblocks a dependent task (``blocked`` counts by ``is_open``, unaffected by the
  default-visibility rule).
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_cli_accepted_decision_stays_visible_by_default_and_searchable(project, invoke):
    await invoke(["create", "decision", "Use Redis", "--author", "manager"])
    await invoke(["decision", "2", "status", "Accepted"])

    default = await invoke(["list", "--type", "decision"])
    assert "ADR-2" in default.output
    found = await invoke(["search", "Redis"])
    assert "ADR-2" in found.output


async def test_cli_published_guide_stays_visible_by_default_and_searchable(project, invoke):
    await invoke(["create", "guide", "Ops runbook", "--author", "manager"])
    await invoke(["guide", "2", "status", "Published"])

    default = await invoke(["list", "--type", "guide"])
    assert "GUIDE-2" in default.output
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
