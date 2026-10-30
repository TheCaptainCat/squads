"""`sq search`: the text, the type and status filters (each alone) and the hit forms."""

import json

import pytest

from tests._readable import init_readable, lines

pytestmark = pytest.mark.anyio


@pytest.fixture
def readable(copy_squad):
    return copy_squad("readable", init_readable)


async def _search(invoke, *args: str) -> tuple[int, list[str]]:
    result = await invoke(["search", *args])
    return result.exit_code, lines(result.output)


@pytest.mark.covers("search", "text")
async def test_search_lists_each_item_with_the_places_the_text_was_found(readable, invoke) -> None:
    assert await _search(invoke, "parse") == (
        0,
        [
            "TASK-3 Parse queries (InProgress)",
            "    title: Parse queries",
            "    subtask:ST2: ### ST2 — Parse the operators",
            "REV-7 Review the parser (Requested)",
            "    title: Review the parser",
        ],
    )


@pytest.mark.covers("search", "text")
async def test_search_ignores_the_case_of_the_text(readable, invoke) -> None:
    assert await _search(invoke, "PARSE") == await _search(invoke, "parse")


@pytest.mark.covers("search", "text")
async def test_search_finds_text_in_a_comment(readable, invoke) -> None:
    assert await _search(invoke, "tokeniser") == (
        0,
        [
            "TASK-3 Parse queries (InProgress)",
            "    discussion#1: [2026-06-07T10:00:00Z] Catherine Manager: - @manager please",
            "look at the tokeniser",
        ],
    )


@pytest.mark.covers("search", "text")
async def test_search_says_when_nothing_matches(readable, invoke) -> None:
    assert await _search(invoke, "zzz") == (0, ["no matches for zzz"])


@pytest.mark.covers("search", "text")
async def test_search_refuses_empty_text(readable, invoke) -> None:
    assert await _search(invoke, "") == (1, ["error: search needs a non-empty query"])


@pytest.mark.covers("search", "--type")
async def test_type_keeps_the_hits_of_one_type(readable, invoke) -> None:
    assert await _search(invoke, "parse", "--type", "review") == (
        0,
        ["REV-7 Review the parser (Requested)", "    title: Review the parser"],
    )


@pytest.mark.covers("search", "--type")
async def test_type_refuses_an_unknown_type(readable, invoke) -> None:
    assert await _search(invoke, "parse", "--type", "ghost") == (
        1,
        [
            "error: unknown type 'ghost' (one of: bug, contract, decision, epic, feature, "
            "guide, milestone, operator, review, role, skill, task)"
        ],
    )


@pytest.mark.covers("search", "--status")
async def test_status_keeps_the_hits_in_one_status(readable, invoke) -> None:
    assert await _search(invoke, "parse", "--status", "InProgress") == (
        0,
        [
            "TASK-3 Parse queries (InProgress)",
            "    title: Parse queries",
            "    subtask:ST2: ### ST2 — Parse the operators",
        ],
    )


@pytest.mark.covers("search", "--status")
async def test_status_refuses_an_unknown_status(readable, invoke) -> None:
    code, out = await _search(invoke, "parse", "--status", "Ghost")
    assert (code, out[0][:34]) == (1, "error: unknown status 'Ghost' (one")


@pytest.mark.covers("search", "--json")
async def test_json_prints_one_object_per_matching_item_with_its_hits(readable, invoke) -> None:
    result = await invoke(["search", "tokeniser", "--json"])
    assert result.exit_code == 0, result.output
    # Compared as text, so the key order is held as well as the content.
    expected = [
        {
            "id": "TASK-3",
            "title": "Parse queries",
            "type": "task",
            "status": "InProgress",
            "hits": [
                {
                    "region": "discussion#1",
                    "location": "discussion — comment 1 (Catherine Manager, 2026-06-07T10:00:00Z)",
                    "snippet": "[2026-06-07T10:00:00Z] Catherine Manager: "
                    "- @manager please look at the tokeniser",
                    "hash": "59e0936df6dbc55baeea2fde8e7ab1f24b7ea44e70ce7c413e1caeb45288bf93",
                }
            ],
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
            },
        }
    ]
    assert result.output == json.dumps(expected, indent=2) + "\n"
