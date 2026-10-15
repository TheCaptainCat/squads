"""`description_present` at the CLI: `update --desc` clears it on every type that
accepts the check; `sq create` without `--desc` is refused (exit 1) only at `@error` and with it
is accepted; `sq check` exits 0 at `warn` and 3 at `@error`; `sq workflow lint` refuses the
check on a roster type.
"""

import json

import pytest

from _helpers import create_item
from _selection_table import (
    DESCRIPTION_PRESENT,
    TypeRow,
    member_findings,
    override_toml,
    service_with,
    write_override,
)

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("row", DESCRIPTION_PRESENT.accepting_rows(), ids=lambda r: r.id)
async def test_update_desc_clears_the_finding_on_every_type(project, invoke, row: TypeRow) -> None:
    unselected = service_with(project.squad_dir, override_toml(row, ()))
    item = (await create_item(unselected, row.type, "t")).item
    svc = service_with(project.squad_dir, override_toml(row, ("description_present@error",)))
    assert member_findings(await svc.check(), DESCRIPTION_PRESENT)
    cleared = await invoke([row.type, str(item.sequence_id), "update", "--desc", "A summary."])
    assert cleared.exit_code == 0, cleared.output
    assert member_findings(await svc.check(), DESCRIPTION_PRESENT) == []


@pytest.mark.parametrize(
    ("entry", "create_exit", "check_exit"),
    [("description_present", 0, 0), ("description_present@error", 1, 3)],
)
async def test_create_and_check_exit_codes_follow_the_level(
    project, invoke, entry, create_exit, check_exit
) -> None:
    row = TypeRow("task", "task")
    service_with(project.squad_dir, override_toml(row, ()))
    first = await invoke(["create", "task", "no summary", "--author", "manager"])
    assert first.exit_code == 0, first.output
    service_with(project.squad_dir, override_toml(row, (entry,)))

    without = await invoke(["create", "task", "no summary", "--author", "manager"])
    assert without.exit_code == create_exit, without.output
    with_desc = await invoke(["create", "task", "t", "--author", "manager", "--desc", "A summary."])
    assert with_desc.exit_code == 0, with_desc.output

    checked = await invoke(["check"])
    assert checked.exit_code == check_exit, checked.output
    assert "description is empty" in checked.output
    rows = json.loads((await invoke(["check", "--json"])).output)
    levels = {r["level"] for r in rows if "description is empty" in r.get("message", "")}
    assert levels == {"error" if check_exit else "warn"}


async def test_lint_refuses_the_check_on_a_roster_type(project, invoke) -> None:
    write_override(project.squad_dir, '[items.operator]\nvalidators = ["description_present"]\n')
    linted = await invoke(["workflow", "lint"])
    assert linted.exit_code == 1, linted.output
    assert "roster" in linted.output
