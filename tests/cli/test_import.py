"""`sq import`: applying a JSONL file of events in one transaction, checking it first, and
refusing it whole."""

import json
from pathlib import Path
from typing import Any

import pytest

from tests.cli._squadwide import listed

pytestmark = pytest.mark.anyio

CREATE = {"op": "create", "type": "task", "title": "Imported", "handle": "t", "as": "manager"}
COMMENT = {"op": "comment", "target": "t", "message": "hello"}
PLAN = "  create: 1\n  comment: 1\nhandles:\n  t -> TASK-2\n"
ONLY_ROLE = [("ROLE-1", "Catherine Manager")]
IMPORTED = [*ONLY_ROLE, ("TASK-2", "Imported")]


def _events(*events: dict[str, Any]) -> str:
    """Write *events* as a JSONL file in the working directory; return its name."""
    Path("events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8"
    )
    return "events.jsonl"


@pytest.mark.covers("import", "FILE")
async def test_file_applies_its_events_and_reports_the_ids_it_gave(project, invoke) -> None:
    result = await invoke(["import", _events(CREATE, COMMENT)])
    assert (result.exit_code, result.output) == (0, PLAN + "imported 2 event(s)\n")
    assert await listed(invoke) == IMPORTED
    shown = await invoke(["task", "2", "show", "--json"])
    task = json.loads(shown.output)
    assert (task["author"], [c["body"] for c in task["discussion"]]) == ("manager", ["- hello"])


@pytest.mark.covers("import", "FILE")
async def test_file_dash_reads_the_events_from_standard_input(project, invoke) -> None:
    result = await invoke(["import", "-"], input=json.dumps(CREATE) + "\n")
    assert (result.exit_code, result.output) == (
        0,
        "  create: 1\nhandles:\n  t -> TASK-2\nimported 1 event(s)\n",
    )
    assert await listed(invoke) == IMPORTED


@pytest.mark.covers("import", "FILE")
async def test_file_refuses_a_path_that_cannot_be_read(project, invoke) -> None:
    result = await invoke(["import", "missing.jsonl"])
    assert (result.exit_code, result.output) == (
        1,
        "error: cannot read import file 'missing.jsonl': No such file or directory\n",
    )


async def test_file_is_required(project, invoke) -> None:
    result = await invoke(["import"])
    assert (result.exit_code, result.output) == (
        2,
        "Usage: sq import [OPTIONS] FILE\nTry 'sq import --help' for help.\n"
        "╭─ Error ──────────────────────────────────────────────────────────────────────╮\n"
        "│ Missing argument 'FILE'.                                                     │\n"
        "╰──────────────────────────────────────────────────────────────────────────────╯\n",
    )


@pytest.mark.covers("import", "--dry-run")
async def test_dry_run_prints_the_plan_and_writes_nothing(project, invoke) -> None:
    result = await invoke(["import", _events(CREATE, COMMENT), "--dry-run"])
    assert (result.exit_code, result.output) == (0, PLAN + "dry run — nothing written\n")
    assert await listed(invoke) == ONLY_ROLE


@pytest.mark.covers("import", "--as")
async def test_as_attributes_an_event_that_names_no_actor(project, invoke) -> None:
    anonymous = {k: v for k, v in CREATE.items() if k != "as"}
    result = await invoke(["import", _events(anonymous), "--as", "manager"])
    assert result.exit_code == 0, result.output
    shown = await invoke(["task", "2", "show", "--json"])
    assert json.loads(shown.output)["author"] == "manager"


async def test_an_event_with_no_actor_is_refused_without_as(project, invoke) -> None:
    anonymous = {k: v for k, v in CREATE.items() if k != "as"}
    result = await invoke(["import", _events(anonymous)])
    assert (result.exit_code, result.output) == (
        1,
        "line 1: no actor: missing 'as'\n1 issue(s) found — nothing written.\n",
    )
    assert await listed(invoke) == ONLY_ROLE


@pytest.mark.covers("import", "--as")
async def test_as_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    anonymous = {k: v for k, v in CREATE.items() if k != "as"}
    result = await invoke(["import", _events(anonymous), "--as", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "line 1: author 'nobody' is not a registered role or operator — register it first\n"
        "1 issue(s) found — nothing written.\n",
    )


@pytest.mark.covers("import", "--json")
async def test_json_prints_the_plan_and_the_outcome_of_an_applied_file(project, invoke) -> None:
    result = await invoke(["import", _events(CREATE, COMMENT), "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {
        "op_counts": {"create": 1, "comment": 1},
        "handle_to_id": {"t": "TASK-2"},
        "handle_to_sub": {},
        "issues": [],
        "ok": True,
        "applied": True,
        "dry_run": False,
        "created_ids": ["TASK-2"],
        "warnings": [],
    }


@pytest.mark.covers("import", "--dry-run", "--json")
async def test_json_with_dry_run_reports_the_plan_as_not_applied(project, invoke) -> None:
    result = await invoke(["import", _events(CREATE, COMMENT), "--dry-run", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert (payload["applied"], payload["dry_run"], payload["created_ids"]) == (False, True, [])
    assert payload["handle_to_id"] == {"t": "TASK-2"}
    assert await listed(invoke) == ONLY_ROLE


@pytest.mark.covers("import", "--json")
async def test_json_lists_every_refusal_by_line_and_exits_1(project, invoke) -> None:
    result = await invoke(
        [
            "import",
            _events(CREATE, {"op": "status", "target": "TASK-99", "status": "Ready"}),
            "--json",
        ]
    )
    assert result.exit_code == 1
    assert json.loads(result.output) == {
        "op_counts": {"create": 1, "status": 1},
        "handle_to_id": {"t": "TASK-2"},
        "handle_to_sub": {},
        "issues": [{"line": 2, "message": "no item 'TASK-99' in the index"}],
        "ok": False,
        "applied": False,
        "dry_run": False,
        "created_ids": [],
        "warnings": [],
    }


@pytest.mark.covers("import", "FILE")
async def test_a_refused_line_leaves_the_valid_events_before_it_unapplied(project, invoke) -> None:
    events = _events(
        CREATE, {"op": "nope"}, {"op": "status", "target": "TASK-99", "status": "Ready"}
    )
    result = await invoke(["import", events])
    assert result.exit_code == 1
    assert result.output.splitlines()[1:] == [
        "line 3: no item 'TASK-99' in the index",
        "2 issue(s) found — nothing written.",
    ]
    assert await listed(invoke) == ONLY_ROLE


@pytest.mark.covers("import", "FILE")
async def test_an_event_refused_while_applying_undoes_the_events_before_it(project, invoke) -> None:
    events = _events(
        CREATE,
        {"op": "body", "target": "t", "body": "one"},
        {"op": "body", "target": "t", "body": "two"},
    )
    result = await invoke(["import", events])
    assert (result.exit_code, result.output) == (
        1,
        "error: TASK-2 already has a body (1 line); setting one would discard it:\n\n    one\n\n"
        "Nothing was written. Add to it with `--append`, or pass `--force` to replace it.\n",
    )
    assert await listed(invoke) == ONLY_ROLE
