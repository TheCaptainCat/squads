"""`sq inbox` (the open items whose discussion mentions a slug) and `sq mine` (the items assigned
to a slug, directly or through a sub-entity)."""

import json

import pytest

from tests._readable import init_readable_with_operator, lines
from tests.cli._output import json_text

pytestmark = pytest.mark.anyio

MANAGER_ROWS = [
    "ID      Type     Status      Priority   Title        Parent  Assignee  Matched",
    "FEAT-2  feature  Draft       🟠 high    Search               manager",
    "TASK-3  task     InProgress  🔴 urgent  Parse        FEAT-2  manager",
    "                                        queries",
    "REV-7   review   Requested              Review the                     F1 (Open)",
    "                                        parser",
]
CLOSED_ROW = [
    "BUG-6   bug      Verified    🟡 medium  Empty query          manager",
    "                                        crash",
]


@pytest.fixture
def readable(copy_squad):
    return copy_squad("readable-operator", init_readable_with_operator)


async def _run(invoke, *args: str) -> tuple[int, list[str]]:
    result = await invoke(list(args))
    return result.exit_code, lines(result.output)


@pytest.mark.covers("inbox", "ROLE")
async def test_inbox_lists_the_open_items_that_mention_the_slug(readable, invoke) -> None:
    assert await _run(invoke, "inbox", "manager") == (
        0,
        ["TASK-3 Parse queries (InProgress)", "    - @manager please look at the tokeniser"],
    )
    assert await _run(invoke, "inbox", "op-pierre") == (
        0,
        ["REV-7 Review the parser (Requested)", "    - @op-pierre what is your view?"],
    )


@pytest.mark.covers("inbox", "ROLE")
async def test_inbox_says_when_nothing_mentions_the_slug(populated_project, invoke) -> None:
    assert await _run(invoke, "inbox", "manager") == (0, ["nothing for @manager"])


@pytest.mark.covers("inbox", "ROLE")
async def test_inbox_refuses_a_slug_no_roster_entry_has(readable, invoke) -> None:
    assert await _run(invoke, "inbox", "ghost") == (
        1,
        ["error: unknown slug 'ghost'; valid slugs: manager, op-pierre"],
    )


@pytest.mark.covers("inbox", "--json")
async def test_inbox_json_prints_one_object_per_item_with_the_mentioning_lines(
    readable, invoke
) -> None:
    result = await invoke(["inbox", "op-pierre", "--json"])
    assert result.exit_code == 0, result.output
    # Compared as text, so the key order is held as well as the content.
    expected = [
        {
            "id": "REV-7",
            "title": "Review the parser",
            "lines": ["- @op-pierre what is your view?"],
            "regions": [None],
            "hashes": ["297f6f158ac5d9ac7bd3dd38efc678ac6c5635d20298f4b553df17fef5dd8c4a"],
            "display": {
                "type": "Review",
                "status": {"badge": "⚪ Requested", "intent": "neutral"},
                "badges": {},
                "assignee": None,
                "status_code": "Requested",
            },
        }
    ]
    assert result.output == json.dumps(expected, indent=2) + "\n"


@pytest.mark.covers("mine", "ROLE")
async def test_mine_lists_the_open_items_assigned_directly_or_through_a_sub_entity(
    readable, invoke
) -> None:
    assert await _run(invoke, "mine", "manager") == (0, MANAGER_ROWS)


@pytest.mark.covers("mine", "ROLE")
async def test_mine_says_when_nothing_is_assigned(readable, invoke) -> None:
    assert await _run(invoke, "mine", "op-pierre") == (0, ["nothing assigned to op-pierre"])


@pytest.mark.covers("mine", "ROLE")
async def test_mine_refuses_a_slug_no_roster_entry_has(readable, invoke) -> None:
    assert await _run(invoke, "mine", "ghost") == (
        1,
        ["error: unknown slug 'ghost'; valid slugs: manager, op-pierre"],
    )


@pytest.mark.covers("mine", "--all")
async def test_mine_all_includes_the_closed_items(readable, invoke) -> None:
    assert await _run(invoke, "mine", "manager", "--all") == (
        0,
        [*MANAGER_ROWS[:4], *CLOSED_ROW, *MANAGER_ROWS[4:]],
    )


@pytest.mark.covers("mine", "--json")
async def test_mine_json_prints_one_object_per_item_with_the_matching_sub_entities(
    readable, invoke
) -> None:
    result = await invoke(["mine", "manager", "--json"])
    assert result.exit_code == 0, result.output
    expected = [
        {
            "sequence_id": 2,
            "type": "feature",
            "title": "Search",
            "slug": "search",
            "status": "Draft",
            "description": "",
            "parent": None,
            "author": "manager",
            "assignee": "manager",
            "labels": ["core"],
            "refs": [],
            "subentities": [
                {
                    "local_id": "US1",
                    "title": "Query the index",
                    "status": "Todo",
                    "assignee": None,
                    "maps_to": None,
                    "deferred_to": None,
                },
                {
                    "local_id": "US2",
                    "title": "Rank the results",
                    "status": "Todo",
                    "assignee": None,
                    "maps_to": None,
                    "deferred_to": None,
                },
            ],
            "path": "features/FEAT-000002-search.md",
            "created_at": "2026-06-07T10:00:00Z",
            "updated_at": "2026-06-07T10:00:00Z",
            "created_session": None,
            "modified_session": None,
            "id": "FEAT-2",
            "priority": "high",
            "matched_subentities": [],
            "display": {
                "type": "Feature",
                "status": {"badge": "⚪ Draft", "intent": "neutral"},
                "badges": {
                    "priority": {"label": "Priority", "badge": "🟠 high", "badge_label": "🟠 High"}
                },
                "assignee": "Catherine Manager",
                "matched": "",
            },
        },
        {
            "sequence_id": 3,
            "type": "task",
            "title": "Parse queries",
            "slug": "parse-queries",
            "status": "InProgress",
            "description": "",
            "parent": "FEAT-2",
            "author": "manager",
            "assignee": "manager",
            "labels": ["parser"],
            "refs": [],
            "subentities": [
                {
                    "local_id": "ST1",
                    "title": "Tokenise the input",
                    "status": "Todo",
                    "assignee": None,
                    "maps_to": "US1",
                    "deferred_to": None,
                },
                {
                    "local_id": "ST2",
                    "title": "Parse the operators",
                    "status": "Done",
                    "assignee": None,
                    "maps_to": None,
                    "deferred_to": None,
                },
            ],
            "path": "tasks/TASK-000003-parse-queries.md",
            "created_at": "2026-06-07T10:00:00Z",
            "updated_at": "2026-06-07T10:00:00Z",
            "created_session": None,
            "modified_session": None,
            "id": "TASK-3",
            "priority": "urgent",
            "matched_subentities": [],
            "display": {
                "type": "Task",
                "status": {"badge": "🟡 In Progress", "intent": "positive"},
                "badges": {
                    "priority": {
                        "label": "Priority",
                        "badge": "🔴 urgent",
                        "badge_label": "🔴 Urgent",
                    }
                },
                "assignee": "Catherine Manager",
                "matched": "",
            },
        },
        {
            "sequence_id": 7,
            "type": "review",
            "title": "Review the parser",
            "slug": "review-the-parser",
            "status": "Requested",
            "description": "",
            "parent": None,
            "author": "manager",
            "assignee": None,
            "labels": ["parser"],
            "refs": ["BUG-6"],
            "subentities": [
                {
                    "local_id": "F1",
                    "title": "Unbounded recursion",
                    "status": "Open",
                    "assignee": "manager",
                    "maps_to": None,
                    "deferred_to": None,
                    "severity": "high",
                }
            ],
            "path": "reviews/REV-000007-review-the-parser.md",
            "created_at": "2026-06-07T10:00:00Z",
            "updated_at": "2026-06-07T10:00:00Z",
            "created_session": None,
            "modified_session": None,
            "id": "REV-7",
            "matched_subentities": [
                {
                    "local_id": "F1",
                    "kind": "finding",
                    "title": "Unbounded recursion",
                    "status": "Open",
                }
            ],
            "display": {
                "type": "Review",
                "status": {"badge": "⚪ Requested", "intent": "neutral"},
                "badges": {},
                "assignee": None,
                "matched": "F1 (Open)",
            },
        },
    ]
    # Compared as text, so the key order is held as well as the content.
    assert result.output == json_text(expected)
