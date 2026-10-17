"""`blocked_has_blocker` at the CLI: `sq check` exits 0 at `warn` and 3 at `@error` and shows the
finding in text and `--json`; `sq task <n> status Blocked` is refused (exit 1) only at `@error`
until an edge exists on the item or on another item; `ref rm` then `sq check` reports the item;
and `sq workflow lint` refuses the check wherever it cannot fire.
"""

import json

import pytest

from _helpers import create_item
from _selection_table import TypeRow, override_toml, service_with, write_override
from squads._workflow._loader import lint_workflow_spec

pytestmark = pytest.mark.anyio

_TASK = TypeRow("task", "task")
_MESSAGE = "no dependency edge is recorded"


async def _stranded(project, entry: str | None):
    svc = service_with(project.squad_dir, override_toml(_TASK, ()))
    item = (await create_item(svc, "task", "waiting")).item
    other = (await create_item(svc, "task", "other")).item
    await svc.update(item.id, status="Blocked", force=True)
    entries = (entry,) if entry else ()
    service_with(project.squad_dir, override_toml(_TASK, entries))
    return item, other


@pytest.mark.parametrize(
    ("entry", "check_exit", "level"),
    [
        (None, 0, None),
        ("blocked_has_blocker", 0, "warn"),
        ("blocked_has_blocker@warn", 0, "warn"),
        ("blocked_has_blocker@error", 3, "error"),
    ],
)
async def test_check_reports_at_the_selected_level_with_its_exit_code(
    project, invoke, entry: str | None, check_exit: int, level: str | None
) -> None:
    await _stranded(project, entry)
    checked = await invoke(["check"])
    assert checked.exit_code == check_exit, checked.output
    assert (_MESSAGE in checked.output) is (level is not None)
    rows = json.loads((await invoke(["check", "--json"])).output)
    levels = [r["level"] for r in rows if _MESSAGE in r.get("message", "")]
    assert levels == ([level] if level else [])


@pytest.mark.parametrize(
    ("entry", "move_exit"), [("blocked_has_blocker", 0), ("blocked_has_blocker@error", 1)]
)
async def test_a_status_move_to_blocked_is_refused_only_at_error(
    project, invoke, entry: str, move_exit: int
) -> None:
    svc = service_with(project.squad_dir, override_toml(_TASK, (entry,)))
    item = (await create_item(svc, "task", "t")).item
    await svc.update(item.id, status="InProgress", force=True)
    moved = await invoke(["task", str(item.sequence_id), "status", "Blocked"])
    assert moved.exit_code == move_exit, moved.output
    if move_exit:
        assert _MESSAGE in moved.output


@pytest.mark.parametrize("edge", ["own", "incoming"])
async def test_the_status_move_is_accepted_once_the_edge_exists_on_either_item(
    project, invoke, edge: str
) -> None:
    svc = service_with(project.squad_dir, override_toml(_TASK, ("blocked_has_blocker@error",)))
    item = (await create_item(svc, "task", "t")).item
    other = (await create_item(svc, "task", "other")).item
    await svc.update(item.id, status="InProgress", force=True)
    refused = await invoke(["task", str(item.sequence_id), "status", "Blocked"])
    assert refused.exit_code == 1, refused.output
    if edge == "own":
        added = await invoke(
            ["task", str(item.sequence_id), "ref", "add", other.id, "--kind", "depends-on"]
        )
    else:
        added = await invoke(
            ["task", str(other.sequence_id), "ref", "add", item.id, "--kind", "blocks"]
        )
    assert added.exit_code == 0, added.output
    moved = await invoke(["task", str(item.sequence_id), "status", "Blocked"])
    assert moved.exit_code == 0, moved.output
    assert (await invoke(["check"])).exit_code == 0


async def test_removing_the_edge_is_reported_by_check_and_refuses_the_next_write(
    project, invoke
) -> None:
    svc = service_with(project.squad_dir, override_toml(_TASK, ("blocked_has_blocker@error",)))
    item = (await create_item(svc, "task", "t")).item
    other = (await create_item(svc, "task", "other")).item
    await svc.add_ref(item.id, other.id, kind="depends-on")
    await svc.update(item.id, status="Blocked", force=True)
    assert (await invoke(["check"])).exit_code == 0

    removed = await invoke(["task", str(item.sequence_id), "ref", "rm", other.id])
    assert removed.exit_code == 0, removed.output
    checked = await invoke(["check"])
    assert checked.exit_code == 3, checked.output
    assert _MESSAGE in checked.output
    touched = await invoke(["task", str(item.sequence_id), "update", "--add-label", "touched"])
    assert touched.exit_code == 1, touched.output


@pytest.mark.parametrize(
    ("override", "fragment"),
    [
        ('[items.review]\nvalidators = ["blocked_has_blocker"]\n', "blocked = true"),
        ('[items.role]\nvalidators = ["blocked_has_blocker"]\n', "roster type"),
        ('[items.task]\nvalidators = ["blocked_has_blocker:blocked"]\n', "takes no param"),
        (
            '[selected]\nref_kinds = ["related", "implements", "fixes", "addresses", "supersedes", '
            '"duplicates", "scopes", "targets"]\n\n'
            '[items.task]\nvalidators = ["blocked_has_blocker"]\n',
            'role = "dependency"',
        ),
    ],
    ids=["no-blocked-status", "roster-type", "parameter", "no-dependency-kind"],
)
async def test_lint_refuses_the_check_wherever_it_cannot_fire(
    project, invoke, override: str, fragment: str
) -> None:
    write_override(project.squad_dir, override)
    linted = await invoke(["workflow", "lint"])
    assert linted.exit_code == 1, linted.output
    found = " ".join(
        f"{location} {message}"
        for level, location, message, *_ in lint_workflow_spec(project.squad_dir)
        if level == "error"
    )
    assert "blocked_has_blocker" in found
    assert fragment in found
