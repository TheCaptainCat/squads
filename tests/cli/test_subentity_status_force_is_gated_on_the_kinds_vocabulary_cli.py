"""``sq <type> <n> <kind> <k> update --status`` refuses a status the kind does not declare, with
or without ``--force``, and leaves ``sq check`` green on everything it does accept.

The command layer is a distinct place the wiring can regress: ``--status`` is parsed against the
squad's *global* status set (every status any machine declares), so a value belonging to another
kind's machine reaches the service as a perfectly well-formed argument. This pins that the
command surfaces the refusal — exit 1, the offending value and the kind's own allowed statuses
named — while the edge waiver ``--force`` exists for still works.
"""

import pytest

pytestmark = pytest.mark.anyio


async def _task_with_a_subtask(invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    await invoke(["task", "2", "add-subtask", "Wire API"])


@pytest.mark.parametrize("flags", [[], ["--force"]], ids=["without-force", "with-force"])
async def test_a_status_from_another_kinds_machine_is_refused(project, invoke, flags) -> None:
    await _task_with_a_subtask(invoke)

    r = await invoke(["task", "2", "subtask", "1", "update", "--status", "Verified", *flags])

    assert r.exit_code == 1, r.output
    assert "'Verified' is not a valid subtask status" in r.output
    assert "Todo" in r.output and "Cancelled" in r.output
    listed = await invoke(["task", "2", "subtasks"])
    assert "Verified" not in listed.output


async def test_a_refused_status_leaves_the_integrity_gate_green(project, invoke) -> None:
    await _task_with_a_subtask(invoke)
    await invoke(["task", "2", "subtask", "1", "update", "--status", "Verified", "--force"])

    r = await invoke(["check"])

    assert r.exit_code == 0, r.output
    assert "invalid status" not in r.output


async def test_force_still_moves_a_subtask_across_an_edge_the_machine_forbids(
    project, invoke
) -> None:
    await _task_with_a_subtask(invoke)

    r = await invoke(["task", "2", "subtask", "1", "update", "--status", "Done", "--force"])

    assert r.exit_code == 0, r.output
    listed = await invoke(["task", "2", "subtasks"])
    assert "Done" in listed.output
    assert (await invoke(["check"])).exit_code == 0


async def test_the_same_edge_without_force_still_reports_the_transition(project, invoke) -> None:
    await _task_with_a_subtask(invoke)

    r = await invoke(["task", "2", "subtask", "1", "update", "--status", "Done"])

    assert r.exit_code == 1, r.output
    assert "cannot move Todo" in r.output
    assert "--force" in r.output
