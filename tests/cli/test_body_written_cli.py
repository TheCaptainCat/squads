"""`body_written` at the CLI: `sq check` exits 0 for a finding at `warn` and 3 at `@error`, its
`--json` carries the item id, no write is refused at `@error`, and `sq workflow lint` refuses
the check on a roster type with exit 1.
"""

import json
import re

import pytest

from _selection_table import TypeRow, override_toml, service_with, write_override

pytestmark = pytest.mark.anyio

_TASK = TypeRow("task", "task")


@pytest.mark.parametrize(
    ("entry", "exit_code", "level"),
    [("body_written", 0, "warn"), ("body_written@error", 3, "error")],
)
async def test_check_exit_code_follows_the_level_and_no_write_is_refused(
    project, invoke, entry, exit_code, level
) -> None:
    service_with(project.squad_dir, override_toml(_TASK, (entry,)))
    created = await invoke(["create", "task", "no body", "--author", "manager"])
    assert created.exit_code == 0, created.output
    match = re.search(r"TASK-(\d+)", created.output)
    assert match
    number = match.group(1)
    updated = await invoke(["task", number, "update", "--add-label", "x"])
    assert updated.exit_code == 0, updated.output
    moved = await invoke(["task", number, "status", "Ready"])
    assert moved.exit_code == 0, moved.output

    text = await invoke(["check"])
    assert text.exit_code == exit_code, text.output
    assert "still the template scaffold" in text.output
    rows = json.loads((await invoke(["check", "--json"])).output)
    assert [r["level"] for r in rows if "template scaffold" in r.get("message", "")] == [level]


async def test_lint_refuses_the_check_on_a_roster_type(project, invoke) -> None:
    write_override(project.squad_dir, '[items.skill]\nvalidators = ["body_written"]\n')
    linted = await invoke(["workflow", "lint"])
    assert linted.exit_code == 1, linted.output
    assert "roster" in linted.output
