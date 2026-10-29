"""`sq show`: the item addressed by number or full ID in the rendered, raw, JSON, full and
comment forms."""

import json

import pytest

from tests._profile import selected
from tests._readable import init_readable, lines

P = selected()

pytestmark = pytest.mark.anyio

PARSER_PANEL = [
    "╭──────────────────────────────────────────╮",
    f"│ {P.ref_prefix}-3  ({P.ref})                           │",
    "│ title: Parse queries                     │",
    "│ status: InProgress                       │",
    "│ priority: 🔴 urgent                      │",
    f"│ parent: {P.host_prefix}-2                           │",
    "│ author: manager                          │",
    "│ assignee: manager                        │",
    "│ labels: parser                           │",
    f"│ file: {P.ref_folder}/{P.ref_prefix}-000003-parse-queries.md │",
    "╰──────────────────────────────────────────╯",
    "",
    "## Description",
    "",
    f"_TODO: describe this {P.ref}._",
    "",
    "Subtask  Status  Assignee  Title                Story",
    f"{P.kind_prefix}1      Todo              Tokenise the input   {P.target_prefix}1",
    f"{P.kind_prefix}2      Done              Parse the operators",
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
@pytest.mark.bundled_only("the rendered panel and its notices are the bundled task's")
async def test_show_addresses_the_item_by_number_or_full_id(readable, invoke) -> None:
    by_number = await _show(invoke, "3")
    by_id = await _show(invoke, f"{P.ref_prefix}-3")
    assert by_number == (0, PARSER_PANEL)
    assert by_id == by_number


@pytest.mark.covers("show", "ID")
async def test_show_refuses_a_number_no_item_has(readable, invoke) -> None:
    assert await _show(invoke, "99") == (
        1,
        ["error: no item with number 99 (use a full ID like TYPE-99 or bare 99)"],
    )


@pytest.mark.covers("show", "ID")
@pytest.mark.bundled_only("the rendered panel and its notices are the bundled task's")
async def test_show_refuses_a_full_id_whose_prefix_is_another_types(readable, invoke) -> None:
    assert await _show(invoke, f"{P.ref_prefix}-2") == (
        1,
        [f"error: {P.ref_prefix}-2 is {P.host_prefix}-2 ({P.host})"],
    )


@pytest.mark.covers("show", "ID")
async def test_show_refuses_text_that_is_not_an_id(readable, invoke) -> None:
    assert await _show(invoke, "ghost") == (
        1,
        ["error: invalid item id 'ghost' (use a bare number or a full ID like TYPE-NNNNNN)"],
    )


@pytest.mark.covers("show", "--raw")
@pytest.mark.bundled_only("the rendered panel and its notices are the bundled task's")
async def test_raw_prints_plain_text_instead_of_the_rendered_panel(readable, invoke) -> None:
    assert await _show(invoke, "4", "--raw") == (
        0,
        [
            f"# {P.ref_prefix}-4 — Rank results",
            "",
            "- **status:** Draft",
            "- **priority:** 🟢 low",
            f"- **parent:** {P.host_prefix}-2",
            "- **author:** manager",
            f"- **refs:** {P.ref_prefix}-3 (depends-on), {P.third_prefix}-7",
            "",
            "## Description",
            "",
            f"_TODO: describe this {P.ref}._",
        ],
    )


@pytest.mark.covers("show", "--comments")
@pytest.mark.bundled_only("the rendered panel and its notices are the bundled task's")
async def test_comments_appends_the_discussion(readable, invoke) -> None:
    assert await _show(invoke, "3", "--comments") == (0, [*PARSER_PANEL, *PARSER_COMMENT])
    assert (await _show(invoke, "3"))[1] == PARSER_PANEL


@pytest.mark.covers("show", "--full")
@pytest.mark.bundled_only("the sub-entity panes are the bundled subtask's")
async def test_full_adds_one_pane_per_sub_entity(readable, invoke) -> None:
    assert await _show(invoke, "7", "--full") == (
        0,
        [
            "╭───────────────────────────────────────────────╮",
            f"│ {P.third_prefix}-7  ({P.third})                               │",
            "│ title: Review the parser                      │",
            "│ status: Requested                             │",
            "│ author: manager                               │",
            "│ labels: parser                                │",
            "│ refs: BUG-6                                   │",
            f"│ file: reviews/{P.third_prefix}-000007-{P.third}-the-parser.md │",
            "╰───────────────────────────────────────────────╯",
            "",
            "## Scope",
            "",
            f"_TODO: what is under {P.third}?_",
            "",
            "Finding  Severity  Status  Assignee  Title",
            "F1       🟠 high   Open    manager   Unbounded recursion",
            "=== F1 — Unbounded recursion  🔴 Open  🟠 High  manager ===",
            f"_Describe the {P.third_kind}, its impact, and a recommendation — free-form._",
            "",
        ],
    )
    assert "=== F1" not in "\n".join((await _show(invoke, "7"))[1])


@pytest.mark.covers("show", "--json")
async def test_json_prints_the_item_as_one_object(readable, invoke) -> None:
    result = await invoke(["show", "5", "--json"])
    assert result.exit_code == 0, result.output
    body = (
        "## Context\n\n_TODO: what is the issue and the forces at play?_\n\n"
        "## Decision\n\n## Consequences"
    )
    # Compared as text, so the key order is held as well as the content.
    expected = {
        "sequence_id": 5,
        "type": "decision",
        "title": "Pick an index",
        "slug": "pick-an-index",
        "status": "Proposed",
        "description": "Why an inverted index",
        "parent": None,
        "author": "manager",
        "assignee": None,
        "labels": [],
        "refs": [],
        "subentities": [],
        "path": "adrs/ADR-000005-pick-an-index.md",
        "created_at": "2026-06-07T10:00:00Z",
        "updated_at": "2026-06-07T10:00:00Z",
        "created_session": None,
        "modified_session": None,
        "id": "ADR-5",
        "body": body,
        "views": {},
        "discussion": [],
        "badges": {},
        "display": {
            "type": "Decision",
            "status": {"badge": "⚪ Proposed", "intent": "neutral"},
            "badges": {},
            "assignee": None,
            "body": body,
            "summary": None,
            "attributes": [],
        },
    }
    assert result.output == json.dumps(expected, indent=2) + "\n"


@pytest.mark.covers("show", "--json")
@pytest.mark.bundled_only("the rendered panel and its notices are the bundled task's")
async def test_json_prints_the_notices_on_stderr_and_only_the_object_on_stdout(
    project, invoke
) -> None:
    created = await invoke(["--at", "2026-06-01", "create", P.ref, "Parse", "--author", "manager"])
    assert created.exit_code == 0, created.output
    # No command writes an unrecognised working language, so the configuration is edited.
    config = project.root / ".squads.toml"
    text = config.read_text(encoding="utf-8")
    config.write_text(
        text.replace('working_language = "en"', 'working_language = "klingon!!"'), encoding="utf-8"
    )
    result = await invoke(["show", f"{P.ref_prefix}-2", "--json"])
    body = f"## Description\n\n_TODO: describe this {P.ref}._"
    expected = {
        "sequence_id": 2,
        "type": P.ref,
        "title": "Parse",
        "slug": "parse",
        "status": "Draft",
        "description": "",
        "parent": None,
        "author": "manager",
        "assignee": None,
        "labels": [],
        "refs": [],
        "subentities": [],
        "path": f"{P.ref_folder}/{P.ref_prefix}-000002-parse.md",
        "created_at": "2026-06-01T00:00:00Z",
        "updated_at": "2026-06-01T00:00:00Z",
        "created_session": None,
        "modified_session": None,
        "id": f"{P.ref_prefix}-2",
        "body": body,
        "views": {},
        "discussion": [],
        "badges": {},
        "display": {
            "type": "Task",
            "status": {"badge": "⚪ Draft", "intent": "neutral"},
            "badges": {},
            "assignee": None,
            "body": body,
            "summary": None,
            "attributes": [],
        },
    }
    assert (result.exit_code, result.stdout, result.stderr) == (
        0,
        json.dumps(expected, indent=2) + "\n",
        'warning: working_language "klingon!!" in .squads.toml is not a language tag squads '
        "recognises; using English (en)\n",
    )


@pytest.mark.covers("show", "ID")
async def test_a_refused_show_prints_the_notices_before_the_error(project, invoke) -> None:
    # No command writes an unrecognised working language, so the configuration is edited.
    config = project.root / ".squads.toml"
    text = config.read_text(encoding="utf-8")
    config.write_text(
        text.replace('working_language = "en"', 'working_language = "klingon!!"'), encoding="utf-8"
    )
    result = await invoke(["show", "99"])
    assert (result.exit_code, result.stdout, result.stderr) == (
        1,
        "",
        'warning: working_language "klingon!!" in .squads.toml is not a language tag squads '
        "recognises; using English (en)\n"
        "error: no item with number 99 (use a full ID like TYPE-99 or bare 99)\n",
    )
