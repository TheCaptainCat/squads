"""CLI smoke test for ``sq role <addr> set-default`` — the default-role designation move."""

import pytest

pytestmark = pytest.mark.anyio


async def test_set_default_moves_the_designation_and_reports_the_cleared_holder(
    project, invoke, svc
):
    r = await invoke(["role", "activate", "qa"])
    assert r.exit_code == 0, r.output
    manager = await svc.roster_item("role", "manager")

    r = await invoke(["role", "qa", "set-default"])

    assert r.exit_code == 0, r.output
    assert "is now the default" in r.output
    assert f"cleared {manager.id}" in r.output
    claude_md = (project.root / "CLAUDE.md").read_text(encoding="utf-8")
    assert "default to **Mara Tester**" in claude_md


async def test_set_default_on_the_current_holder_is_a_reported_no_op(project, invoke):
    r = await invoke(["role", "manager", "set-default"])

    assert r.exit_code == 0, r.output
    assert "already the default" in r.output


async def test_set_default_refuses_a_non_live_role(project, invoke):
    r = await invoke(["role", "activate", "qa"])
    assert r.exit_code == 0, r.output
    r = await invoke(["role", "qa", "status", "Archived"])
    assert r.exit_code == 0, r.output

    r = await invoke(["role", "qa", "set-default"])

    assert r.exit_code == 1
    assert "not live" in r.output
