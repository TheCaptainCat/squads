"""`item_title_max` at the CLI: `sq check` exits 0 for a finding at `warn` and 3 at `@error`,
and `--json` carries the item id; `sq create` and `sq <type> <n> update` are refused (exit 1)
only at `@error`; `sq workflow lint` reports a missing threshold and a roster selection with
exit 1. The shape families are driven through the service.
"""

import json

import pytest

from _helpers import create_item
from _selection_table import TypeRow, override_toml, service_with, write_override

pytestmark = pytest.mark.anyio

_TASK = TypeRow("task", "task")
_LONG = "x" * 81


@pytest.mark.parametrize(
    ("entry", "exit_code", "level"),
    [("item_title_max:80", 0, "warn"), ("item_title_max:80@error", 3, "error")],
)
async def test_check_exit_code_follows_the_level(project, invoke, entry, exit_code, level) -> None:
    unselected = service_with(project.squad_dir, override_toml(_TASK, ()))
    item = (await create_item(unselected, "task", _LONG)).item
    service_with(project.squad_dir, override_toml(_TASK, (entry,)))
    text = await invoke(["check"])
    assert text.exit_code == exit_code, text.output
    assert "one-line handle" in text.output
    as_json = await invoke(["check", "--json"])
    assert as_json.exit_code == exit_code, as_json.output
    rows = [r for r in json.loads(as_json.output) if r.get("item") == item.id]
    assert [r["level"] for r in rows] == [level]


@pytest.mark.parametrize(
    ("entry", "create_exit"), [("item_title_max:80", 0), ("item_title_max:80@error", 1)]
)
async def test_create_and_update_are_refused_only_at_error(
    project, invoke, entry, create_exit
) -> None:
    unselected = service_with(project.squad_dir, override_toml(_TASK, ()))
    existing = (await create_item(unselected, "task", _LONG)).item
    service_with(project.squad_dir, override_toml(_TASK, (entry,)))

    created = await invoke(["create", "task", _LONG, "--author", "manager"])
    assert created.exit_code == create_exit, created.output
    updated = await invoke(["task", str(existing.sequence_id), "update", "--add-label", "x"])
    assert updated.exit_code == create_exit, updated.output
    fixed = await invoke(["task", str(existing.sequence_id), "update", "--title", "short"])
    assert fixed.exit_code == 0, fixed.output


async def test_lint_refuses_a_missing_threshold_and_a_roster_selection(project, invoke) -> None:
    write_override(project.squad_dir, '[items.task]\nvalidators = ["item_title_max"]\n')
    missing = await invoke(["workflow", "lint"])
    assert missing.exit_code == 1, missing.output
    assert "required" in missing.output

    write_override(project.squad_dir, '[items.role]\nvalidators = ["item_title_max:80"]\n')
    roster = await invoke(["workflow", "lint"])
    assert roster.exit_code == 1, roster.output
    assert "roster" in roster.output
