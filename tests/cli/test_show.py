"""`sq show`: the item addressed by number or full ID in the rendered, raw, JSON, full and
comment forms."""

import json

import pytest

from tests.cli._readable import init_readable, lines

pytestmark = pytest.mark.anyio

PARSER_PANEL = [
    "╭──────────────────────────────────────────╮",
    "│ TASK-3  (task)                           │",
    "│ title: Parse queries                     │",
    "│ status: InProgress                       │",
    "│ priority: 🔴 urgent                      │",
    "│ parent: FEAT-2                           │",
    "│ author: manager                          │",
    "│ assignee: manager                        │",
    "│ labels: parser                           │",
    "│ file: tasks/TASK-000003-parse-queries.md │",
    "╰──────────────────────────────────────────╯",
    "",
    "## Description",
    "",
    "_TODO: describe this task._",
    "",
    "Subtask  Status  Assignee  Title                Story",
    "ST1      Todo              Tokenise the input   US1",
    "ST2      Done              Parse the operators",
]
PARSER_COMMENT = [
    "",
    "--- 59e0936 [2026-06-07T10:00:00Z] Catherine Manager (manager) ---",
    "- @manager please look at the tokeniser",
    "",
]


@pytest.fixture
def readable(copy_squad):
    return copy_squad("readable", init_readable)


async def _show(invoke, *args: str) -> tuple[int, list[str]]:
    result = await invoke(["show", *args])
    return result.exit_code, lines(result.output)


@pytest.mark.covers("show", "ID")
async def test_show_addresses_the_item_by_number_or_full_id(readable, invoke) -> None:
    by_number = await _show(invoke, "3")
    by_id = await _show(invoke, "TASK-3")
    assert by_number == (0, PARSER_PANEL)
    assert by_id == by_number


async def test_show_refuses_a_number_no_item_has(readable, invoke) -> None:
    assert await _show(invoke, "99") == (
        1,
        ["error: no item with number 99 (use a full ID like TYPE-99 or bare 99)"],
    )


async def test_show_refuses_a_full_id_whose_prefix_is_another_types(readable, invoke) -> None:
    assert await _show(invoke, "TASK-2") == (1, ["error: TASK-2 is FEAT-2 (feature)"])


async def test_show_refuses_text_that_is_not_an_id(readable, invoke) -> None:
    assert await _show(invoke, "ghost") == (
        1,
        ["error: invalid item id 'ghost' (use a bare number or a full ID like TYPE-NNNNNN)"],
    )


@pytest.mark.covers("show", "--raw")
async def test_raw_prints_plain_text_instead_of_the_rendered_panel(readable, invoke) -> None:
    assert await _show(invoke, "4", "--raw") == (
        0,
        [
            "# TASK-4 — Rank results",
            "",
            "- **status:** Draft",
            "- **priority:** 🟢 low",
            "- **parent:** FEAT-2",
            "- **author:** manager",
            "- **refs:** TASK-3 (depends-on), REV-7",
            "",
            "## Description",
            "",
            "_TODO: describe this task._",
        ],
    )


@pytest.mark.covers("show", "--comments")
async def test_comments_appends_the_discussion(readable, invoke) -> None:
    assert await _show(invoke, "3", "--comments") == (0, [*PARSER_PANEL, *PARSER_COMMENT])
    assert (await _show(invoke, "3"))[1] == PARSER_PANEL


@pytest.mark.covers("show", "--full")
async def test_full_adds_one_pane_per_sub_entity(readable, invoke) -> None:
    assert await _show(invoke, "7", "--full") == (
        0,
        [
            "╭───────────────────────────────────────────────╮",
            "│ REV-7  (review)                               │",
            "│ title: Review the parser                      │",
            "│ status: Requested                             │",
            "│ author: manager                               │",
            "│ labels: parser                                │",
            "│ refs: BUG-6                                   │",
            "│ file: reviews/REV-000007-review-the-parser.md │",
            "╰───────────────────────────────────────────────╯",
            "",
            "## Scope",
            "",
            "_TODO: what is under review?_",
            "",
            "Finding  Severity  Status  Assignee  Title",
            "F1       🟠 high   Open    manager   Unbounded recursion",
            "=== F1 — Unbounded recursion  🔴 Open  🟠 High  manager ===",
            "_Describe the finding, its impact, and a recommendation — free-form._",
            "",
        ],
    )
    assert "=== F1" not in "\n".join((await _show(invoke, "7"))[1])


@pytest.mark.covers("show", "--json")
async def test_json_prints_the_item_as_one_object(readable, invoke) -> None:
    result = await invoke(["show", "5", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {
        "sequence_id": 5,
        "type": "decision",
        "title": "Pick an index",
        "slug": "pick-an-index",
        "status": "Proposed",
        "description": "Why an inverted index",
        "parent": None,
        "author": "manager",
        "assignee": None,
        "priority": None,
        "severity": None,
        "labels": [],
        "refs": [],
        "subentities": [],
        "path": "adrs/ADR-000005-pick-an-index.md",
        "created_at": "2026-06-07T10:00:00Z",
        "updated_at": "2026-06-07T10:00:00Z",
        "created_session": None,
        "modified_session": None,
        "id": "ADR-5",
        "body": "## Context\n\n_TODO: what is the issue and the forces at play?_\n\n"
        "## Decision\n\n## Consequences",
        "views": {},
        "discussion": [],
        "badges": {},
    }
