"""`settled_requires_discussion` at the CLI: the `status` verb to a settled status exits 0 at every
level, `sq check` exits 0 for a finding at `warn` and 3 at `@error`, `--json` carries the item,
one `comment` clears it, and `sq workflow lint` refuses the check on a roster type.
"""

import json

import pytest

from _helpers import create_item
from _selection_table import TypeRow, override_toml, service_with, write_override

pytestmark = pytest.mark.anyio

_TASK = TypeRow("task", "task")


@pytest.mark.parametrize(
    ("entry", "check_exit", "level"),
    [("settled_requires_discussion", 0, "warn"), ("settled_requires_discussion@error", 3, "error")],
)
async def test_the_status_verb_succeeds_and_check_exit_follows_the_level(
    project, invoke, entry, check_exit, level
) -> None:
    svc = service_with(project.squad_dir, override_toml(_TASK, (entry,)))
    item = (await create_item(svc, "task", "t")).item
    number = str(item.sequence_id)
    moved = await invoke(["task", number, "update", "--status", "Done", "--force"])
    assert moved.exit_code == 0, moved.output

    checked = await invoke(["check"])
    assert checked.exit_code == check_exit, checked.output
    rows = json.loads((await invoke(["check", "--json"])).output)
    found = [r for r in rows if "discussion holds no comment" in r.get("message", "")]
    assert [(r["item"], r["level"]) for r in found] == [(item.id, level)]

    commented = await invoke(["task", number, "comment", "--as", "manager", "-m", "Closed out."])
    assert commented.exit_code == 0, commented.output
    assert (await invoke(["check"])).exit_code == 0


async def test_lint_refuses_the_check_on_a_roster_type(project, invoke) -> None:
    write_override(
        project.squad_dir, '[items.role]\nvalidators = ["settled_requires_discussion"]\n'
    )
    linted = await invoke(["workflow", "lint"])
    assert linted.exit_code == 1, linted.output
    assert "roster" in linted.output
