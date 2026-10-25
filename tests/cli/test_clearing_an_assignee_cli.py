"""`update --clear-assignee` removes an assignee, and an empty `--assignee` is refused on an item
and on a sub-entity rather than reported as a write that did not happen."""

import pytest

from _helpers import create_item
from _selection_table import TypeRow, override_toml, service_with

pytestmark = pytest.mark.anyio

_TASK = TypeRow("task", "task")


async def _task(svc, **kwargs):
    item = (await create_item(svc, "task", "t", **kwargs)).item
    return item, ["task", str(item.sequence_id), "update"]


async def test_clearing_removes_the_assignee(svc, invoke) -> None:
    item, base = await _task(svc, assignee="manager")

    result = await invoke([*base, "--clear-assignee"])

    assert result.exit_code == 0, result.output
    assert "updated" in result.output
    assert (await svc.get(item.id)).assignee is None


async def test_clearing_an_unassigned_item_writes_nothing(svc, invoke) -> None:
    item, base = await _task(svc)
    before = (await svc.get(item.id)).updated_at

    result = await invoke([*base, "--clear-assignee"])

    assert result.exit_code == 0, result.output
    assert "updated" not in result.output
    assert (await svc.get(item.id)).updated_at == before


@pytest.mark.parametrize(
    ("flags", "message"),
    [
        (["--assignee", ""], "--clear-assignee"),
        (["--assignee", "manager", "--clear-assignee"], "not both"),
    ],
)
async def test_an_empty_or_contradicted_assignee_is_refused(svc, invoke, flags, message) -> None:
    item, base = await _task(svc, assignee="manager")

    result = await invoke([*base, *flags])

    assert result.exit_code == 1, result.output
    assert message in result.output
    assert (await svc.get(item.id)).assignee == "manager"


async def test_clearing_an_unassigned_subtask_writes_nothing(svc, invoke) -> None:
    task = (await create_item(svc, "task", "t")).item
    await svc.add_block(task.id, "subtask", "s")
    before = (await svc.get(task.id)).updated_at

    result = await invoke(
        ["task", str(task.sequence_id), "subtask", "1", "update", "--clear-assignee"]
    )

    assert result.exit_code == 0, result.output
    assert "updated" not in result.output
    assert (await svc.get(task.id)).updated_at == before


async def test_an_update_with_no_option_writes_nothing(svc, invoke) -> None:
    item, base = await _task(svc)
    before = (await svc.get(item.id)).updated_at

    result = await invoke(base)

    assert result.exit_code == 1, result.output
    assert "nothing to update" in result.output
    assert (await svc.get(item.id)).updated_at == before


@pytest.mark.parametrize(
    ("flags", "message"),
    [
        (["--assignee", ""], "--clear-assignee"),
        (["--assignee", "manager", "--clear-assignee"], "not both"),
    ],
)
async def test_the_subtask_verb_refuses_the_same_flags(svc, invoke, flags, message) -> None:
    task = (await create_item(svc, "task", "t")).item
    await svc.add_block(task.id, "subtask", "s", assignee="manager")

    result = await invoke(["task", str(task.sequence_id), "subtask", "1", "update", *flags])

    assert result.exit_code == 1, result.output
    assert message in result.output


async def test_clearing_is_refused_by_the_validator_on_an_active_item(project, invoke) -> None:
    svc = service_with(project.squad_dir, override_toml(_TASK, ("assignee_present@error",)))
    item, base = await _task(svc, assignee="manager")
    await svc.update(item.id, status="InProgress")

    result = await invoke([*base, "--clear-assignee"])

    assert result.exit_code == 1, result.output
    assert "nobody is assigned" in result.output
    assert (await svc.get(item.id)).assignee == "manager"
