"""`assignee_present` at the CLI: `sq <type> <n> status` to an active status is refused (exit 1)
only at `@error`, assigning in the same `update` is accepted, `sq check` exits 0 at `warn` and 3
at `@error`, and `sq workflow lint` refuses the check on a type with no live status.
"""

import json

import pytest

from _helpers import create_item
from _selection_table import TypeRow, override_toml, service_with, write_override

pytestmark = pytest.mark.anyio

_TASK = TypeRow("task", "task")


@pytest.mark.parametrize(
    ("entry", "move_exit", "check_exit", "level"),
    [("assignee_present", 0, 0, "warn"), ("assignee_present@error", 1, 0, None)],
)
async def test_a_status_move_is_refused_only_at_error(
    project, invoke, entry, move_exit, check_exit, level
) -> None:
    svc = service_with(project.squad_dir, override_toml(_TASK, ()))
    item = (await create_item(svc, "task", "t")).item
    service_with(project.squad_dir, override_toml(_TASK, (entry,)))

    moved = await invoke(["task", str(item.sequence_id), "update", "--status", "InProgress"])
    assert moved.exit_code == move_exit, moved.output
    checked = await invoke(["check"])
    assert checked.exit_code == check_exit, checked.output
    rows = json.loads((await invoke(["check", "--json"])).output)
    levels = [r["level"] for r in rows if "nobody is assigned" in r.get("message", "")]
    assert levels == ([level] if level else [])

    with_assignee = await invoke(
        ["task", str(item.sequence_id), "update", "--status", "InProgress", "--assignee", "manager"]
    )
    assert with_assignee.exit_code == 0, with_assignee.output


async def test_check_exits_3_for_an_unassigned_active_item_at_error(project, invoke) -> None:
    svc = service_with(project.squad_dir, override_toml(_TASK, ()))
    item = (await create_item(svc, "task", "t")).item
    await svc.update(item.id, status="InProgress", force=True)
    service_with(project.squad_dir, override_toml(_TASK, ("assignee_present@error",)))
    checked = await invoke(["check"])
    assert checked.exit_code == 3, checked.output
    assert "nobody is assigned" in checked.output


async def test_lint_refuses_the_check_on_a_type_with_no_live_status(project, invoke) -> None:
    write_override(project.squad_dir, '[items.decision]\nvalidators = ["assignee_present"]\n')
    linted = await invoke(["workflow", "lint"])
    assert linted.exit_code == 1, linted.output
    assert "live" in linted.output
