"""`sq role|skill rm --purge` is refused where `status Archived` is refused, and prints the same
warnings when it goes ahead."""

import pytest

pytestmark = pytest.mark.anyio


async def test_purging_a_skill_every_role_preloads_is_refused(project, invoke) -> None:
    await invoke(["role", "activate", "tech-lead"])  # its playbook interacts with task
    await invoke(["skill", "add", "Sq Task"])  # implied by the task type

    result = await invoke(["skill", "sq-task", "rm", "--purge"])
    archived = await invoke(["skill", "sq-task", "status", "Archived"])

    assert archived.exit_code != 0, archived.output
    assert result.exit_code == archived.exit_code, result.output
    assert "cannot remove" in result.output
    assert (await invoke(["skill", "sq-task", "show"])).exit_code == 0


async def test_purging_the_default_role_warns_as_archiving_does(project, invoke) -> None:
    await invoke(["role", "activate", "architect"])

    result = await invoke(["role", "manager", "rm", "--purge"])

    assert result.exit_code == 0, result.output
    assert "removed ROLE-" in result.output
    assert "warning:" in result.output
    assert "default-role designation" in result.output
