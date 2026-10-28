"""`sq blocked` (open items waiting on another open item) and `sq workload` (open and closed work
per assignee)."""

import json

import pytest

from tests.cli._readable import init_readable, lines

pytestmark = pytest.mark.anyio


@pytest.fixture
def readable(copy_squad):
    return copy_squad("readable", init_readable)


async def _run(invoke, *args: str) -> tuple[int, list[str]]:
    result = await invoke(list(args))
    return result.exit_code, lines(result.output)


async def test_blocked_names_each_waiting_item_and_what_it_waits_on(readable, invoke) -> None:
    assert await _run(invoke, "blocked") == (
        0,
        ["TASK-4 Rank results (Draft)", "    blocked by TASK-3 Parse queries (InProgress)"],
    )


async def test_blocked_says_when_nothing_is_blocked(populated_project, invoke) -> None:
    assert await _run(invoke, "blocked") == (0, ["nothing blocked"])


@pytest.mark.covers("blocked", "--json")
async def test_blocked_json_prints_one_object_per_waiting_item(readable, invoke) -> None:
    result = await invoke(["blocked", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == [
        {
            "id": "TASK-4",
            "title": "Rank results",
            "blockers": [{"id": "TASK-3", "title": "Parse queries", "status": "InProgress"}],
        }
    ]


async def test_workload_counts_each_assignees_items_and_sub_entities(readable, invoke) -> None:
    assert await _run(invoke, "workload") == (
        0,
        [
            "Assignee      Open  Closed  Total  Sub Open  Sub Closed  Sub Total",
            "(unassigned)  3     0       3      3         1           4",
            "manager       2     1       3      1         0           1",
        ],
    )


@pytest.mark.covers("workload", "--json")
async def test_workload_json_prints_one_object_per_assignee(readable, invoke) -> None:
    result = await invoke(["workload", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == [
        {
            "assignee": None,
            "open": 3,
            "closed": 0,
            "total": 3,
            "subentity_open": 3,
            "subentity_closed": 1,
            "subentity_total": 4,
        },
        {
            "assignee": "manager",
            "open": 2,
            "closed": 1,
            "total": 3,
            "subentity_open": 1,
            "subentity_closed": 0,
            "subentity_total": 1,
        },
    ]
