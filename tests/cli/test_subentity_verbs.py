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

from tests._populated import FEATURE, REVIEW, TASK
from tests._profile import selected

P = selected()

pytestmark = pytest.mark.anyio

TASK_FILE = f"{P.ref_prefix}-000003-build-the-query-parser.md"
REVIEW_FILE = f"{P.third_prefix}-000004-{P.third}-the-query-parser.md"
NO_BODY = f"_Describe this {P.kind} here — free-form paragraphs or bullet lists._"
NO_FINDING_BODY = f"_Describe the {P.third_kind}, its impact, and a recommendation — free-form._"
UNKNOWN_STATUS = (
    "error: unknown status 'Nope' (one of: Accepted, Active, Approved, Archived, Blocked, "
    "Cancelled, ChangesRequested, Deferred, Deprecated, Done, Draft, Fixed, InProgress, InReview, "
    "Noted, Open, Proposed, Published, Ready, Rejected, Requested, Superseded, Todo, Verified, "
    "WontFix)\n"
)
UNKNOWN_SLUG = "error: unknown slug 'ghost'; valid slugs: manager\n"
ADDED_HINT = (
    f'  set its body:  sq {P.ref} 3 {P.kind} {P.kind_prefix}{{n}} body -m "…"'
    "  (or --file body.md / --file -)\n"
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
    return json.loads(await _ok(invoke, [P.ref, str(number), P.kind, str(local), "show", "--json"]))


async def _finding(invoke, local: int = 1) -> dict[str, Any]:
    return json.loads(
        await _ok(invoke, [P.third, str(REVIEW), P.third_kind, str(local), "show", "--json"])
    )


async def _create_task(invoke, *extra: str) -> int:
    """Create a task the populated feature does not parent and return its number."""
    output = await _ok(invoke, ["create", P.ref, "Loose end", "--author", "manager", *extra])
    return int(output.split("-")[1].split()[0])


async def _actors(invoke, target: str) -> list[tuple[str, str]]:
    """The (actor, sub-entity operation) pairs the reflog holds for *target*, oldest first."""
    entries = json.loads(
        await _ok(invoke, ["reflog", "--item", target, "--op", "subentity", "--json"])
    )
    return [(e["actor"], e["delta"]["op"]) for e in entries]


# --- the group: LOCAL-ID --------------------------------------------------------------------


@pytest.mark.covers("<type> <kind>", "LOCAL-ID")
@pytest.mark.bundled_only(
    "the case reads a bundled kind's fields, statuses, defaults or rendered text"
)
async def test_the_group_addresses_a_subtask_by_number_or_local_id(
    populated_project, invoke
) -> None:
    by_number = await _subtask(invoke, 1)
    by_local_id = json.loads(
        await _ok(invoke, [P.ref, str(TASK), P.kind, f"{P.kind_prefix}1", "show", "--json"])
    )
    by_lowercase = json.loads(
        await _ok(invoke, [P.ref, str(TASK), P.kind, "st1", "show", "--json"])
    )
    assert by_number == by_local_id == by_lowercase
    assert by_number["local_id"] == f"{P.kind_prefix}1"


@pytest.mark.covers("<type> <kind>", "LOCAL-ID")
async def test_the_group_refuses_a_local_id_the_item_does_not_hold(
    populated_project, invoke
) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), P.kind, "9", "show"]) == (
        1,
        f"error: no {P.kind} {P.kind_prefix}9 in {P.ref_prefix}-3\n",
    )


# --- the plural listing ---------------------------------------------------------------------


@pytest.mark.covers("<type> <kinds>", "--json")
@pytest.mark.bundled_only(
    "the case reads a bundled kind's fields, statuses, defaults or rendered text"
)
async def test_the_plural_listing_prints_every_subtask_as_json(populated_project, invoke) -> None:
    output = await _ok(invoke, [P.ref, str(TASK), P.kind_plural, "--json"])
    rows = [
        {
            "local_id": f"{P.kind_prefix}1",
            "title": "Tokenise the input",
            "status": "Todo",
            "assignee": None,
            "maps_to": f"{P.target_prefix}1",
            "deferred_to": None,
            "badges": {},
            "display": _todo_display(f"{P.target_prefix}1"),
        },
        {
            "local_id": f"{P.kind_prefix}2",
            "title": "Parse the operators",
            "status": "Todo",
            "assignee": None,
            "maps_to": None,
            "deferred_to": None,
            "badges": {},
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
        "maps_to": story,
        "maps_to_kind": {
            "name": "story",
            "label": "Story",
            "plural": "stories",
            "heading": "User Stories",
        },
        "carrier_title": None,
    }


@pytest.mark.covers("<type> <kinds>")
@pytest.mark.bundled_only(
    "the case reads a bundled kind's fields, statuses, defaults or rendered text"
)
async def test_the_plural_listing_prints_a_table_of_subtasks(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), P.kind_plural]) == (
        0,
        "Subtask  Status  Assignee  Title                Story\n"
        f"{P.kind_prefix}1      Todo              Tokenise the input   {P.target_prefix}1  \n"
        f"{P.kind_prefix}2      Todo              Parse the operators       \n",
    )


# --- show -----------------------------------------------------------------------------------


@pytest.mark.covers("<type> <kind> show", "--json")
@pytest.mark.bundled_only(
    "the case reads a bundled kind's fields, statuses, defaults or rendered text"
)
async def test_show_json_prints_the_subtask_as_one_object(populated_project, invoke) -> None:
    output = await _ok(invoke, [P.ref, str(TASK), P.kind, "1", "show", "--json"])
    kind = {"name": P.kind, "label": "Subtask", "plural": P.kind_plural, "heading": "Subtasks"}
    expected = {
        "local_id": f"{P.kind_prefix}1",
        "title": "Tokenise the input",
        "status": "Todo",
        "assignee": None,
        "maps_to": f"{P.target_prefix}1",
        "deferred_to": None,
        "body": NO_BODY,
        "badges": {},
        "discussion": [],
        "display": {
            **_todo_display(f"{P.target_prefix}1"),
            "kind": kind,
            "discussion": None,
        },
    }
    # Compared as text, so the key order is held as well as the content.
    assert output == json.dumps(expected, indent=2) + "\n"


@pytest.mark.covers("<type> <kind> show")
@pytest.mark.bundled_only(
    "the case reads a bundled kind's fields, statuses, defaults or rendered text"
)
async def test_show_prints_the_status_story_body_and_discussion(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), P.kind, "1", "show"]) == (
        0,
        f"{P.kind_prefix}1 — Tokenise the input  ({P.kind})\n"
        f"  status: Todo   {P.target_kind.title()}: {P.target_prefix}1\n\n"
        f"{NO_BODY}\n\n"
        "Discussion\n(none)\n",
    )


# --- add-<kind> -----------------------------------------------------------------------------


@pytest.mark.covers("<type> add-<kind>", "title")
@pytest.mark.bundled_only(
    "the case reads a bundled kind's fields, statuses, defaults or rendered text"
)
async def test_add_scaffolds_a_todo_subtask_with_the_given_title(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), f"add-{P.kind}", "Index the tokens"]) == (
        0,
        f"added {P.kind_prefix}3 to {P.ref_prefix}-3\n" + ADDED_HINT.format(n=3),
    )
    added = await _subtask(invoke, 3)
    assert (added["title"], added["status"], added["maps_to"], added["body"]) == (
        "Index the tokens",
        "Todo",
        None,
        NO_BODY,
    )


@pytest.mark.covers("<type> add-<kind>", "title")
async def test_add_refuses_a_missing_or_blank_title(populated_project, invoke) -> None:
    before = (await _ran(invoke, [P.ref, str(TASK), "show", "--full"]))[1]
    assert await _ran(invoke, [P.ref, str(TASK), f"add-{P.kind}"]) == (
        2,
        f"Usage: sq {P.ref} {{N}} add-{P.kind} [OPTIONS] {{title}}\n"
        f"Try 'sq {P.ref} {{N}} add-{P.kind} --help' for help.\n"
        "╭─ Error ──────────────────────────────────────────────────────────────────────╮\n"
        "│ Missing argument 'title'.                                                    │\n"
        "╰──────────────────────────────────────────────────────────────────────────────╯\n",
    )
    assert await _ran(invoke, [P.ref, str(TASK), f"add-{P.kind}", "  "]) == (
        1,
        "error: title must not be empty\n",
    )
    assert (await _ran(invoke, [P.ref, str(TASK), "show", "--full"]))[1] == before


@pytest.mark.covers("<type> <kind> update", "--title")
async def test_update_refuses_a_blank_title(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), P.kind, "1", "update", "--title", " "]) == (
        1,
        "error: title must not be empty\n",
    )
    assert (await _subtask(invoke, 1))["title"] == "Tokenise the input"


@pytest.mark.covers("<type> add-<kind>", "--message")
async def test_add_message_writes_each_message_as_a_body_paragraph(
    populated_project, invoke
) -> None:
    await _ok(invoke, [P.ref, str(TASK), f"add-{P.kind}", "Index", "-m", "First", "-m", "Second"])
    assert (await _subtask(invoke, 3))["body"] == "First\n\nSecond"


@pytest.mark.covers("<type> add-<kind>", "--file")
async def test_add_file_writes_the_file_as_the_body(populated_project, invoke) -> None:
    _write_file()
    await _ok(invoke, [P.ref, str(TASK), f"add-{P.kind}", "Index", "--file", "text.md"])
    assert (await _subtask(invoke, 3))["body"] == "From a file"


@pytest.mark.covers("<type> add-<kind>", "--file")
async def test_add_file_reads_the_body_from_stdin_for_a_dash(populated_project, invoke) -> None:
    await _ok(
        invoke, [P.ref, str(TASK), f"add-{P.kind}", "Index", "--file", "-"], input="Piped in\n"
    )
    assert (await _subtask(invoke, 3))["body"] == "Piped in"


@pytest.mark.covers("<type> add-<kind>", "--file")
async def test_add_file_refuses_a_file_that_does_not_exist(populated_project, invoke) -> None:
    assert await _ran(
        invoke, [P.ref, str(TASK), f"add-{P.kind}", "Index", "--file", "missing.md"]
    ) == (
        1,
        "error: cannot read file 'missing.md': No such file or directory\n",
    )


@pytest.mark.covers("<type> add-<kind>", "--message", "--file")
async def test_add_refuses_message_with_file(populated_project, invoke) -> None:
    _write_file()
    out = await _ran(
        invoke, [P.ref, str(TASK), f"add-{P.kind}", "Index", "-m", "x", "--file", "text.md"]
    )
    assert out == (1, "error: provide the body via -m or --file, not both\n")


@pytest.mark.covers("<type> add-<kind>", "--status")
async def test_add_status_starts_the_subtask_in_that_status(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), f"add-{P.kind}", "Index", "--status", "InProgress"])
    assert (await _subtask(invoke, 3))["status"] == "InProgress"


@pytest.mark.covers("<type> add-<kind>", "--status")
async def test_add_refuses_a_status_the_spec_does_not_declare(populated_project, invoke) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), f"add-{P.kind}", "Index", "--status", "Nope"])
    assert out == (1, UNKNOWN_STATUS)


@pytest.mark.covers("<type> add-<kind>", "--assignee")
async def test_add_assignee_assigns_the_new_subtask(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), f"add-{P.kind}", "Index", "--assignee", "manager"])
    assert (await _subtask(invoke, 3))["assignee"] == "manager"


@pytest.mark.covers("<type> add-<kind>", "--assignee")
async def test_add_refuses_an_assignee_no_roster_entry_has(populated_project, invoke) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), f"add-{P.kind}", "Index", "--assignee", "ghost"])
    assert out == (1, UNKNOWN_SLUG)


@pytest.mark.covers("<type> add-<kind>", "--<target-kind>")
async def test_add_story_maps_the_subtask_to_a_story_of_the_parent_feature(
    populated_project, invoke
) -> None:
    await _ok(
        invoke,
        [P.ref, str(TASK), f"add-{P.kind}", "Index", f"--{P.target_kind}", f"{P.target_prefix}2"],
    )
    await _ok(invoke, [P.ref, str(TASK), f"add-{P.kind}", "Rank", f"--{P.target_kind}", "1"])
    assert [(await _subtask(invoke, n))["maps_to"] for n in (3, 4)] == [
        f"{P.target_prefix}2",
        f"{P.target_prefix}1",
    ]


@pytest.mark.covers("<type> add-<kind>", "--<target-kind>")
async def test_add_story_refuses_a_story_the_parent_feature_lacks(
    populated_project, invoke
) -> None:
    assert await _ran(
        invoke,
        [P.ref, str(TASK), f"add-{P.kind}", "Index", f"--{P.target_kind}", f"{P.target_prefix}9"],
    ) == (
        1,
        f"error: {P.target_kind} {P.target_prefix}9 not found in {P.host_prefix}-{FEATURE}\n",
    )


@pytest.mark.covers("<type> add-<kind>", "--<target-kind>")
async def test_add_story_is_resolved_against_the_parent_of_the_task_it_is_added_to(
    populated_project, invoke
) -> None:
    output = await _ok(invoke, ["create", P.host, "Indexing", "--author", "manager"])
    other = int(output.split("-")[1].split()[0])
    await _ok(invoke, [P.host, str(other), f"add-{P.target_kind}", f"Only {P.target_kind}"])
    loose = await _create_task(invoke, "--parent", str(other))
    assert await _ran(
        invoke,
        [P.ref, str(loose), f"add-{P.kind}", "Index", f"--{P.target_kind}", f"{P.target_prefix}2"],
    ) == (
        1,
        f"error: {P.target_kind} {P.target_prefix}2 not found in {P.host_prefix}-{other}\n",
    )


@pytest.mark.covers("<type> add-<kind>", "--<target-kind>")
async def test_add_story_refuses_a_task_with_no_feature_parent(populated_project, invoke) -> None:
    loose = await _create_task(invoke)
    assert await _ran(
        invoke,
        [P.ref, str(loose), f"add-{P.kind}", "Index", f"--{P.target_kind}", f"{P.target_prefix}1"],
    ) == (
        1,
        f"error: {P.ref_prefix}-{loose} has no {P.host} parent; set one before mapping {P.kind} "
        f"to {P.target_prefix}1\n",
    )


@pytest.mark.covers("<type> add-<kind>", "--json")
@pytest.mark.bundled_only(
    "the case reads a bundled kind's fields, statuses, defaults or rendered text"
)
async def test_add_json_prints_where_the_body_region_was_written(populated_project, invoke) -> None:
    payload = json.loads(await _ok(invoke, [P.ref, str(TASK), f"add-{P.kind}", "Index", "--json"]))
    assert Path(payload.pop("path")).name == TASK_FILE
    assert payload == {
        "local_id": f"{P.kind_prefix}3",
        "region": f"{P.kind}:{P.kind_prefix}3:body",
        "start_line": 64,
        "end_line": 66,
        "display": {
            "item": f"{P.ref_prefix}-3",
            "body_command": f'sq {P.ref} 3 {P.kind} {P.kind_prefix}3 body -m "…"',
        },
    }


@pytest.mark.covers("<type> add-<kind>", "--as")
async def test_add_attributes_the_new_subtask_to_the_named_slug(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), f"add-{P.kind}", "Index", "--as", "manager"])
    await _ok(invoke, [P.ref, str(TASK), f"add-{P.kind}", "Rank"])
    assert (await _actors(invoke, f"{P.ref_prefix}-3"))[-2:] == [
        ("manager", "add"),
        ("system", "add"),
    ]


@pytest.mark.covers("<type> add-<kind>", "--as")
async def test_add_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), f"add-{P.kind}", "Index", "--as", "ghost"]) == (
        1,
        UNKNOWN_SLUG,
    )


@pytest.mark.covers("<type> add-<kind>", "--<field>")
@pytest.mark.bundled_only(
    "the case reads a bundled kind's fields, statuses, defaults or rendered text"
)
async def test_add_severity_sets_the_severity_of_a_new_finding(populated_project, invoke) -> None:
    out = await _ran(
        invoke, [P.third, str(REVIEW), f"add-{P.third_kind}", "Dead branch", "--severity", "low"]
    )
    assert out == (
        0,
        f"added F3 to {P.third_prefix}-4\n"
        f'  set its body:  sq {P.third} 4 {P.third_kind} F3 body -m "…"'
        "  (or --file body.md / --file -)\n",
    )
    assert (await _finding(invoke, 3))["severity"] == "low"


@pytest.mark.covers("<type> add-<kind>", "title")
@pytest.mark.bundled_only(
    "the case reads a bundled kind's fields, statuses, defaults or rendered text"
)
async def test_add_severity_defaults_to_medium_when_not_given(populated_project, invoke) -> None:
    await _ok(invoke, [P.third, str(REVIEW), f"add-{P.third_kind}", "Dead branch"])
    assert (await _finding(invoke, 3))["severity"] == "medium"


@pytest.mark.covers("<type> add-<kind>", "--<field>")
@pytest.mark.bundled_only(
    "the case reads a bundled kind's fields, statuses, defaults or rendered text"
)
async def test_add_refuses_a_severity_outside_the_declared_ones(populated_project, invoke) -> None:
    out = await _ran(
        invoke, [P.third, str(REVIEW), f"add-{P.third_kind}", "Dead branch", "--severity", "Bad"]
    )
    assert out == (1, "error: unknown severity 'Bad' (one of: critical, high, medium, low, info)\n")


@pytest.mark.covers("<type> add-<kind>", "--deferred-to")
async def test_add_deferred_to_names_the_item_that_carries_a_deferred_finding(
    populated_project, invoke
) -> None:
    await _ok(
        invoke,
        [
            P.third,
            str(REVIEW),
            f"add-{P.third_kind}",
            "Later",
            "--status",
            "Deferred",
            "--deferred-to",
            "3",
        ],
    )
    deferred = await _finding(invoke, 3)
    assert (deferred["status"], deferred["deferred_to"]) == ("Deferred", f"{P.ref_prefix}-3")


@pytest.mark.covers("<type> add-<kind>", "--deferred-to")
@pytest.mark.bundled_only(
    "the case reads a bundled kind's fields, statuses, defaults or rendered text"
)
async def test_add_refuses_deferred_to_on_a_finding_that_is_not_deferred(
    populated_project, invoke
) -> None:
    out = await _ran(
        invoke, [P.third, str(REVIEW), f"add-{P.third_kind}", "Later", "--deferred-to", "3"]
    )
    assert out == (
        1,
        f"error: a carrier (--deferred-to / deferred_to) applies to {P.third_kind} sub-entities "
        f"in a "
        "deferred status (Deferred); F3 is Open\n",
    )


@pytest.mark.covers("<type> add-<kind>", "--deferred-to")
async def test_add_refuses_a_deferred_to_that_is_not_an_item_id(populated_project, invoke) -> None:
    out = await _ran(
        invoke,
        [
            P.third,
            str(REVIEW),
            f"add-{P.third_kind}",
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


@pytest.mark.covers("<type> add-<kind>", "--deferred-to")
async def test_add_refuses_a_deferred_to_no_item_has(populated_project, invoke) -> None:
    out = await _ran(
        invoke,
        [
            P.third,
            str(REVIEW),
            f"add-{P.third_kind}",
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
    assert await _ran(invoke, [P.ref, str(TASK), P.kind, "1", "update", "--title", "Lex"]) == (
        0,
        f"updated {P.ref_prefix}-3 {P.kind_prefix}1\n",
    )
    assert (await _subtask(invoke, 1))["title"] == "Lex"


@pytest.mark.covers("<type> <kind> update", "--status")
async def test_update_moves_to_a_status_the_lifecycle_allows(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), P.kind, "1", "update", "--status", "InProgress"])
    assert (await _subtask(invoke, 1))["status"] == "InProgress"


@pytest.mark.covers("<type> <kind> update", "--status")
async def test_update_refuses_a_status_the_spec_does_not_declare(populated_project, invoke) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), P.kind, "1", "update", "--status", "Nope"])
    assert out == (1, UNKNOWN_STATUS)


@pytest.mark.covers("<type> <kind> update", "--force")
async def test_update_force_makes_a_move_the_lifecycle_refuses(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), P.kind, "1", "update", "--status", "Done"])
    refused = await _ran(
        invoke, [P.ref, str(TASK), P.kind, "1", "update", "--status", P.kind_initial]
    )
    assert refused == (
        1,
        f"error: {P.kind} {P.kind_prefix}1 cannot move Done → {P.kind_initial} (use --force to "
        f"override)\n",
    )
    assert (await _subtask(invoke, 1))["status"] == "Done"
    forced = [P.ref, str(TASK), P.kind, "1", "update", "--status", P.kind_initial, "--force"]
    assert await _ran(invoke, forced) == (0, f"updated {P.ref_prefix}-3 {P.kind_prefix}1\n")
    assert (await _subtask(invoke, 1))["status"] == P.kind_initial


@pytest.mark.covers("<type> <kind> update", "--assignee")
async def test_update_assignee_assigns_the_subtask(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), P.kind, "1", "update", "--assignee", "manager"])
    assert (await _subtask(invoke, 1))["assignee"] == "manager"


@pytest.mark.covers("<type> <kind> update", "--assignee")
async def test_update_refuses_an_assignee_no_roster_entry_has(populated_project, invoke) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), P.kind, "1", "update", "--assignee", "ghost"])
    assert out == (1, UNKNOWN_SLUG)


@pytest.mark.covers("<type> <kind> update", "--clear-assignee")
async def test_update_clear_assignee_unassigns_the_subtask(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), P.kind, "1", "update", "--assignee", "manager"])
    out = await _ran(invoke, [P.ref, str(TASK), P.kind, "1", "update", "--clear-assignee"])
    assert out == (0, f"updated {P.ref_prefix}-3 {P.kind_prefix}1\n")
    assert (await _subtask(invoke, 1))["assignee"] is None


@pytest.mark.covers("<type> <kind> update", "--clear-assignee")
async def test_update_clear_assignee_says_so_when_there_is_none_to_clear(
    populated_project, invoke
) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), P.kind, "1", "update", "--clear-assignee"])
    assert out == (0, f"{P.ref_prefix}-3 {P.kind_prefix}1 has no assignee to clear\n")


@pytest.mark.covers("<type> <kind> update", "--assignee", "--clear-assignee")
async def test_update_refuses_assignee_with_clear_assignee(populated_project, invoke) -> None:
    out = await _ran(
        invoke,
        [P.ref, str(TASK), P.kind, "2", "update", "--assignee", "manager", "--clear-assignee"],
    )
    assert out == (1, "error: use --assignee or --clear-assignee, not both\n")


@pytest.mark.covers("<type> <kind> update", "--<target-kind>")
async def test_update_story_maps_the_subtask_to_a_story_of_the_parent_feature(
    populated_project, invoke
) -> None:
    await _ok(
        invoke,
        [P.ref, str(TASK), P.kind, "1", "update", f"--{P.target_kind}", f"{P.target_prefix}2"],
    )
    await _ok(invoke, [P.ref, str(TASK), P.kind, "2", "update", f"--{P.target_kind}", "1"])
    assert [(await _subtask(invoke, n))["maps_to"] for n in (1, 2)] == [
        f"{P.target_prefix}2",
        f"{P.target_prefix}1",
    ]


@pytest.mark.covers("<type> <kind> update", "--<target-kind>")
async def test_update_story_refuses_a_story_the_parent_feature_lacks(
    populated_project, invoke
) -> None:
    out = await _ran(
        invoke,
        [P.ref, str(TASK), P.kind, "1", "update", f"--{P.target_kind}", f"{P.target_prefix}9"],
    )
    assert out == (
        1,
        f"error: {P.target_kind} {P.target_prefix}9 not found in {P.host_prefix}-{FEATURE}\n",
    )


@pytest.mark.covers("<type> <kind> update", "--<target-kind>")
async def test_update_story_is_resolved_against_the_parent_of_the_task_it_belongs_to(
    populated_project, invoke
) -> None:
    output = await _ok(invoke, ["create", P.host, "Indexing", "--author", "manager"])
    other = int(output.split("-")[1].split()[0])
    await _ok(invoke, [P.host, str(other), f"add-{P.target_kind}", f"Only {P.target_kind}"])
    loose = await _create_task(invoke, "--parent", str(other))
    await _ok(invoke, [P.ref, str(loose), f"add-{P.kind}", "Index"])
    assert await _ran(
        invoke,
        [P.ref, str(loose), P.kind, "1", "update", f"--{P.target_kind}", f"{P.target_prefix}2"],
    ) == (
        1,
        f"error: {P.target_kind} {P.target_prefix}2 not found in {P.host_prefix}-{other}\n",
    )
    await _ok(
        invoke,
        [P.ref, str(loose), P.kind, "1", "update", f"--{P.target_kind}", f"{P.target_prefix}1"],
    )
    assert (await _subtask(invoke, 1, loose))["maps_to"] == f"{P.target_prefix}1"


@pytest.mark.covers("<type> <kind> update", "--<target-kind>")
async def test_update_story_refuses_a_task_with_no_feature_parent(
    populated_project, invoke
) -> None:
    loose = await _create_task(invoke)
    await _ok(invoke, [P.ref, str(loose), f"add-{P.kind}", "Index"])
    assert await _ran(
        invoke,
        [P.ref, str(loose), P.kind, "1", "update", f"--{P.target_kind}", f"{P.target_prefix}1"],
    ) == (
        1,
        f"error: {P.ref_prefix}-{loose} has no {P.host} parent; set one before mapping {P.kind} "
        f"to {P.target_prefix}1\n",
    )


@pytest.mark.covers("<type> <kind> update", "--no-<target-kind>")
async def test_update_no_story_clears_the_story_mapping(populated_project, invoke) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), P.kind, "1", "update", f"--no-{P.target_kind}"])
    assert out == (0, f"updated {P.ref_prefix}-3 {P.kind_prefix}1\n")
    assert (await _subtask(invoke, 1))["maps_to"] is None


@pytest.mark.covers("<type> <kind> update", "--<target-kind>", "--no-<target-kind>")
async def test_update_refuses_story_with_no_story(populated_project, invoke) -> None:
    out = await _ran(
        invoke,
        [
            P.ref,
            str(TASK),
            P.kind,
            "1",
            "update",
            f"--{P.target_kind}",
            f"{P.target_prefix}2",
            f"--no-{P.target_kind}",
        ],
    )
    assert out == (1, f"error: use --{P.target_kind} or --no-{P.target_kind}, not both\n")


@pytest.mark.covers("<type> <kind> update", "--as")
async def test_update_attributes_the_edit_to_the_named_slug(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), P.kind, "1", "update", "--title", "A", "--as", "manager"])
    await _ok(invoke, [P.ref, str(TASK), P.kind, "1", "update", "--title", "B"])
    assert (await _actors(invoke, f"{P.ref_prefix}-3"))[-2:] == [
        ("manager", "update"),
        ("system", "update"),
    ]


@pytest.mark.covers("<type> <kind> update", "--as")
async def test_update_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    out = await _ran(
        invoke, [P.ref, str(TASK), P.kind, "1", "update", "--title", "T", "--as", "ghost"]
    )
    assert out == (1, UNKNOWN_SLUG)


@pytest.mark.covers("<type> <kind> update")
async def test_update_refuses_a_call_that_changes_nothing(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), P.kind, "1", "update"]) == (
        1,
        "error: nothing to update (pass at least one field, e.g. --title/--status)\n",
    )


@pytest.mark.covers("<type> <kind> update", "--<field>")
@pytest.mark.bundled_only(
    "the case reads a bundled kind's fields, statuses, defaults or rendered text"
)
async def test_update_severity_changes_the_severity_of_a_finding(populated_project, invoke) -> None:
    out = await _ran(
        invoke, [P.third, str(REVIEW), P.third_kind, "1", "update", "--severity", "low"]
    )
    assert out == (0, f"updated {P.third_prefix}-4 F1\n")
    assert (await _finding(invoke, 1))["severity"] == "low"


@pytest.mark.covers("<type> <kind> update", "--<field>")
@pytest.mark.bundled_only(
    "the case reads a bundled kind's fields, statuses, defaults or rendered text"
)
async def test_update_severity_accepts_the_label_in_any_case(populated_project, invoke) -> None:
    await _ok(invoke, [P.third, str(REVIEW), P.third_kind, "2", "update", "--severity", "INFO"])
    assert (await _finding(invoke, 2))["severity"] == "info"


@pytest.mark.covers("<type> <kind> update", "--<field>")
@pytest.mark.bundled_only(
    "the case reads a bundled kind's fields, statuses, defaults or rendered text"
)
async def test_update_refuses_a_severity_outside_the_declared_ones(
    populated_project, invoke
) -> None:
    out = await _ran(
        invoke, [P.third, str(REVIEW), P.third_kind, "1", "update", "--severity", "bogus"]
    )
    assert out == (
        1,
        "error: unknown severity 'bogus' (one of: critical, high, medium, low, info)\n",
    )


@pytest.mark.covers("<type> <kind> update", "--deferred-to")
@pytest.mark.bundled_only(
    "the case reads a bundled kind's fields, statuses, defaults or rendered text"
)
async def test_update_deferred_to_points_a_deferred_finding_at_another_item(
    populated_project, invoke
) -> None:
    deferring = [P.third, str(REVIEW), P.third_kind, "1", "update", "--status", "Deferred"]
    await _ok(invoke, [*deferring, "--deferred-to", "3"])
    assert (await _finding(invoke, 1))["deferred_to"] == f"{P.ref_prefix}-3"
    out = await _ran(
        invoke, [P.third, str(REVIEW), P.third_kind, "1", "update", "--deferred-to", "2"]
    )
    assert out == (0, f"updated {P.third_prefix}-4 F1\n")
    assert (await _finding(invoke, 1))["deferred_to"] == f"{P.host_prefix}-2"


@pytest.mark.covers("<type> <kind> update", "--deferred-to")
@pytest.mark.bundled_only(
    "the case reads a bundled kind's fields, statuses, defaults or rendered text"
)
async def test_update_refuses_deferred_to_on_a_finding_that_is_not_deferred(
    populated_project, invoke
) -> None:
    out = await _ran(
        invoke, [P.third, str(REVIEW), P.third_kind, "2", "update", "--deferred-to", "3"]
    )
    assert out == (
        1,
        f"error: a carrier (--deferred-to / deferred_to) applies to {P.third_kind} sub-entities "
        f"in a "
        "deferred status (Deferred); F2 is Open\n",
    )


@pytest.mark.covers("<type> <kind> update", "--deferred-to")
async def test_update_refuses_a_deferred_to_that_is_not_an_item_id(
    populated_project, invoke
) -> None:
    out = await _ran(
        invoke,
        [
            P.third,
            str(REVIEW),
            P.third_kind,
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


@pytest.mark.covers("<type> <kind> update", "--deferred-to")
async def test_update_refuses_a_deferred_to_no_item_has(populated_project, invoke) -> None:
    out = await _ran(
        invoke,
        [
            P.third,
            str(REVIEW),
            P.third_kind,
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
    out = await _ran(invoke, [P.ref, str(TASK), P.kind, "1", "body", "-m", "First", "-m", "Second"])
    assert out == (0, f"{P.ref_prefix}-3 {P.kind_prefix}1: body set\n")
    assert (await _subtask(invoke, 1))["body"] == "First\n\nSecond"


@pytest.mark.covers("<type> <kind> body")
async def test_body_refuses_a_call_with_no_text(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), P.kind, "1", "body"]) == (
        1,
        "error: provide the body via -m (repeatable) or --file PATH ('-' for stdin)\n",
    )


@pytest.mark.covers("<type> <kind> body", "--file")
async def test_body_reads_the_text_from_a_file(populated_project, invoke) -> None:
    _write_file()
    out = await _ran(invoke, [P.ref, str(TASK), P.kind, "1", "body", "--file", "text.md"])
    assert out == (0, f"{P.ref_prefix}-3 {P.kind_prefix}1: body set\n")
    assert (await _subtask(invoke, 1))["body"] == "From a file"


@pytest.mark.covers("<type> <kind> body", "--file")
async def test_body_reads_the_text_from_stdin_for_a_dash(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), P.kind, "1", "body", "--file", "-"], input="Piped in\n")
    assert (await _subtask(invoke, 1))["body"] == "Piped in"


@pytest.mark.covers("<type> <kind> body", "--file")
async def test_body_refuses_a_file_that_does_not_exist(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), P.kind, "1", "body", "--file", "missing.md"]) == (
        1,
        "error: cannot read file 'missing.md': No such file or directory\n",
    )


@pytest.mark.covers("<type> <kind> body", "--message", "--file")
async def test_body_refuses_message_with_file(populated_project, invoke) -> None:
    _write_file()
    out = await _ran(
        invoke, [P.ref, str(TASK), P.kind, "1", "body", "-m", "Text", "--file", "text.md"]
    )
    assert out == (1, "error: provide the body via -m or --file, not both\n")


@pytest.mark.covers("<type> <kind> body", "--append")
async def test_body_append_adds_after_the_existing_body(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), P.kind, "1", "body", "-m", "First"])
    out = await _ran(invoke, [P.ref, str(TASK), P.kind, "1", "body", "-m", "Second", "--append"])
    assert out == (0, f"{P.ref_prefix}-3 {P.kind_prefix}1: body appended\n")
    assert (await _subtask(invoke, 1))["body"] == "First\n\nSecond"


@pytest.mark.covers("<type> <kind> body", "--force")
async def test_body_force_replaces_a_body_already_written(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), P.kind, "1", "body", "-m", "First"])
    refused = await _ran(invoke, [P.ref, str(TASK), P.kind, "1", "body", "-m", "Second"])
    assert refused == (
        1,
        f"error: {P.ref_prefix}-3 {P.kind_prefix}1 already has a body (1 line); setting one would "
        f"discard it:\n\n"
        "    First\n\n"
        "Nothing was written. Add to it with `--append`, or pass `--force` to replace it.\n",
    )
    forced = await _ran(invoke, [P.ref, str(TASK), P.kind, "1", "body", "-m", "Second", "--force"])
    assert forced == (0, f"{P.ref_prefix}-3 {P.kind_prefix}1: body set\n")
    assert (await _subtask(invoke, 1))["body"] == "Second"


@pytest.mark.covers("<type> <kind> body", "--as")
async def test_body_attributes_the_edit_to_the_named_slug(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), P.kind, "1", "body", "-m", "First", "--as", "manager"])
    await _ok(invoke, [P.ref, str(TASK), P.kind, "1", "body", "-m", "Second", "--append"])
    assert (await _actors(invoke, f"{P.ref_prefix}-3"))[-2:] == [
        ("manager", "body"),
        ("system", "body"),
    ]


@pytest.mark.covers("<type> <kind> body", "--as")
async def test_body_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), P.kind, "1", "body", "-m", "x", "--as", "ghost"])
    assert out == (1, UNKNOWN_SLUG)


# --- remove ---------------------------------------------------------------------------------


@pytest.mark.covers("<type> <kind> remove", "--yes")
async def test_remove_yes_deletes_the_subtask_without_asking(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), P.kind, "1", "remove", "--yes"]) == (
        0,
        f"removed {P.kind} {P.kind_prefix}1 from {P.ref_prefix}-3\n",
    )
    assert await _ran(invoke, [P.ref, str(TASK), P.kind, "1", "show"]) == (
        1,
        f"error: no {P.kind} {P.kind_prefix}1 in {P.ref_prefix}-3\n",
    )


@pytest.mark.covers("<type> <kind> remove")
async def test_remove_asks_for_confirmation_and_keeps_the_subtask_when_declined(
    populated_project, invoke
) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), P.kind, "1", "remove"], input="n\n")
    assert out == (
        1,
        f"Remove {P.kind} {P.kind_prefix}1 from {P.ref_prefix}-3? This cannot be undone. [y/N]: "
        f"n\nAborted.\n",
    )
    assert (await _subtask(invoke, 1))["local_id"] == f"{P.kind_prefix}1"


@pytest.mark.covers("<type> <kind> remove")
async def test_remove_deletes_the_subtask_when_confirmed(populated_project, invoke) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), P.kind, "1", "remove"], input="y\n")
    assert out == (
        0,
        f"Remove {P.kind} {P.kind_prefix}1 from {P.ref_prefix}-3? This cannot be undone. [y/N]: y\n"
        f"removed {P.kind} {P.kind_prefix}1 from {P.ref_prefix}-3\n",
    )
    assert [
        row["local_id"]
        for row in json.loads(await _ok(invoke, [P.ref, str(TASK), P.kind_plural, "--json"]))
    ] == [f"{P.kind_prefix}2"]


@pytest.mark.covers("<type> <kind> remove", "--yes")
async def test_remove_refuses_a_subtask_the_item_does_not_hold(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), P.kind, "7", "remove", "--yes"]) == (
        1,
        f"error: no {P.kind} {P.kind_prefix}7 in {P.ref_prefix}-3\n",
    )


@pytest.mark.covers("<type> <kind> remove", "--json")
async def test_remove_json_prints_the_removed_subtask(populated_project, invoke) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), P.kind, "1", "remove", "--yes", "--json"])
    assert (out[0], json.loads(out[1])) == (
        0,
        {"removed": f"{P.kind} {P.kind_prefix}1", "item": f"{P.ref_prefix}-3"},
    )


@pytest.mark.covers("<type> <kind> remove", "--as")
async def test_remove_attributes_the_deletion_to_the_named_slug(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), P.kind, "1", "remove", "--yes", "--as", "manager"])
    await _ok(invoke, [P.ref, str(TASK), P.kind, "2", "remove", "--yes"])
    assert (await _actors(invoke, f"{P.ref_prefix}-3"))[-2:] == [
        ("manager", "remove"),
        ("system", "remove"),
    ]


@pytest.mark.covers("<type> <kind> remove", "--as")
async def test_remove_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), P.kind, "1", "remove", "--yes", "--as", "ghost"])
    assert out == (1, UNKNOWN_SLUG)


# --- the written sub-entity, with --json -----------------------------------------------------


def _written_subtask(title: str, body: str, **outcome: Any) -> str:
    """The populated task's second subtask as the written entry, with the write's *outcome*
    beside it, as `--json` prints it: compared as text, so the key order is held as well as the
    content."""
    subtask = {
        "local_id": f"{P.kind_prefix}2",
        "title": title,
        "status": "Todo",
        "assignee": None,
        "maps_to": None,
        "deferred_to": None,
        "body": body,
        "badges": {},
        "discussion": [],
        "display": {
            "type": "Subtask",
            "status": {"badge": "⚪ Todo", "intent": "neutral"},
            "badges": {},
            "assignee": None,
            "maps_to": None,
            "maps_to_kind": {
                "name": "story",
                "label": "Story",
                "plural": "stories",
                "heading": "User Stories",
            },
            "carrier_title": None,
            "kind": {
                "name": P.kind,
                "label": "Subtask",
                "plural": P.kind_plural,
                "heading": "Subtasks",
            },
            "discussion": None,
        },
    }
    return json.dumps({"entry": subtask, **outcome}, indent=2) + "\n"


@pytest.mark.covers("<type> <kind> update", "--json")
@pytest.mark.bundled_only(
    "the case reads a bundled kind's fields, statuses, defaults or rendered text"
)
async def test_update_json_prints_the_subentity_after_the_update(populated_project, invoke) -> None:
    printed = await _ok(
        invoke, [P.ref, str(TASK), P.kind, "2", "update", "--title", "Parse it", "--json"]
    )
    assert printed == _written_subtask("Parse it", NO_BODY, nothing_to_clear=False)


@pytest.mark.covers("<type> <kind> body", "--json")
@pytest.mark.bundled_only(
    "the case reads a bundled kind's fields, statuses, defaults or rendered text"
)
async def test_body_json_prints_the_subentity_after_the_write(populated_project, invoke) -> None:
    printed = await _ok(invoke, [P.ref, str(TASK), P.kind, "2", "body", "-m", "Text", "--json"])
    assert printed == _written_subtask("Parse the operators", "Text")


@pytest.mark.covers("<type> <kind> remove", "--json")
async def test_remove_json_asks_on_stderr_and_prints_only_the_document_on_stdout(
    populated_project, invoke
) -> None:
    result = await invoke([P.ref, str(TASK), P.kind, "2", "remove", "--json"], input="y\n")
    assert result.exit_code == 0, result.output
    expected = {"removed": f"{P.kind} {P.kind_prefix}2", "item": f"{P.ref_prefix}-3"}
    assert result.stdout == json.dumps(expected, indent=2) + "\n"
    assert (
        result.stderr
        == f"Remove {P.kind} {P.kind_prefix}2 from {P.ref_prefix}-3? This cannot be undone. [y/N]: "
    )


# --- the stored entry -----------------------------------------------------------------------


@pytest.mark.covers("<type> <kind> update", "--title")
@pytest.mark.covers("repair")
async def test_an_unknown_key_on_an_entry_survives_an_update_and_a_repair(
    populated_project, invoke
) -> None:
    path = populated_project.squad_dir / P.ref_folder / TASK_FILE
    text = path.read_text(encoding="utf-8")
    assert text.count(f"- local_id: {P.kind_prefix}2\n") == 1
    path.write_text(
        text.replace(
            f"- local_id: {P.kind_prefix}2\n",
            f"- local_id: {P.kind_prefix}2\n  note: ''\n  kept: yes\n",
        )
    )
    await _ok(invoke, ["repair"])

    await _ok(invoke, [P.ref, str(TASK), P.kind, "2", "update", "--title", "Parse more"])
    await _ok(invoke, ["repair"])

    second = await _subtask(invoke, 2)
    assert (second["title"], second["note"], second["kept"]) == ("Parse more", "", True)


# --- the vocabulary the spec declares: the override squad -----------------------------------


async def _action(invoke, local: int = 1) -> dict[str, Any]:
    return json.loads(await _ok(invoke, ["job", "9", "action", str(local), "show", "--json"]))


@pytest.mark.covers("<type> add-<kind>", "title")
@pytest.mark.covers("<type> <kind>", "LOCAL-ID")
@pytest.mark.bundled_only(
    "the case reads a bundled kind's fields, statuses, defaults or rendered text"
)
async def test_the_mapping_option_is_named_after_the_kind_the_parent_hosts(
    override_project, invoke
) -> None:
    await _ok(invoke, ["job", "9", "add-action", "Publish it", "--outcome", "2"])
    assert (await _action(invoke, 3))["maps_to"] == "OC2"

    await _ok(invoke, ["job", "9", "action", "1", "update", "--outcome", "OC1"])
    assert (await _action(invoke))["maps_to"] == "OC1"

    await _ok(invoke, ["job", "9", "action", "1", "update", "--no-outcome"])
    assert (await _action(invoke))["maps_to"] is None

    assert await _ran(invoke, ["job", "9", "action", "1", "update", f"--{P.target_kind}", "1"]) == (
        2,
        "Usage: sq job {N} action {LOCAL-ID} update [OPTIONS]\n"
        "Try 'sq job {N} action {LOCAL-ID} update --help' for help.\n"
        "╭─ Error ──────────────────────────────────────────────────────────────────────╮\n"
        f"│ No such option: --{P.target_kind} (Possible options: --json)                          "
        f" │\n"
        "╰──────────────────────────────────────────────────────────────────────────────╯\n",
    )


@pytest.mark.covers("<type> <kind>", "LOCAL-ID")
async def test_the_mapping_flags_are_refused_together_under_the_target_kinds_name(
    override_project, invoke
) -> None:
    assert await _ran(
        invoke, ["job", "9", "action", "1", "update", "--outcome", "1", "--no-outcome"]
    ) == (1, "error: use --outcome or --no-outcome, not both\n")


@pytest.mark.covers("<type> add-<kind>", "title")
@pytest.mark.covers("<type> <kind>", "LOCAL-ID")
async def test_a_missing_mapping_target_is_named_by_its_kind_and_local_prefix(
    override_project, invoke
) -> None:
    assert await _ran(invoke, ["job", "9", "add-action", "Publish it", "--outcome", "9"]) == (
        1,
        "error: outcome OC9 not found in INI-8\n",
    )
    assert await _ran(invoke, ["job", "9", "action", "1", "update", "--outcome", "OC9"]) == (
        1,
        "error: outcome OC9 not found in INI-8\n",
    )


@pytest.mark.covers("<type> <kinds>")
@pytest.mark.covers("<type> <kind> show")
async def test_the_help_the_column_and_the_show_line_name_the_target_kind(
    override_project, invoke
) -> None:
    await _ok(invoke, ["job", "9", "action", "1", "update", "--outcome", "1"])
    add_help = (await _ok(invoke, ["job", "9", "add-action", "--help"])).splitlines()
    update_help = (await _ok(invoke, ["job", "9", "action", "1", "update", "--help"])).splitlines()

    assert (
        "│ --impact               <str>  Impact: large|small.                           │"
        in add_help
    )
    assert (
        "│ --outcome              <str>  Desired outcome it maps to, as `OC<n>` or      │"
        in add_help
    )
    assert (
        "│ --outcome               <str>  Desired outcome to map it to, as `OC<n>` or   │"
        in update_help
    )
    assert (
        "│ --no-outcome                   Clear Desired outcome mapping.                │"
        in update_help
    )
    assert await _ok(invoke, ["job", "9", "actions"]) == (
        "Action  Impact    Status    Assignee  Title                   Desired outcome\n"
        "AC1     🔴 large  Todo                Draft the outline       OC1            \n"
        "AC2               Deferred            Record the walkthrough                 \n"
    )
    assert await _ok(invoke, ["job", "9", "action", "1", "show"]) == (
        "AC1 — Draft the outline  (action)\n"
        "  status: Todo   Impact: large   Desired outcome: OC1\n"
        "\n"
        "Outline.\n"
        "\n"
        "Discussion\n"
        "(none)\n"
    )
    update_item_help = (await _ok(invoke, ["job", "9", "update", "--help"])).splitlines()
    create_help = (await _ok(invoke, ["create", "job", "--help"])).splitlines()
    list_help = (await _ok(invoke, ["list", "--help"])).splitlines()
    assert (
        "│ --no-work-size                 Clear Work size.                              │"
        in update_item_help
    )
    assert (
        "│    --owner-team                  <str>  job attribute: owner team.           │"
        in create_help
    )
    assert (
        "│ --min-urgency            <str>  Urgency at least: now|soon|later.            │"
        in list_help
    )


@pytest.mark.covers("<type> <kind>", "LOCAL-ID")
async def test_a_clear_flag_removes_an_optional_field_and_is_refused_beside_its_value(
    override_project, invoke
) -> None:
    assert (await _action(invoke))["impact"] == "large"
    assert await _ran(
        invoke, ["job", "9", "action", "1", "update", "--impact", "small", "--no-impact"]
    ) == (1, "error: use --impact or --no-impact, not both\n")

    await _ok(invoke, ["job", "9", "action", "1", "update", "--no-impact"])

    cleared = await _action(invoke)
    assert "impact" not in cleared
    assert cleared["badges"] == {}


@pytest.mark.covers("<type> <kind>", "LOCAL-ID")
@pytest.mark.bundled_only(
    "the case reads a bundled kind's fields, statuses, defaults or rendered text"
)
async def test_a_required_field_has_no_clear_flag(populated_project, invoke) -> None:
    assert await _ran(
        invoke, [P.third, str(REVIEW), P.third_kind, "1", "update", "--no-severity"]
    ) == (
        2,
        f"Usage: sq {P.third} {{N}} {P.third_kind} {{LOCAL-ID}} update [OPTIONS]\n"
        f"Try 'sq {P.third} {{N}} {P.third_kind} {{LOCAL-ID}} update --help' for help.\n"
        "╭─ Error ──────────────────────────────────────────────────────────────────────╮\n"
        "│ No such option: --no-severity (Possible options: --severity)                 │\n"
        "╰──────────────────────────────────────────────────────────────────────────────╯\n",
    )


@pytest.mark.covers("<type> <kind> update", "--deferred-to")
async def test_a_refusal_names_the_declared_kind_with_no_article_chosen(
    override_project, invoke
) -> None:
    assert await _ran(invoke, ["job", "9", "action", "1", "update", "--deferred-to", "10"]) == (
        1,
        "error: a carrier (--deferred-to / deferred_to) applies to action sub-entities in a "
        "deferred status (Deferred); AC1 is Todo\n",
    )


@pytest.mark.covers("<type> <kind> show", "--json")
@pytest.mark.covers("<type> <kinds>", "--json")
async def test_a_sub_entity_object_is_flat_with_its_mapping_always_present(
    override_project, invoke
) -> None:
    shown = await _ok(invoke, ["job", "9", "action", "1", "show", "--json"])
    kind = {"name": "action", "label": "Action", "plural": "actions", "heading": "Actions"}
    target = {
        "name": "outcome",
        "label": "Desired outcome",
        "plural": "outcomes",
        "heading": "Desired Outcomes",
    }
    large = {"label": "Impact", "badge": "🔴 large", "badge_label": "🔴 Large"}
    expected = {
        "local_id": "AC1",
        "title": "Draft the outline",
        "status": "Todo",
        "assignee": None,
        "maps_to": None,
        "deferred_to": None,
        "impact": "large",
        "body": "Outline.",
        "badges": {"impact": "large"},
        "discussion": [],
        "display": {
            "type": "Action",
            "status": {"badge": "⚪ Todo", "intent": "neutral"},
            "badges": {"impact": large},
            "assignee": None,
            "maps_to": None,
            "maps_to_kind": target,
            "carrier_title": None,
            "kind": kind,
            "discussion": None,
        },
    }
    assert shown == json.dumps(expected, indent=2) + "\n"

    await _ok(invoke, ["job", "9", "action", "1", "update", "--outcome", "2"])
    mapped = await _action(invoke)
    assert (mapped["maps_to"], mapped["display"]["maps_to"]) == ("OC2", "OC2")

    listed = json.loads(await _ok(invoke, ["job", "9", "actions", "--json"]))
    assert list(listed[0]) == [
        "local_id",
        "title",
        "status",
        "assignee",
        "maps_to",
        "deferred_to",
        "impact",
        "badges",
        "display",
    ]
    assert listed[0]["badges"] == {"impact": "large"}
    assert listed[1]["badges"] == {}


@pytest.mark.bundled_only("declares a label on the bundled story kind")
@pytest.mark.covers("<type> <kind>", "LOCAL-ID")
async def test_a_declared_label_on_a_bundled_kind_reaches_the_mapping_option_help(
    populated_project, invoke
) -> None:
    overrides = populated_project.squad_dir / ".overrides"
    overrides.mkdir()
    (overrides / "workflow.toml").write_text(
        '# squads:override-base:0.19.0\n[subentity_kinds.story]\nlabel = "Need"\n',
        encoding="utf-8",
    )
    await _ok(invoke, ["task", str(TASK), "subtask", "1", "show"])
    add_help = (await _ok(invoke, ["task", str(TASK), "add-subtask", "--help"])).splitlines()
    update_help = (
        await _ok(invoke, ["task", str(TASK), "subtask", "1", "update", "--help"])
    ).splitlines()
    assert any("Need it maps to, as `US<n>` or `<n>`." in line for line in add_help)
    assert any("Clear Need mapping." in line for line in update_help)
