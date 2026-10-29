"""`sq blocked` (open items waiting on another open item) and `sq workload` (open and closed work
per assignee)."""

import pytest

from tests._readable import init_readable, lines
from tests.cli._output import json_text

pytestmark = pytest.mark.anyio

LOW = {"label": "Priority", "badge": "🟢 low", "badge_label": "🟢 Low"}


@pytest.fixture
def readable(copy_squad):
    return copy_squad("readable", init_readable)


async def _run(invoke, *args: str) -> tuple[int, list[str]]:
    result = await invoke(list(args))
    return result.exit_code, lines(result.output)


@pytest.mark.covers("blocked")
async def test_blocked_names_each_waiting_item_and_what_it_waits_on(readable, invoke) -> None:
    assert await _run(invoke, "blocked") == (
        0,
        ["TASK-4 Rank results (Draft)", "    blocked by TASK-3 Parse queries (InProgress)"],
    )


@pytest.mark.covers("blocked")
async def test_blocked_says_when_nothing_is_blocked(populated_project, invoke) -> None:
    assert await _run(invoke, "blocked") == (0, ["nothing blocked"])


@pytest.mark.covers("blocked", "--json")
async def test_blocked_json_prints_one_object_per_waiting_item(readable, invoke) -> None:
    result = await invoke(["blocked", "--json"])
    assert result.exit_code == 0, result.output
    # Compared as text, so the key order is held as well as the content.
    assert result.output == json_text(
        [
            {
                "id": "TASK-4",
                "title": "Rank results",
                "blockers": [{"id": "TASK-3", "title": "Parse queries", "status": "InProgress"}],
                "display": {
                    "type": "Task",
                    "status": {"badge": "⚪ Draft", "intent": "neutral"},
                    "badges": {"priority": LOW},
                    "assignee": None,
                    "status_code": "Draft",
                },
            }
        ]
    )


@pytest.mark.covers("workload")
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
    assert result.output == json_text(
        [
            {
                "assignee": None,
                "open": 3,
                "closed": 0,
                "total": 3,
                "subentity_open": 3,
                "subentity_closed": 1,
                "subentity_total": 4,
                "display": {"assignee": "(unassigned)"},
            },
            {
                "assignee": "manager",
                "open": 2,
                "closed": 1,
                "total": 3,
                "subentity_open": 1,
                "subentity_closed": 0,
                "subentity_total": 1,
                "display": {"assignee": "manager"},
            },
        ]
    )
