"""CLI smoke: the two verbs that used to report success while doing something other than what
they said now exit 1 and say why.

``body`` replaced an already-written region silently; ``role activate`` reported an activation
it had not performed. Both are answered the same way — refuse, name the remedy, write nothing —
so both are pinned here on the surface an operator or agent actually types, including the exit
code, which is what a caller branches on.
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_body_refuses_to_replace_an_already_written_body(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    first = await invoke(["task", "2", "body", "-m", "## Runbook", "-m", "the real content"])
    assert first.exit_code == 0, first.output

    r = await invoke(["task", "2", "body", "-m", "probe"])
    assert r.exit_code == 1
    assert "already has a body" in r.output
    assert "--append" in r.output and "--force" in r.output

    shown = await invoke(["task", "2", "show", "--full"])
    assert "the real content" in shown.output
    assert "probe" not in shown.output


async def test_body_force_replaces_and_append_adds(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    await invoke(["task", "2", "body", "-m", "the real content"])

    appended = await invoke(["task", "2", "body", "--append", "-m", "and a tail"])
    assert appended.exit_code == 0, appended.output

    forced = await invoke(["task", "2", "body", "--force", "-m", "wholly new"])
    assert forced.exit_code == 0, forced.output

    shown = await invoke(["task", "2", "show", "--full"])
    assert "wholly new" in shown.output
    assert "the real content" not in shown.output


async def test_a_sub_entity_body_carries_the_same_guard(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    await invoke(["task", "2", "add-subtask", "a subtask"])
    first = await invoke(["task", "2", "subtask", "ST1", "body", "-m", "the real content"])
    assert first.exit_code == 0, first.output

    r = await invoke(["task", "2", "subtask", "ST1", "body", "-m", "probe"])
    assert r.exit_code == 1
    assert "already has a body" in r.output


async def test_a_custom_skill_body_carries_the_same_guard(project, invoke) -> None:
    await invoke(["skill", "add", "Release Runbook"])
    first = await invoke(["skill", "release-runbook", "body", "-m", "the real runbook"])
    assert first.exit_code == 0, first.output

    r = await invoke(["skill", "release-runbook", "body", "-m", "probe"])
    assert r.exit_code == 1
    assert "already has a body" in r.output

    shown = await invoke(["skill", "release-runbook", "show", "--raw"])
    assert "the real runbook" in shown.output


async def test_role_activate_refuses_a_retired_role_instead_of_claiming_success(
    project, invoke
) -> None:
    activated = await invoke(["role", "activate", "tech-writer"])
    assert activated.exit_code == 0, activated.output
    await invoke(["role", "tech-writer", "status", "Archived"])

    r = await invoke(["role", "activate", "tech-writer"])
    assert r.exit_code == 1
    assert "activated" not in r.output
    assert "sq role tech-writer status Active" in r.output

    listed = await invoke(["list", "-t", "role", "-a", "--json"])
    assert '"Archived"' in listed.output
