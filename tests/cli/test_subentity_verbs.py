"""The sub-entity verbs, tested on `task subtask`: the `<kind>` group's `LOCAL-ID` argument, the
`add-<kind>` and plural listing verbs, and `show`, `update`, `body` and `remove`. `--severity` and
`--deferred-to` are tested on `review finding`, the only host that carries them.

Every other sub-entity kind and host is held by the verb-set parity guard, so nothing here repeats
per kind.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from tests.cli._populated import FEATURE, REVIEW, TASK

pytestmark = pytest.mark.anyio

TASK_FILE = "TASK-000003-build-the-query-parser.md"
REVIEW_FILE = "REV-000004-review-the-query-parser.md"
NO_BODY = "_Describe this subtask here — free-form paragraphs or bullet lists._"
NO_FINDING_BODY = "_Describe the finding, its impact, and a recommendation — free-form._"
UNKNOWN_STATUS = (
    "error: unknown status 'Nope' (one of: Accepted, Active, Approved, Archived, Blocked, "
    "Cancelled, ChangesRequested, Deferred, Deprecated, Done, Draft, Fixed, InProgress, InReview, "
    "Noted, Open, Proposed, Published, Ready, Rejected, Requested, Superseded, Todo, Verified, "
    "WontFix)\n"
)
UNKNOWN_SLUG = "error: unknown slug 'ghost'; valid slugs: manager\n"
ADDED_HINT = (
    '  set its body:  sq task 3 subtask ST{n} body -m "…"  (or --file body.md / --file -)\n'
)


def _write_file(name: str = "text.md", text: str = "From a file\n") -> None:
    Path(name).write_text(text, encoding="utf-8")


async def _ran(invoke, args: list[str], **kw: Any) -> tuple[int, str]:
    result = await invoke(args, **kw)
    return result.exit_code, result.output


async def _ok(invoke, args: list[str], **kw: Any) -> str:
    code, output = await _ran(invoke, args, **kw)
    assert code == 0, output
    return output


async def _subtask(invoke, local: int = 1, number: int = TASK) -> dict[str, Any]:
    return json.loads(
        await _ok(invoke, ["task", str(number), "subtask", str(local), "show", "--json"])
    )


async def _finding(invoke, local: int = 1) -> dict[str, Any]:
    return json.loads(
        await _ok(invoke, ["review", str(REVIEW), "finding", str(local), "show", "--json"])
    )


async def _create_task(invoke, *extra: str) -> int:
    """Create a task the populated feature does not parent and return its number."""
    output = await _ok(invoke, ["create", "task", "Loose end", "--author", "manager", *extra])
    return int(output.split("-")[1].split()[0])


async def _actors(invoke, target: str) -> list[tuple[str, str]]:
    """The (actor, sub-entity operation) pairs the reflog holds for *target*, oldest first."""
    entries = json.loads(
        await _ok(invoke, ["reflog", "--item", target, "--op", "subentity", "--json"])
    )
    return [(e["actor"], e["delta"]["op"]) for e in entries]


# --- the group: LOCAL-ID --------------------------------------------------------------------


@pytest.mark.covers("<type> <kind>", "LOCAL-ID")
async def test_the_group_addresses_a_subtask_by_number_or_local_id(
    populated_project, invoke
) -> None:
    by_number = await _subtask(invoke, 1)
    by_local_id = json.loads(
        await _ok(invoke, ["task", str(TASK), "subtask", "ST1", "show", "--json"])
    )
    by_lowercase = json.loads(
        await _ok(invoke, ["task", str(TASK), "subtask", "st1", "show", "--json"])
    )
    assert by_number == by_local_id == by_lowercase
    assert by_number["local_id"] == "ST1"


async def test_the_group_refuses_a_local_id_the_item_does_not_hold(
    populated_project, invoke
) -> None:
    assert await _ran(invoke, ["task", str(TASK), "subtask", "9", "show"]) == (
        1,
        "error: no subtask ST9 in TASK-3\n",
    )


# --- the plural listing ---------------------------------------------------------------------


@pytest.mark.covers("<type> <kinds>", "--json")
async def test_the_plural_listing_prints_every_subtask_as_json(populated_project, invoke) -> None:
    output = await _ok(invoke, ["task", str(TASK), "subtasks", "--json"])
    rows = [
        {
            "local_id": "ST1",
            "title": "Tokenise the input",
            "status": "Todo",
            "assignee": None,
            "severity": None,
            "story": "US1",
            "deferred_to": None,
            "display": _todo_display("US1"),
        },
        {
            "local_id": "ST2",
            "title": "Parse the operators",
            "status": "Todo",
            "assignee": None,
            "severity": None,
            "story": None,
            "deferred_to": None,
            "display": _todo_display(None),
        },
    ]
    # Compared as text, so the key order is held as well as the content.
    assert output == json.dumps(rows, indent=2) + "\n"


def _todo_display(story: str | None) -> dict[str, Any]:
    """The display of a subtask at Todo with no assignee."""
    return {
        "type": "Subtask",
        "status": {"badge": "⚪ Todo", "intent": "neutral"},
        "badges": {},
        "assignee": None,
        "story": story,
        "carrier_title": None,
    }


async def test_the_plural_listing_prints_a_table_of_subtasks(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "subtasks"]) == (
        0,
        "Subtask  Status  Assignee  Title                Story\n"
        "ST1      Todo              Tokenise the input   US1  \n"
        "ST2      Todo              Parse the operators       \n",
    )


# --- show -----------------------------------------------------------------------------------


@pytest.mark.covers("<type> <kind> show", "--json")
async def test_show_json_prints_the_subtask_as_one_object(populated_project, invoke) -> None:
    output = await _ok(invoke, ["task", str(TASK), "subtask", "1", "show", "--json"])
    kind = {"name": "subtask", "label": "Subtask", "plural": "subtasks", "heading": "Subtasks"}
    expected = {
        "local_id": "ST1",
        "title": "Tokenise the input",
        "status": "Todo",
        "assignee": None,
        "severity": None,
        "story": "US1",
        "deferred_to": None,
        "extra": {},
        "body": NO_BODY,
        "badges": {},
        "discussion": [],
        "display": {**_todo_display("US1"), "kind": kind, "discussion": None},
    }
    # Compared as text, so the key order is held as well as the content.
    assert output == json.dumps(expected, indent=2) + "\n"


async def test_show_prints_the_status_story_body_and_discussion(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "subtask", "1", "show"]) == (
        0,
        "ST1 — Tokenise the input  (subtask)\n"
        "  status: Todo   story: US1\n\n"
        f"{NO_BODY}\n\n"
        "Discussion\n(none)\n",
    )


# --- add-<kind> -----------------------------------------------------------------------------


@pytest.mark.covers("<type> add-<kind>", "TITLE")
async def test_add_scaffolds_a_todo_subtask_with_the_given_title(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "add-subtask", "Index the tokens"]) == (
        0,
        "added ST3 to TASK-3\n" + ADDED_HINT.format(n=3),
    )
    added = await _subtask(invoke, 3)
    assert (added["title"], added["status"], added["story"], added["body"]) == (
        "Index the tokens",
        "Todo",
        None,
        NO_BODY,
    )


@pytest.mark.covers("<type> add-<kind>", "--message")
async def test_add_message_writes_each_message_as_a_body_paragraph(
    populated_project, invoke
) -> None:
    await _ok(invoke, ["task", str(TASK), "add-subtask", "Index", "-m", "First", "-m", "Second"])
    assert (await _subtask(invoke, 3))["body"] == "First\n\nSecond"


@pytest.mark.covers("<type> add-<kind>", "--file")
async def test_add_file_writes_the_file_as_the_body(populated_project, invoke) -> None:
    _write_file()
    await _ok(invoke, ["task", str(TASK), "add-subtask", "Index", "--file", "text.md"])
    assert (await _subtask(invoke, 3))["body"] == "From a file"


async def test_add_file_reads_the_body_from_stdin_for_a_dash(populated_project, invoke) -> None:
    await _ok(
        invoke, ["task", str(TASK), "add-subtask", "Index", "--file", "-"], input="Piped in\n"
    )
    assert (await _subtask(invoke, 3))["body"] == "Piped in"


async def test_add_file_refuses_a_file_that_does_not_exist(populated_project, invoke) -> None:
    assert await _ran(
        invoke, ["task", str(TASK), "add-subtask", "Index", "--file", "missing.md"]
    ) == (
        1,
        "error: cannot read file 'missing.md': No such file or directory\n",
    )


@pytest.mark.covers("<type> add-<kind>", "--message", "--file")
async def test_add_refuses_message_with_file(populated_project, invoke) -> None:
    _write_file()
    out = await _ran(
        invoke, ["task", str(TASK), "add-subtask", "Index", "-m", "x", "--file", "text.md"]
    )
    assert out == (1, "error: provide the body via -m or --file, not both\n")


@pytest.mark.covers("<type> add-<kind>", "--status")
async def test_add_status_starts_the_subtask_in_that_status(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "add-subtask", "Index", "--status", "InProgress"])
    assert (await _subtask(invoke, 3))["status"] == "InProgress"


async def test_add_refuses_a_status_the_spec_does_not_declare(populated_project, invoke) -> None:
    out = await _ran(invoke, ["task", str(TASK), "add-subtask", "Index", "--status", "Nope"])
    assert out == (1, UNKNOWN_STATUS)


@pytest.mark.covers("<type> add-<kind>", "--assignee")
async def test_add_assignee_assigns_the_new_subtask(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "add-subtask", "Index", "--assignee", "manager"])
    assert (await _subtask(invoke, 3))["assignee"] == "manager"


async def test_add_refuses_an_assignee_no_roster_entry_has(populated_project, invoke) -> None:
    out = await _ran(invoke, ["task", str(TASK), "add-subtask", "Index", "--assignee", "ghost"])
    assert out == (1, UNKNOWN_SLUG)


@pytest.mark.covers("<type> add-<kind>", "--story")
async def test_add_story_maps_the_subtask_to_a_story_of_the_parent_feature(
    populated_project, invoke
) -> None:
    await _ok(invoke, ["task", str(TASK), "add-subtask", "Index", "--story", "US2"])
    await _ok(invoke, ["task", str(TASK), "add-subtask", "Rank", "--story", "1"])
    assert [(await _subtask(invoke, n))["story"] for n in (3, 4)] == ["US2", "US1"]


async def test_add_story_refuses_a_story_the_parent_feature_lacks(
    populated_project, invoke
) -> None:
    assert await _ran(invoke, ["task", str(TASK), "add-subtask", "Index", "--story", "US9"]) == (
        1,
        f"error: user story US9 not found in FEAT-{FEATURE}\n",
    )


async def test_add_story_is_resolved_against_the_parent_of_the_task_it_is_added_to(
    populated_project, invoke
) -> None:
    output = await _ok(invoke, ["create", "feature", "Indexing", "--author", "manager"])
    other = int(output.split("-")[1].split()[0])
    await _ok(invoke, ["feature", str(other), "add-story", "Only story"])
    loose = await _create_task(invoke, "--parent", str(other))
    assert await _ran(invoke, ["task", str(loose), "add-subtask", "Index", "--story", "US2"]) == (
        1,
        f"error: user story US2 not found in FEAT-{other}\n",
    )


async def test_add_story_refuses_a_task_with_no_feature_parent(populated_project, invoke) -> None:
    loose = await _create_task(invoke)
    assert await _ran(invoke, ["task", str(loose), "add-subtask", "Index", "--story", "US1"]) == (
        1,
        f"error: TASK-{loose} has no feature parent; set one before mapping a subtask to US1\n",
    )


@pytest.mark.covers("<type> add-<kind>", "--json")
async def test_add_json_prints_where_the_body_region_was_written(populated_project, invoke) -> None:
    payload = json.loads(await _ok(invoke, ["task", str(TASK), "add-subtask", "Index", "--json"]))
    assert Path(payload.pop("path")).name == TASK_FILE
    assert payload == {
        "local_id": "ST3",
        "region": "subtask:ST3:body",
        "start_line": 64,
        "end_line": 66,
    }


@pytest.mark.covers("<type> add-<kind>", "--as")
async def test_add_attributes_the_new_subtask_to_the_named_slug(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "add-subtask", "Index", "--as", "manager"])
    await _ok(invoke, ["task", str(TASK), "add-subtask", "Rank"])
    assert (await _actors(invoke, "TASK-3"))[-2:] == [("manager", "add"), ("system", "add")]


async def test_add_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "add-subtask", "Index", "--as", "ghost"]) == (
        1,
        UNKNOWN_SLUG,
    )


@pytest.mark.covers("<type> add-<kind>", "--severity")
async def test_add_severity_sets_the_severity_of_a_new_finding(populated_project, invoke) -> None:
    out = await _ran(
        invoke, ["review", str(REVIEW), "add-finding", "Dead branch", "--severity", "low"]
    )
    assert out == (
        0,
        "added F3 to REV-4\n"
        '  set its body:  sq review 4 finding F3 body -m "…"  (or --file body.md / --file -)\n',
    )
    assert (await _finding(invoke, 3))["severity"] == "low"


async def test_add_severity_defaults_to_medium_when_not_given(populated_project, invoke) -> None:
    await _ok(invoke, ["review", str(REVIEW), "add-finding", "Dead branch"])
    assert (await _finding(invoke, 3))["severity"] == "medium"


async def test_add_refuses_a_severity_outside_the_declared_ones(populated_project, invoke) -> None:
    out = await _ran(
        invoke, ["review", str(REVIEW), "add-finding", "Dead branch", "--severity", "Bad"]
    )
    assert out == (1, "error: unknown severity 'Bad' (one of: critical, high, medium, low, info)\n")


@pytest.mark.covers("<type> add-<kind>", "--deferred-to")
async def test_add_deferred_to_names_the_item_that_carries_a_deferred_finding(
    populated_project, invoke
) -> None:
    await _ok(
        invoke,
        [
            "review",
            str(REVIEW),
            "add-finding",
            "Later",
            "--status",
            "Deferred",
            "--deferred-to",
            "3",
        ],
    )
    deferred = await _finding(invoke, 3)
    assert (deferred["status"], deferred["deferred_to"]) == ("Deferred", "TASK-3")


async def test_add_refuses_deferred_to_on_a_finding_that_is_not_deferred(
    populated_project, invoke
) -> None:
    out = await _ran(invoke, ["review", str(REVIEW), "add-finding", "Later", "--deferred-to", "3"])
    assert out == (
        1,
        "error: a carrier (--deferred-to / deferred_to) applies to a finding in a deferred status "
        "(Deferred); F3 is Open\n",
    )


async def test_add_refuses_a_deferred_to_that_is_not_an_item_id(populated_project, invoke) -> None:
    out = await _ran(
        invoke,
        [
            "review",
            str(REVIEW),
            "add-finding",
            "Later",
            "--status",
            "Deferred",
            "--deferred-to",
            "x",
        ],
    )
    assert out == (
        1,
        "error: invalid item id 'x' (use a bare number or a full ID like TYPE-NNNNNN)\n",
    )


async def test_add_refuses_a_deferred_to_no_item_has(populated_project, invoke) -> None:
    out = await _ran(
        invoke,
        [
            "review",
            str(REVIEW),
            "add-finding",
            "Later",
            "--status",
            "Deferred",
            "--deferred-to",
            "99",
        ],
    )
    assert out == (1, "error: no item with number 99 (use a full ID like TYPE-99 or bare 99)\n")


# --- update ---------------------------------------------------------------------------------


@pytest.mark.covers("<type> <kind> update", "--title")
async def test_update_replaces_the_title(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "subtask", "1", "update", "--title", "Lex"]) == (
        0,
        "updated TASK-3 ST1\n",
    )
    assert (await _subtask(invoke, 1))["title"] == "Lex"


@pytest.mark.covers("<type> <kind> update", "--status")
async def test_update_moves_to_a_status_the_lifecycle_allows(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "subtask", "1", "update", "--status", "InProgress"])
    assert (await _subtask(invoke, 1))["status"] == "InProgress"


async def test_update_refuses_a_status_the_spec_does_not_declare(populated_project, invoke) -> None:
    out = await _ran(invoke, ["task", str(TASK), "subtask", "1", "update", "--status", "Nope"])
    assert out == (1, UNKNOWN_STATUS)


@pytest.mark.covers("<type> <kind> update", "--force")
async def test_update_force_makes_a_move_the_lifecycle_refuses(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "subtask", "1", "update", "--status", "Done"])
    refused = await _ran(
        invoke, ["task", str(TASK), "subtask", "1", "update", "--status", "Cancelled"]
    )
    assert refused == (
        1,
        "error: subtask ST1 cannot move Done → Cancelled (use --force to override)\n",
    )
    assert (await _subtask(invoke, 1))["status"] == "Done"
    forced = ["task", str(TASK), "subtask", "1", "update", "--status", "Cancelled", "--force"]
    assert await _ran(invoke, forced) == (0, "updated TASK-3 ST1\n")
    assert (await _subtask(invoke, 1))["status"] == "Cancelled"


@pytest.mark.covers("<type> <kind> update", "--assignee")
async def test_update_assignee_assigns_the_subtask(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "subtask", "1", "update", "--assignee", "manager"])
    assert (await _subtask(invoke, 1))["assignee"] == "manager"


async def test_update_refuses_an_assignee_no_roster_entry_has(populated_project, invoke) -> None:
    out = await _ran(invoke, ["task", str(TASK), "subtask", "1", "update", "--assignee", "ghost"])
    assert out == (1, UNKNOWN_SLUG)


@pytest.mark.covers("<type> <kind> update", "--clear-assignee")
async def test_update_clear_assignee_unassigns_the_subtask(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "subtask", "1", "update", "--assignee", "manager"])
    out = await _ran(invoke, ["task", str(TASK), "subtask", "1", "update", "--clear-assignee"])
    assert out == (0, "updated TASK-3 ST1\n")
    assert (await _subtask(invoke, 1))["assignee"] is None


async def test_update_clear_assignee_says_so_when_there_is_none_to_clear(
    populated_project, invoke
) -> None:
    out = await _ran(invoke, ["task", str(TASK), "subtask", "1", "update", "--clear-assignee"])
    assert out == (0, "TASK-3 ST1 has no assignee to clear\n")


@pytest.mark.covers("<type> <kind> update", "--assignee", "--clear-assignee")
async def test_update_refuses_assignee_with_clear_assignee(populated_project, invoke) -> None:
    out = await _ran(
        invoke,
        ["task", str(TASK), "subtask", "2", "update", "--assignee", "manager", "--clear-assignee"],
    )
    assert out == (1, "error: use --assignee or --clear-assignee, not both\n")


@pytest.mark.covers("<type> <kind> update", "--story")
async def test_update_story_maps_the_subtask_to_a_story_of_the_parent_feature(
    populated_project, invoke
) -> None:
    await _ok(invoke, ["task", str(TASK), "subtask", "1", "update", "--story", "US2"])
    await _ok(invoke, ["task", str(TASK), "subtask", "2", "update", "--story", "1"])
    assert [(await _subtask(invoke, n))["story"] for n in (1, 2)] == ["US2", "US1"]


async def test_update_story_refuses_a_story_the_parent_feature_lacks(
    populated_project, invoke
) -> None:
    out = await _ran(invoke, ["task", str(TASK), "subtask", "1", "update", "--story", "US9"])
    assert out == (1, f"error: user story US9 not found in FEAT-{FEATURE}\n")


async def test_update_story_is_resolved_against_the_parent_of_the_task_it_belongs_to(
    populated_project, invoke
) -> None:
    output = await _ok(invoke, ["create", "feature", "Indexing", "--author", "manager"])
    other = int(output.split("-")[1].split()[0])
    await _ok(invoke, ["feature", str(other), "add-story", "Only story"])
    loose = await _create_task(invoke, "--parent", str(other))
    await _ok(invoke, ["task", str(loose), "add-subtask", "Index"])
    assert await _ran(invoke, ["task", str(loose), "subtask", "1", "update", "--story", "US2"]) == (
        1,
        f"error: user story US2 not found in FEAT-{other}\n",
    )
    await _ok(invoke, ["task", str(loose), "subtask", "1", "update", "--story", "US1"])
    assert (await _subtask(invoke, 1, loose))["story"] == "US1"


async def test_update_story_refuses_a_task_with_no_feature_parent(
    populated_project, invoke
) -> None:
    loose = await _create_task(invoke)
    await _ok(invoke, ["task", str(loose), "add-subtask", "Index"])
    assert await _ran(invoke, ["task", str(loose), "subtask", "1", "update", "--story", "US1"]) == (
        1,
        f"error: TASK-{loose} has no feature parent; set one before mapping a subtask to US1\n",
    )


@pytest.mark.covers("<type> <kind> update", "--no-story")
async def test_update_no_story_clears_the_story_mapping(populated_project, invoke) -> None:
    out = await _ran(invoke, ["task", str(TASK), "subtask", "1", "update", "--no-story"])
    assert out == (0, "updated TASK-3 ST1\n")
    assert (await _subtask(invoke, 1))["story"] is None


@pytest.mark.covers("<type> <kind> update", "--story", "--no-story")
async def test_update_refuses_story_with_no_story(populated_project, invoke) -> None:
    out = await _ran(
        invoke, ["task", str(TASK), "subtask", "1", "update", "--story", "US2", "--no-story"]
    )
    assert out == (1, "error: use --story or --no-story, not both\n")


@pytest.mark.covers("<type> <kind> update", "--as")
async def test_update_attributes_the_edit_to_the_named_slug(populated_project, invoke) -> None:
    await _ok(
        invoke, ["task", str(TASK), "subtask", "1", "update", "--title", "A", "--as", "manager"]
    )
    await _ok(invoke, ["task", str(TASK), "subtask", "1", "update", "--title", "B"])
    assert (await _actors(invoke, "TASK-3"))[-2:] == [("manager", "update"), ("system", "update")]


async def test_update_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    out = await _ran(
        invoke, ["task", str(TASK), "subtask", "1", "update", "--title", "T", "--as", "ghost"]
    )
    assert out == (1, UNKNOWN_SLUG)


async def test_update_refuses_a_call_that_changes_nothing(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "subtask", "1", "update"]) == (
        1,
        "error: nothing to update (pass at least one field, e.g. --title/--status)\n",
    )


@pytest.mark.covers("<type> <kind> update", "--severity")
async def test_update_severity_changes_the_severity_of_a_finding(populated_project, invoke) -> None:
    out = await _ran(invoke, ["review", str(REVIEW), "finding", "1", "update", "--severity", "low"])
    assert out == (0, "updated REV-4 F1\n")
    assert (await _finding(invoke, 1))["severity"] == "low"


async def test_update_severity_accepts_the_label_in_any_case(populated_project, invoke) -> None:
    await _ok(invoke, ["review", str(REVIEW), "finding", "2", "update", "--severity", "INFO"])
    assert (await _finding(invoke, 2))["severity"] == "info"


async def test_update_refuses_a_severity_outside_the_declared_ones(
    populated_project, invoke
) -> None:
    out = await _ran(
        invoke, ["review", str(REVIEW), "finding", "1", "update", "--severity", "bogus"]
    )
    assert out == (
        1,
        "error: unknown severity 'bogus' (one of: critical, high, medium, low, info)\n",
    )


@pytest.mark.covers("<type> <kind> update", "--deferred-to")
async def test_update_deferred_to_points_a_deferred_finding_at_another_item(
    populated_project, invoke
) -> None:
    deferring = ["review", str(REVIEW), "finding", "1", "update", "--status", "Deferred"]
    await _ok(invoke, [*deferring, "--deferred-to", "3"])
    assert (await _finding(invoke, 1))["deferred_to"] == "TASK-3"
    out = await _ran(
        invoke, ["review", str(REVIEW), "finding", "1", "update", "--deferred-to", "2"]
    )
    assert out == (0, "updated REV-4 F1\n")
    assert (await _finding(invoke, 1))["deferred_to"] == "FEAT-2"


async def test_update_refuses_deferred_to_on_a_finding_that_is_not_deferred(
    populated_project, invoke
) -> None:
    out = await _ran(
        invoke, ["review", str(REVIEW), "finding", "2", "update", "--deferred-to", "3"]
    )
    assert out == (
        1,
        "error: a carrier (--deferred-to / deferred_to) applies to a finding in a deferred status "
        "(Deferred); F2 is Open\n",
    )


async def test_update_refuses_a_deferred_to_that_is_not_an_item_id(
    populated_project, invoke
) -> None:
    out = await _ran(
        invoke,
        [
            "review",
            str(REVIEW),
            "finding",
            "1",
            "update",
            "--status",
            "Deferred",
            "--deferred-to",
            "x",
        ],
    )
    assert out == (
        1,
        "error: invalid item id 'x' (use a bare number or a full ID like TYPE-NNNNNN)\n",
    )


async def test_update_refuses_a_deferred_to_no_item_has(populated_project, invoke) -> None:
    out = await _ran(
        invoke,
        [
            "review",
            str(REVIEW),
            "finding",
            "1",
            "update",
            "--status",
            "Deferred",
            "--deferred-to",
            "99",
        ],
    )
    assert out == (1, "error: no item with number 99 (use a full ID like TYPE-99 or bare 99)\n")


# --- body -----------------------------------------------------------------------------------


@pytest.mark.covers("<type> <kind> body", "--message")
async def test_body_sets_each_message_as_a_paragraph(populated_project, invoke) -> None:
    out = await _ran(
        invoke, ["task", str(TASK), "subtask", "1", "body", "-m", "First", "-m", "Second"]
    )
    assert out == (0, "TASK-3 ST1: body set\n")
    assert (await _subtask(invoke, 1))["body"] == "First\n\nSecond"


async def test_body_refuses_a_call_with_no_text(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "subtask", "1", "body"]) == (
        1,
        "error: provide the body via -m (repeatable) or --file PATH ('-' for stdin)\n",
    )


@pytest.mark.covers("<type> <kind> body", "--file")
async def test_body_reads_the_text_from_a_file(populated_project, invoke) -> None:
    _write_file()
    out = await _ran(invoke, ["task", str(TASK), "subtask", "1", "body", "--file", "text.md"])
    assert out == (0, "TASK-3 ST1: body set\n")
    assert (await _subtask(invoke, 1))["body"] == "From a file"


async def test_body_reads_the_text_from_stdin_for_a_dash(populated_project, invoke) -> None:
    await _ok(
        invoke, ["task", str(TASK), "subtask", "1", "body", "--file", "-"], input="Piped in\n"
    )
    assert (await _subtask(invoke, 1))["body"] == "Piped in"


async def test_body_refuses_a_file_that_does_not_exist(populated_project, invoke) -> None:
    assert await _ran(
        invoke, ["task", str(TASK), "subtask", "1", "body", "--file", "missing.md"]
    ) == (
        1,
        "error: cannot read file 'missing.md': No such file or directory\n",
    )


@pytest.mark.covers("<type> <kind> body", "--message", "--file")
async def test_body_refuses_message_with_file(populated_project, invoke) -> None:
    _write_file()
    out = await _ran(
        invoke, ["task", str(TASK), "subtask", "1", "body", "-m", "Text", "--file", "text.md"]
    )
    assert out == (1, "error: provide the body via -m or --file, not both\n")


@pytest.mark.covers("<type> <kind> body", "--append")
async def test_body_append_adds_after_the_existing_body(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "subtask", "1", "body", "-m", "First"])
    out = await _ran(
        invoke, ["task", str(TASK), "subtask", "1", "body", "-m", "Second", "--append"]
    )
    assert out == (0, "TASK-3 ST1: body appended\n")
    assert (await _subtask(invoke, 1))["body"] == "First\n\nSecond"


@pytest.mark.covers("<type> <kind> body", "--force")
async def test_body_force_replaces_a_body_already_written(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "subtask", "1", "body", "-m", "First"])
    refused = await _ran(invoke, ["task", str(TASK), "subtask", "1", "body", "-m", "Second"])
    assert refused == (
        1,
        "error: TASK-3 ST1 already has a body (1 line); setting one would discard it:\n\n"
        "    First\n\n"
        "Nothing was written. Add to it with `--append`, or pass `--force` to replace it.\n",
    )
    forced = await _ran(
        invoke, ["task", str(TASK), "subtask", "1", "body", "-m", "Second", "--force"]
    )
    assert forced == (0, "TASK-3 ST1: body set\n")
    assert (await _subtask(invoke, 1))["body"] == "Second"


@pytest.mark.covers("<type> <kind> body", "--as")
async def test_body_attributes_the_edit_to_the_named_slug(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "subtask", "1", "body", "-m", "First", "--as", "manager"])
    await _ok(invoke, ["task", str(TASK), "subtask", "1", "body", "-m", "Second", "--append"])
    assert (await _actors(invoke, "TASK-3"))[-2:] == [("manager", "body"), ("system", "body")]


async def test_body_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    out = await _ran(
        invoke, ["task", str(TASK), "subtask", "1", "body", "-m", "x", "--as", "ghost"]
    )
    assert out == (1, UNKNOWN_SLUG)


# --- remove ---------------------------------------------------------------------------------


@pytest.mark.covers("<type> <kind> remove", "--yes")
async def test_remove_yes_deletes_the_subtask_without_asking(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "subtask", "1", "remove", "--yes"]) == (
        0,
        "removed subtask ST1 from TASK-3\n",
    )
    assert await _ran(invoke, ["task", str(TASK), "subtask", "1", "show"]) == (
        1,
        "error: no subtask ST1 in TASK-3\n",
    )


async def test_remove_asks_for_confirmation_and_keeps_the_subtask_when_declined(
    populated_project, invoke
) -> None:
    out = await _ran(invoke, ["task", str(TASK), "subtask", "1", "remove"], input="n\n")
    assert out == (1, "Remove subtask ST1 from TASK-3? This cannot be undone. [y/N]: n\nAborted.\n")
    assert (await _subtask(invoke, 1))["local_id"] == "ST1"


async def test_remove_deletes_the_subtask_when_confirmed(populated_project, invoke) -> None:
    out = await _ran(invoke, ["task", str(TASK), "subtask", "1", "remove"], input="y\n")
    assert out == (
        0,
        "Remove subtask ST1 from TASK-3? This cannot be undone. [y/N]: y\n"
        "removed subtask ST1 from TASK-3\n",
    )
    assert [
        row["local_id"]
        for row in json.loads(await _ok(invoke, ["task", str(TASK), "subtasks", "--json"]))
    ] == ["ST2"]


async def test_remove_refuses_a_subtask_the_item_does_not_hold(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "subtask", "7", "remove", "--yes"]) == (
        1,
        "error: no subtask ST7 in TASK-3\n",
    )


@pytest.mark.covers("<type> <kind> remove", "--json")
async def test_remove_json_prints_the_removed_subtask(populated_project, invoke) -> None:
    out = await _ran(invoke, ["task", str(TASK), "subtask", "1", "remove", "--yes", "--json"])
    assert (out[0], json.loads(out[1])) == (0, {"removed": "subtask ST1"})


@pytest.mark.covers("<type> <kind> remove", "--as")
async def test_remove_attributes_the_deletion_to_the_named_slug(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "subtask", "1", "remove", "--yes", "--as", "manager"])
    await _ok(invoke, ["task", str(TASK), "subtask", "2", "remove", "--yes"])
    assert (await _actors(invoke, "TASK-3"))[-2:] == [("manager", "remove"), ("system", "remove")]


async def test_remove_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    out = await _ran(
        invoke, ["task", str(TASK), "subtask", "1", "remove", "--yes", "--as", "ghost"]
    )
    assert out == (1, UNKNOWN_SLUG)
