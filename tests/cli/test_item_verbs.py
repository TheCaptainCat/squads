"""The work-item verbs, tested on the `task` type: the group's `N` argument, `show`, `update`,
`status`, `body`, `retype`, `remove`, `comments`, `ref add`/`ref rm`, `refs` and `view add`/`view
disable`.

Every other work-item type is held by the verb-set parity guard, so nothing here repeats per type.
"""

import json
import re
from pathlib import Path
from typing import Any

import pytest

from tests.cli._populated import FEATURE, REVIEW, TASK

pytestmark = pytest.mark.anyio

TASK_PATH = "tasks/TASK-000003-build-the-query-parser.md"
FROZEN_STAMP = "2026-06-07T10:00:00Z"


def _write_body_file() -> None:
    Path("body.md").write_text("From a file\n", encoding="utf-8")


async def _ran(invoke, args: list[str], **kw: Any) -> tuple[int, str]:
    result = await invoke(args, **kw)
    return result.exit_code, result.output


async def _ok(invoke, args: list[str], **kw: Any) -> str:
    code, output = await _ran(invoke, args, **kw)
    assert code == 0, output
    return output


async def _show(invoke, number: int = TASK, item_type: str = "task") -> dict[str, Any]:
    return json.loads(await _ok(invoke, [item_type, str(number), "show", "--json"]))


async def _create_task(invoke, *extra: str) -> int:
    """Create a task with no sub-entities and return its number."""
    output = await _ok(invoke, ["create", "task", "Loose end", "--author", "manager", *extra])
    match = re.match(r"created TASK-(\d+)", output)
    assert match, output
    return int(match.group(1))


async def _create_feature(invoke) -> int:
    output = await _ok(invoke, ["create", "feature", "Indexing", "--author", "manager"])
    match = re.match(r"created FEAT-(\d+)", output)
    assert match, output
    return int(match.group(1))


async def _add_operator(invoke) -> str:
    """Register a second slug the task can be authored by or assigned to."""
    await _ok(invoke, ["operator", "add", "Pierre Chat"])
    return "op-pierre"


async def _actors(invoke, target: str, op: str) -> list[str]:
    entries = json.loads(await _ok(invoke, ["reflog", "--item", target, "--op", op, "--json"]))
    return [e["actor"] for e in entries]


# --- the group: N ---------------------------------------------------------------------------


@pytest.mark.covers("<type>", "N")
async def test_the_item_group_addresses_the_item_by_its_number(populated_project, invoke) -> None:
    loose = await _create_task(invoke)
    by_number = await _show(invoke, loose)
    by_full_id = json.loads(await _ok(invoke, ["task", f"TASK-{loose}", "show", "--json"]))
    assert (by_number["id"], by_full_id["id"]) == (f"TASK-{loose}", f"TASK-{loose}")


async def test_the_item_group_refuses_the_number_of_another_type(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(FEATURE), "show"]) == (
        1,
        f"error: {FEATURE} is FEAT-{FEATURE} (feature), not a task\n",
    )


async def test_the_item_group_refuses_a_number_no_item_has(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", "99", "show"]) == (
        1,
        "error: no item with number 99 (use TASK-99 or bare 99)\n",
    )


# --- update ---------------------------------------------------------------------------------


@pytest.mark.covers("<type> update", "--title")
async def test_update_replaces_the_title_and_renames_the_file(populated_project, invoke) -> None:
    out = await _ran(invoke, ["task", str(TASK), "update", "--title", "Parse the query"])
    assert out == (0, "updated TASK-3  tasks/TASK-000003-parse-the-query.md\n")
    item = await _show(invoke)
    assert (item["title"], item["path"]) == (
        "Parse the query",
        "tasks/TASK-000003-parse-the-query.md",
    )


@pytest.mark.covers("<type> update", "--desc")
async def test_update_sets_the_summary_shown_in_listings(populated_project, invoke) -> None:
    out = await _ran(invoke, ["task", str(TASK), "update", "--desc", "Turns text into a tree"])
    assert out == (0, f"updated TASK-3  {TASK_PATH}\n")
    assert (await _show(invoke))["description"] == "Turns text into a tree"


@pytest.mark.covers("<type> update", "--author")
async def test_update_changes_the_author(populated_project, invoke) -> None:
    slug = await _add_operator(invoke)
    out = await _ran(invoke, ["task", str(TASK), "update", "--author", slug])
    assert out == (0, f"updated TASK-3  {TASK_PATH}\n")
    assert (await _show(invoke))["author"] == slug


async def test_update_refuses_an_author_no_roster_entry_has(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "update", "--author", "ghost"]) == (
        1,
        "error: unknown slug 'ghost'; valid slugs: manager\n",
    )


@pytest.mark.covers("<type> update", "--status")
async def test_update_moves_to_a_status_the_lifecycle_allows(populated_project, invoke) -> None:
    out = await _ran(invoke, ["task", str(TASK), "update", "--status", "Ready"])
    assert out == (0, f"updated TASK-3  {TASK_PATH}\n")
    assert (await _show(invoke))["status"] == "Ready"


@pytest.mark.covers("<type> update", "--force")
async def test_update_forces_a_status_the_lifecycle_refuses(populated_project, invoke) -> None:
    refused = await _ran(invoke, ["task", str(TASK), "update", "--status", "Done"])
    assert refused == (1, "error: task cannot move Draft → Done (use --force to override)\n")
    assert (await _show(invoke))["status"] == "Draft"
    forced = await _ran(invoke, ["task", str(TASK), "update", "--status", "Done", "--force"])
    assert forced == (0, f"updated TASK-3  {TASK_PATH}\n")
    assert (await _show(invoke))["status"] == "Done"


@pytest.mark.covers("<type> update", "--parent")
async def test_update_moves_the_task_under_another_parent(populated_project, invoke) -> None:
    loose = await _create_task(invoke, "--parent", str(FEATURE))
    other = await _create_feature(invoke)
    out = await _ran(invoke, ["task", str(loose), "update", "--parent", str(other)])
    assert out == (0, f"updated TASK-{loose}  tasks/TASK-00000{loose}-loose-end.md\n")
    assert (await _show(invoke, loose))["parent"] == f"FEAT-{other}"


async def test_update_refuses_a_parent_that_lacks_the_story_a_subtask_maps_to(
    populated_project, invoke
) -> None:
    other = await _create_feature(invoke)
    assert await _ran(invoke, ["task", str(TASK), "update", "--parent", str(other)]) == (
        1,
        f"error: subtask ST1 → US1 missing from FEAT-{other}\n",
    )


async def test_update_refuses_a_parent_no_item_has(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "update", "--parent", "99"]) == (
        1,
        "error: no item with number 99 (use a full ID like TYPE-99 or bare 99)\n",
    )


@pytest.mark.covers("<type> update", "--no-parent")
async def test_update_clears_the_parent(populated_project, invoke) -> None:
    loose = await _create_task(invoke, "--parent", str(FEATURE))
    out = await _ran(invoke, ["task", str(loose), "update", "--no-parent"])
    assert out == (0, f"updated TASK-{loose}  tasks/TASK-00000{loose}-loose-end.md\n")
    assert (await _show(invoke, loose))["parent"] is None


async def test_update_refuses_to_clear_the_parent_a_mapped_subtask_needs(
    populated_project, invoke
) -> None:
    assert await _ran(invoke, ["task", str(TASK), "update", "--no-parent"]) == (
        1,
        "error: subtask maps to a story but the task has no feature parent\n",
    )


@pytest.mark.covers("<type> update", "--assignee")
async def test_update_assigns_the_item(populated_project, invoke) -> None:
    slug = await _add_operator(invoke)
    out = await _ran(invoke, ["task", str(TASK), "update", "--assignee", slug])
    assert out == (0, f"updated TASK-3  {TASK_PATH}\n")
    assert (await _show(invoke))["assignee"] == slug


async def test_update_refuses_an_assignee_no_roster_entry_has(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "update", "--assignee", "ghost"]) == (
        1,
        "error: unknown slug 'ghost'; valid slugs: manager\n",
    )


@pytest.mark.covers("<type> update", "--clear-assignee")
async def test_update_clears_the_assignee(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "update", "--assignee", "manager"])
    out = await _ran(invoke, ["task", str(TASK), "update", "--clear-assignee"])
    assert out == (0, f"updated TASK-3  {TASK_PATH}\n")
    assert (await _show(invoke))["assignee"] is None


@pytest.mark.covers("<type> update", "--priority")
async def test_update_sets_the_priority(populated_project, invoke) -> None:
    out = await _ran(invoke, ["task", str(TASK), "update", "--priority", "high"])
    assert out == (0, f"updated TASK-3  {TASK_PATH}\n")
    assert (await _show(invoke))["priority"] == "high"


async def test_update_refuses_a_priority_outside_the_declared_ones(
    populated_project, invoke
) -> None:
    assert await _ran(invoke, ["task", str(TASK), "update", "--priority", "soon"]) == (
        1,
        "error: invalid priority 'soon' (one of: urgent, high, medium, low)\n",
    )


@pytest.mark.covers("<type> update", "--no-priority")
async def test_update_clears_the_priority(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "update", "--priority", "high"])
    out = await _ran(invoke, ["task", str(TASK), "update", "--no-priority"])
    assert out == (0, f"updated TASK-3  {TASK_PATH}\n")
    assert (await _show(invoke))["priority"] is None


@pytest.mark.covers("<type> update", "--add-label")
async def test_update_adds_each_repeated_label_once(populated_project, invoke) -> None:
    out = await _ran(
        invoke,
        [
            "task",
            str(TASK),
            "update",
            "--add-label",
            "api",
            "--add-label",
            "ui",
            "--add-label",
            "api",
        ],
    )
    assert out == (0, f"updated TASK-3  {TASK_PATH}\n")
    assert (await _show(invoke))["labels"] == ["api", "ui"]


@pytest.mark.covers("<type> update", "--rm-label")
async def test_update_removes_a_label(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "update", "--add-label", "api", "--add-label", "ui"])
    out = await _ran(invoke, ["task", str(TASK), "update", "--rm-label", "api"])
    assert out == (0, f"updated TASK-3  {TASK_PATH}\n")
    assert (await _show(invoke))["labels"] == ["ui"]


@pytest.mark.covers("<type> update", "--set")
async def test_update_sets_a_declared_attribute(populated_project, invoke) -> None:
    out = await _ran(invoke, ["task", str(TASK), "update", "--set", "priority=low"])
    assert out == (0, f"updated TASK-3  {TASK_PATH}\n")
    assert (await _show(invoke))["priority"] == "low"


async def test_update_refuses_a_set_that_is_not_key_equals_value(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "update", "--set", "priority"]) == (
        1,
        "error: --set expects key=value, got 'priority'\n",
    )


async def test_update_refuses_to_set_an_attribute_the_type_does_not_declare(
    populated_project, invoke
) -> None:
    assert await _ran(invoke, ["task", str(TASK), "update", "--set", "colour=red"]) == (
        1,
        "error: 'colour' is not a settable field on a task; valid: (none)\n",
    )


@pytest.mark.covers("<type> update", "--unset")
async def test_update_unsets_a_declared_attribute(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "update", "--priority", "high"])
    out = await _ran(invoke, ["task", str(TASK), "update", "--unset", "priority"])
    assert out == (0, f"updated TASK-3  {TASK_PATH}\n")
    assert (await _show(invoke))["priority"] is None


async def test_update_refuses_to_unset_an_attribute_the_type_does_not_declare(
    populated_project, invoke
) -> None:
    assert await _ran(invoke, ["task", str(TASK), "update", "--unset", "colour"]) == (
        1,
        "error: 'colour' is not a settable field on a task; valid: (none)\n",
    )


@pytest.mark.covers("<type> update", "--as")
async def test_update_attributes_the_edit_to_the_named_slug(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "update", "--title", "Quiet", "--as", "manager"])
    await _ok(invoke, ["task", str(TASK), "update", "--title", "Anonymous"])
    assert await _actors(invoke, f"TASK-{TASK}", "update") == ["manager", "system"]


async def test_update_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "update", "--title", "T", "--as", "ghost"]) == (
        1,
        "error: unknown slug 'ghost'; valid slugs: manager\n",
    )


async def test_update_refuses_a_call_that_changes_nothing(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "update"]) == (
        1,
        "error: nothing to update (pass at least one field, e.g. --title/--status)\n",
    )


@pytest.mark.covers("<type> update", "--parent", "--no-parent")
async def test_update_refuses_parent_with_no_parent(populated_project, invoke) -> None:
    out = await _ran(invoke, ["task", str(TASK), "update", "--parent", str(FEATURE), "--no-parent"])
    assert out == (1, "error: use either --parent or --no-parent, not both\n")


@pytest.mark.covers("<type> update", "--assignee", "--clear-assignee")
async def test_update_refuses_assignee_with_clear_assignee(populated_project, invoke) -> None:
    out = await _ran(
        invoke, ["task", str(TASK), "update", "--assignee", "manager", "--clear-assignee"]
    )
    assert out == (1, "error: use --assignee or --clear-assignee, not both\n")


@pytest.mark.covers("<type> update", "--priority", "--no-priority")
async def test_update_refuses_priority_with_no_priority(populated_project, invoke) -> None:
    out = await _ran(invoke, ["task", str(TASK), "update", "--priority", "high", "--no-priority"])
    assert out == (1, "error: use either --priority or --no-priority, not both\n")


@pytest.mark.covers("<type> update", "--add-label", "--rm-label")
async def test_update_removes_a_label_that_is_added_and_removed_in_one_call(
    populated_project, invoke
) -> None:
    await _ok(invoke, ["task", str(TASK), "update", "--add-label", "keep"])
    out = await _ran(
        invoke,
        ["task", str(TASK), "update", "--add-label", "tmp", "--rm-label", "tmp", "--rm-label", "x"],
    )
    assert out == (0, f"updated TASK-3  {TASK_PATH}\n")
    assert (await _show(invoke))["labels"] == ["keep"]


@pytest.mark.covers("<type> update", "--set", "--unset")
async def test_update_unsets_an_attribute_that_is_set_and_unset_in_one_call(
    populated_project, invoke
) -> None:
    out = await _ran(
        invoke,
        ["task", str(TASK), "update", "--set", "priority=low", "--unset", "priority"],
    )
    assert out == (0, f"updated TASK-3  {TASK_PATH}\n")
    assert (await _show(invoke))["priority"] is None


# --- show -----------------------------------------------------------------------------------

SHOWN_HEAD = [
    "╭───────────────────────────────────────────────────╮",
    "│ TASK-3  (task)                                    │",
    "│ title: Build the query parser                     │",
    "│ status: Draft                                     │",
    "│ parent: FEAT-2                                    │",
    "│ author: manager                                   │",
    "│ file: tasks/TASK-000003-build-the-query-parser.md │",
    "╰───────────────────────────────────────────────────╯",
    "",
    "## Description",
    "",
    "_TODO: describe this task._",
    "",
    "Subtask  Status  Assignee  Title                Story",
    "ST1      Todo              Tokenise the input   US1  ",
    "ST2      Todo              Parse the operators       ",
]
PLACEHOLDER = "_Describe this subtask here — free-form paragraphs or bullet lists._"


def _subtask_json(local_id: str, title: str, story: str | None) -> dict[str, Any]:
    status = {"badge": "⚪ Todo", "intent": "neutral"}
    return {
        "local_id": local_id,
        "title": title,
        "status": "Todo",
        "assignee": None,
        "severity": None,
        "story": story,
        "deferred_to": None,
        "extra": {},
        "body": PLACEHOLDER,
        "badges": {},
        "discussion": [],
        "display": {
            "type": "Subtask",
            "status": status,
            "badges": {},
            "assignee": None,
            "story": story,
            "carrier_title": None,
        },
    }


@pytest.mark.covers("<type> show", "--json")
async def test_show_json_prints_the_item_as_one_object(populated_project, invoke) -> None:
    body = "## Description\n\n_TODO: describe this task._"
    expected = {
        "sequence_id": 3,
        "type": "task",
        "title": "Build the query parser",
        "slug": "build-the-query-parser",
        "status": "Draft",
        "description": "",
        "parent": "FEAT-2",
        "author": "manager",
        "assignee": None,
        "priority": None,
        "severity": None,
        "labels": [],
        "refs": [],
        "subentities": [
            _subtask_json("ST1", "Tokenise the input", "US1"),
            _subtask_json("ST2", "Parse the operators", None),
        ],
        "path": TASK_PATH,
        "created_at": FROZEN_STAMP,
        "updated_at": FROZEN_STAMP,
        "created_session": None,
        "modified_session": None,
        "id": "TASK-3",
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
            "summary": {
                "kind": "subtask",
                "columns": ["Subtask", "Status", "Assignee", "Title", "Story"],
                "rows": [
                    ["ST1", "Todo", "", "Tokenise the input", "US1"],
                    ["ST2", "Todo", "", "Parse the operators", ""],
                ],
            },
            "attributes": [],
        },
    }
    # Compared as text, so the key order is held as well as the content.
    output = await _ok(invoke, ["task", str(TASK), "show", "--json"])
    assert output == json.dumps(expected, indent=2) + "\n"


async def test_show_prints_a_milestone_with_its_labelled_target_date_in_every_form(
    populated_project, invoke
) -> None:
    out = await _ok(invoke, ["create", "milestone", "Beta", "--author", "manager"])
    number = re.match(r"created MILE-(\d+)", out)
    assert number, out
    await _ok(invoke, ["milestone", number[1], "update", "--set", "target_date=2026-12-01"])
    scope = (
        "## Objective\n\n_TODO: what reaching this milestone means — the outcome it marks, in "
        "one or two sentences._\n\n## Scope boundary\n\n_TODO: what counts toward this milestone "
        "and what doesn't. Membership itself is never listed\nhere — join work to it with `ref "
        "add MILE-… --kind targets` and read `sq milestone <n> show`\nfor the current roll-up, "
        "computed fresh from the corpus every time._\n\n"
    )
    rollup = (
        "## Delivered (0)\n\n_(none yet)_\n\n## Outstanding (0)\n\n_(nothing outstanding)_"
        "\n\n## Settled without delivering (0)\n\n_(none)_"
    )
    expected = {
        "sequence_id": 5,
        "type": "milestone",
        "title": "Beta",
        "slug": "beta",
        "status": "Draft",
        "description": "",
        "parent": None,
        "author": "manager",
        "assignee": None,
        "priority": None,
        "severity": None,
        "labels": [],
        "refs": [],
        "subentities": [],
        "path": "milestones/MILE-000005-beta.md",
        "created_at": FROZEN_STAMP,
        "updated_at": FROZEN_STAMP,
        "created_session": None,
        "modified_session": None,
        "id": "MILE-5",
        "target_date": "2026-12-01",
        "body": scope + "<!-- sq:view:milestone_rollup -->",
        "views": {"milestone_rollup": {"delivered": [], "outstanding": [], "settled": []}},
        "discussion": [],
        "badges": {},
        "display": {
            "type": "Milestone",
            "status": {"badge": "⚪ Draft", "intent": "neutral"},
            "badges": {},
            "assignee": None,
            "body": scope + rollup,
            "summary": None,
            "attributes": [{"key": "target_date", "label": "target date", "value": "2026-12-01"}],
        },
    }
    output = await _ok(invoke, ["milestone", number[1], "show", "--json"])
    assert output == json.dumps(expected, indent=2) + "\n"
    rollup_lines = [
        "## Delivered (0)",
        "",
        "_(none yet)_",
        "",
        "## Outstanding (0)",
        "",
        "_(nothing outstanding)_",
        "",
        "## Settled without delivering (0)",
        "",
        "_(none)_",
    ]
    shown = await _ok(invoke, ["milestone", number[1], "show"])
    assert [line.rstrip() for line in shown.splitlines()] == [
        "╭──────────────────────────────────────╮",
        "│ MILE-5  (milestone)                  │",
        "│ title: Beta                          │",
        "│ status: Draft                        │",
        "│ target date: 2026-12-01              │",
        "│ author: manager                      │",
        "│ file: milestones/MILE-000005-beta.md │",
        "╰──────────────────────────────────────╯",
        "",
        "## Objective",
        "",
        "_TODO: what reaching this milestone means — the outcome it marks, in one or two",
        "sentences._",
        "",
        "## Scope boundary",
        "",
        "_TODO: what counts toward this milestone and what doesn't. Membership itself is",
        "never listed",
        "here — join work to it with `ref add MILE-… --kind targets` and read `sq",
        "milestone <n> show`",
        "for the current roll-up, computed fresh from the corpus every time._",
        "",
        *rollup_lines,
    ]
    raw = await _ok(invoke, ["milestone", number[1], "show", "--raw"])
    assert raw.splitlines() == [
        "# MILE-5 — Beta",
        "",
        "- **status:** Draft",
        "- **target date:** 2026-12-01",
        "- **author:** manager",
        "",
        *(scope + rollup).splitlines(),
    ]


@pytest.mark.covers("<type> show", "--raw")
async def test_show_raw_prints_plain_markdown(populated_project, invoke) -> None:
    out = await _ran(invoke, ["task", str(TASK), "show", "--raw"])
    assert out == (
        0,
        "# TASK-3 — Build the query parser\n\n"
        "- **status:** Draft\n- **parent:** FEAT-2\n- **author:** manager\n\n"
        "## Description\n\n_TODO: describe this task._\n",
    )


@pytest.mark.covers("<type> show", "--full")
async def test_show_full_adds_one_pane_per_subtask(populated_project, invoke) -> None:
    out = await _ran(invoke, ["task", str(TASK), "show", "--full"])
    assert out == (
        0,
        "\n".join(
            [
                *SHOWN_HEAD,
                "=== ST1 — Tokenise the input  ⚪ Todo  US1 ===",
                PLACEHOLDER,
                "",
                "=== ST2 — Parse the operators  ⚪ Todo ===",
                PLACEHOLDER,
                "",
                "",
            ]
        ),
    )


@pytest.mark.covers("<type> show", "--comments")
async def test_show_comments_appends_the_discussion(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "comment", "-m", "Looks good", "--as", "manager"])
    short = json.loads(await _ok(invoke, ["task", str(TASK), "comments", "--json"]))[0][
        "short_hash"
    ]
    out = await _ran(invoke, ["task", str(TASK), "show", "--comments"])
    assert out == (
        0,
        "\n".join(
            [
                *SHOWN_HEAD,
                "",
                f"--- {short} [{FROZEN_STAMP}] Catherine Manager (manager) ---",
                "- Looks good",
                "",
                "",
            ]
        ),
    )


# --- status ---------------------------------------------------------------------------------


@pytest.mark.covers("<type> status", "STATUS")
async def test_status_moves_the_item_along_an_allowed_transition(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "status", "Ready"]) == (0, "TASK-3 → Ready\n")
    assert (await _show(invoke))["status"] == "Ready"


async def test_status_refuses_a_transition_the_lifecycle_does_not_allow(
    populated_project, invoke
) -> None:
    assert await _ran(invoke, ["task", str(TASK), "status", "Done"]) == (
        1,
        "error: task cannot move Draft → Done (use --force to override)\n",
    )
    assert (await _show(invoke))["status"] == "Draft"


async def test_status_refuses_a_status_no_lifecycle_declares(populated_project, invoke) -> None:
    code, output = await _ran(invoke, ["task", str(TASK), "status", "Sleeping"])
    assert (code, output.split(" (one of:")[0]) == (1, "error: unknown status 'Sleeping'")


@pytest.mark.covers("<type> status", "--force")
async def test_status_force_makes_a_transition_the_lifecycle_refuses(
    populated_project, invoke
) -> None:
    assert await _ran(invoke, ["task", str(TASK), "status", "Done", "--force"]) == (
        0,
        "TASK-3 → Done\n",
    )
    assert (await _show(invoke))["status"] == "Done"


@pytest.mark.covers("<type> status", "--as")
async def test_status_attributes_the_move_to_the_named_slug(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "status", "Ready", "--as", "manager"])
    await _ok(invoke, ["task", str(TASK), "status", "InProgress"])
    assert await _actors(invoke, f"TASK-{TASK}", "status") == ["manager", "system"]


@pytest.mark.covers("<type> status", "--json")
async def test_status_json_prints_the_moved_items_row(populated_project, invoke) -> None:
    moved = await _ok(invoke, ["task", str(TASK), "status", "Ready", "--json"])
    # Compared as text, so the key order is held as well as the content.
    assert (
        moved
        == json.dumps(
            {
                "sequence_id": 3,
                "type": "task",
                "title": "Build the query parser",
                "slug": "build-the-query-parser",
                "status": "Ready",
                "description": "",
                "parent": "FEAT-2",
                "author": "manager",
                "assignee": None,
                "priority": None,
                "severity": None,
                "labels": [],
                "refs": [],
                "subentities": [
                    {
                        "local_id": "ST1",
                        "title": "Tokenise the input",
                        "status": "Todo",
                        "assignee": None,
                        "severity": None,
                        "story": "US1",
                        "deferred_to": None,
                        "extra": {},
                    },
                    {
                        "local_id": "ST2",
                        "title": "Parse the operators",
                        "status": "Todo",
                        "assignee": None,
                        "severity": None,
                        "story": None,
                        "deferred_to": None,
                        "extra": {},
                    },
                ],
                "path": TASK_PATH,
                "created_at": FROZEN_STAMP,
                "updated_at": FROZEN_STAMP,
                "created_session": None,
                "modified_session": None,
                "id": "TASK-3",
                "badges": {},
                "display": {
                    "type": "Task",
                    "status": {"badge": "⚪ Ready", "intent": "neutral"},
                    "badges": {},
                    "assignee": None,
                },
            },
            indent=2,
        )
        + "\n"
    )
    assert (await _show(invoke))["status"] == "Ready"


async def test_status_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "status", "Ready", "--as", "ghost"]) == (
        1,
        "error: unknown slug 'ghost'; valid slugs: manager\n",
    )


# --- body -----------------------------------------------------------------------------------


@pytest.mark.covers("<type> body", "--message")
async def test_body_sets_each_message_as_a_paragraph(populated_project, invoke) -> None:
    out = await _ran(invoke, ["task", str(TASK), "body", "-m", "First", "-m", "Second"])
    assert out == (0, "TASK-3: body set\n")
    assert (await _show(invoke))["body"] == "First\n\nSecond"


async def test_body_refuses_a_call_with_no_text(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "body"]) == (
        1,
        "error: provide the body via -m (repeatable) or --file PATH ('-' for stdin)\n",
    )


@pytest.mark.covers("<type> body", "--file")
async def test_body_reads_the_text_from_a_file(populated_project, invoke) -> None:
    _write_body_file()
    assert await _ran(invoke, ["task", str(TASK), "body", "--file", "body.md"]) == (
        0,
        "TASK-3: body set\n",
    )
    assert (await _show(invoke))["body"] == "From a file"


async def test_body_reads_the_text_from_stdin_for_a_dash(populated_project, invoke) -> None:
    out = await _ran(invoke, ["task", str(TASK), "body", "--file", "-"], input="Piped in\n")
    assert out == (0, "TASK-3: body set\n")
    assert (await _show(invoke))["body"] == "Piped in"


def _write_bytes(raw: bytes) -> None:
    Path("body.md").write_bytes(raw)


@pytest.mark.covers("<type> body", "--file")
async def test_body_refuses_a_file_that_is_not_utf8(populated_project, invoke) -> None:
    _write_bytes(b"ok\xff\xfe")
    assert await _ran(invoke, ["task", str(TASK), "body", "--file", "body.md"]) == (
        1,
        "error: cannot read file 'body.md': not valid utf-8 (invalid start byte at byte 2)\n",
    )


async def test_body_refuses_a_file_that_does_not_exist(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "body", "--file", "missing.md"]) == (
        1,
        "error: cannot read file 'missing.md': No such file or directory\n",
    )


@pytest.mark.covers("<type> body", "--message", "--file")
async def test_body_refuses_message_with_file(populated_project, invoke) -> None:
    _write_body_file()
    out = await _ran(invoke, ["task", str(TASK), "body", "-m", "Text", "--file", "body.md"])
    assert out == (1, "error: provide the body via -m or --file, not both\n")


@pytest.mark.covers("<type> body", "--append")
async def test_body_append_adds_after_the_existing_body(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "body", "-m", "First"])
    out = await _ran(invoke, ["task", str(TASK), "body", "-m", "Second", "--append"])
    assert out == (0, "TASK-3: body appended\n")
    assert (await _show(invoke))["body"] == "First\n\nSecond"


@pytest.mark.covers("<type> body", "--force")
async def test_body_force_replaces_a_body_already_written(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "body", "-m", "First"])
    refused = await _ran(invoke, ["task", str(TASK), "body", "-m", "Second"])
    assert refused == (
        1,
        "error: TASK-3 already has a body (1 line); setting one would discard it:\n\n"
        "    First\n\n"
        "Nothing was written. Add to it with `--append`, or pass `--force` to replace it.\n",
    )
    forced = await _ran(invoke, ["task", str(TASK), "body", "-m", "Second", "--force"])
    assert forced == (0, "TASK-3: body set\n")
    assert (await _show(invoke))["body"] == "Second"


@pytest.mark.covers("<type> body", "--as")
async def test_body_attributes_the_edit_to_the_named_slug(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "body", "-m", "First", "--as", "manager"])
    await _ok(invoke, ["task", str(TASK), "body", "-m", "Second", "--append"])
    assert await _actors(invoke, f"TASK-{TASK}", "body") == ["manager", "system"]


async def test_body_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "body", "-m", "x", "--as", "ghost"]) == (
        1,
        "error: unknown slug 'ghost'; valid slugs: manager\n",
    )


# --- retype ---------------------------------------------------------------------------------


@pytest.mark.covers("<type> retype", "NEW-TYPE")
async def test_retype_reclassifies_the_item_and_keeps_its_number(populated_project, invoke) -> None:
    loose = await _create_task(invoke)
    out = await _ran(invoke, ["task", str(loose), "retype", "bug"])
    assert out == (
        0,
        f"retyped TASK-{loose} → BUG-{loose}  bugs/BUG-00000{loose}-loose-end.md\n"
        "  status reset: Draft → Open (workflows differ)\n",
    )
    moved = await _show(invoke, loose, "bug")
    assert (moved["id"], moved["status"]) == (f"BUG-{loose}", "Open")


async def test_retype_refuses_an_item_that_holds_sub_entities(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "retype", "bug"]) == (
        1,
        "error: cannot retype TASK-3: it has sub-entities. "
        "Clear or move all sub-entities first, then retype.\n",
    )


async def test_retype_refuses_the_type_the_item_already_has(populated_project, invoke) -> None:
    loose = await _create_task(invoke)
    assert await _ran(invoke, ["task", str(loose), "retype", "task"]) == (
        1,
        f"error: TASK-{loose} is already of type task\n",
    )


async def test_retype_refuses_a_roster_type(populated_project, invoke) -> None:
    loose = await _create_task(invoke)
    assert await _ran(invoke, ["task", str(loose), "retype", "role"]) == (
        1,
        "error: cannot retype to 'role'; valid targets: "
        "bug, contract, decision, epic, feature, guide, milestone, review, task\n",
    )


async def test_retype_refuses_a_type_the_spec_does_not_declare(populated_project, invoke) -> None:
    loose = await _create_task(invoke)
    assert await _ran(invoke, ["task", str(loose), "retype", "story"]) == (
        1,
        "error: unknown type 'story' (one of: bug, contract, decision, epic, feature, guide, "
        "milestone, operator, review, role, skill, task)\n",
    )


@pytest.mark.covers("<type> retype", "--as")
async def test_retype_attributes_the_edit_to_the_named_slug(populated_project, invoke) -> None:
    loose = await _create_task(invoke)
    await _ok(invoke, ["task", str(loose), "retype", "bug", "--as", "manager"])
    assert await _actors(invoke, f"BUG-{loose}", "retype") == ["manager"]


async def test_retype_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    loose = await _create_task(invoke)
    assert await _ran(invoke, ["task", str(loose), "retype", "bug", "--as", "ghost"]) == (
        1,
        "error: unknown slug 'ghost'; valid slugs: manager\n",
    )


# --- remove ---------------------------------------------------------------------------------


@pytest.mark.covers("<type> remove", "--yes")
async def test_remove_yes_deletes_the_item_without_asking(populated_project, invoke) -> None:
    loose = await _create_task(invoke)
    assert await _ran(invoke, ["task", str(loose), "remove", "--yes"]) == (
        0,
        f"removed TASK-{loose}\n",
    )
    assert (await _ran(invoke, ["task", str(loose), "show"]))[0] == 1


async def test_remove_asks_for_confirmation_and_keeps_the_item_when_declined(
    populated_project, invoke
) -> None:
    loose = await _create_task(invoke)
    out = await _ran(invoke, ["task", str(loose), "remove"], input="n\n")
    assert out == (1, f"Remove TASK-{loose}? This cannot be undone. [y/N]: n\nAborted.\n")
    assert (await _show(invoke, loose))["id"] == f"TASK-{loose}"


async def test_remove_refuses_an_item_other_items_reference(populated_project, invoke) -> None:
    loose = await _create_task(invoke)
    await _ok(invoke, ["task", str(TASK), "ref", "add", str(loose)])
    assert await _ran(invoke, ["task", str(loose), "remove", "--yes"]) == (
        1,
        f"error: cannot remove TASK-{loose}: it is referenced by: TASK-3. "
        "Re-parent/remove those items first, or re-run with --force to sever them.\n",
    )


@pytest.mark.covers("<type> remove", "--force")
async def test_remove_force_cuts_the_refs_other_items_carry(populated_project, invoke) -> None:
    loose = await _create_task(invoke)
    await _ok(invoke, ["task", str(TASK), "ref", "add", str(loose)])
    out = await _ran(invoke, ["task", str(loose), "remove", "--yes", "--force"])
    assert out == (0, f"removed TASK-{loose}\n  severed refs in: TASK-3\n")
    assert (await _show(invoke))["refs"] == []


@pytest.mark.covers("<type> remove", "--json")
async def test_remove_json_prints_the_removed_id_and_the_cut_refs(
    populated_project, invoke
) -> None:
    loose = await _create_task(invoke)
    await _ok(invoke, ["task", str(TASK), "ref", "add", str(loose)])
    out = await _ran(invoke, ["task", str(loose), "remove", "--yes", "--force", "--json"])
    assert (out[0], json.loads(out[1])) == (
        0,
        {"removed_id": f"TASK-{loose}", "severed_refs": ["TASK-3"]},
    )


@pytest.mark.covers("<type> remove", "--as")
async def test_remove_attributes_the_deletion_to_the_named_slug(populated_project, invoke) -> None:
    loose = await _create_task(invoke)
    await _ok(invoke, ["task", str(loose), "remove", "--yes", "--as", "manager"])
    assert await _actors(invoke, f"TASK-{loose}", "remove") == ["manager"]


async def test_remove_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    loose = await _create_task(invoke)
    assert await _ran(invoke, ["task", str(loose), "remove", "--yes", "--as", "ghost"]) == (
        1,
        "error: unknown slug 'ghost'; valid slugs: manager\n",
    )


# --- ref add / ref rm -----------------------------------------------------------------------


@pytest.mark.covers("<type> ref add", "TARGET")
async def test_ref_add_links_the_item_to_the_target_as_related(populated_project, invoke) -> None:
    out = await _ran(invoke, ["task", str(TASK), "ref", "add", f"REV-{REVIEW}"])
    assert out == (0, f"TASK-3 → REV-{REVIEW} (related)\n")
    assert (await _show(invoke))["refs"] == [f"REV-{REVIEW}"]


async def test_ref_add_refuses_a_target_that_is_not_an_item_id(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "ref", "add", "elsewhere"]) == (
        1,
        "error: invalid item id 'elsewhere' (use a bare number or a full ID like TYPE-NNNNNN)\n",
    )


@pytest.mark.covers("<type> ref add", "--kind")
async def test_ref_add_kind_names_the_relation(populated_project, invoke) -> None:
    out = await _ran(invoke, ["task", str(TASK), "ref", "add", str(REVIEW), "--kind", "fixes"])
    assert out == (0, f"TASK-3 → REV-{REVIEW} (fixes)\n")
    assert (await _show(invoke))["refs"] == [f"REV-{REVIEW}:fixes"]


async def test_ref_add_refuses_a_kind_the_spec_does_not_declare(populated_project, invoke) -> None:
    assert await _ran(
        invoke, ["task", str(TASK), "ref", "add", str(REVIEW), "--kind", "likes"]
    ) == (
        1,
        "error: unknown ref kind 'likes'. Valid kinds: addresses, blocks, depends-on, "
        "duplicates, fixes, implements, related, scopes, supersedes, targets\n",
    )


@pytest.mark.covers("<type> ref add", "--as")
async def test_ref_add_attributes_the_edit_to_the_named_slug(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "ref", "add", str(REVIEW), "--as", "manager"])
    await _ok(invoke, ["task", str(TASK), "ref", "add", str(FEATURE)])
    assert await _actors(invoke, f"TASK-{TASK}", "ref") == ["manager", "system"]


async def test_ref_add_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    out = await _ran(invoke, ["task", str(TASK), "ref", "add", str(REVIEW), "--as", "ghost"])
    assert out == (1, "error: unknown slug 'ghost'; valid slugs: manager\n")


@pytest.mark.covers("<type> ref rm", "TARGET")
async def test_ref_rm_drops_every_ref_to_the_target(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "ref", "add", str(REVIEW), "--kind", "fixes"])
    await _ok(invoke, ["task", str(TASK), "ref", "add", str(REVIEW), "--kind", "related"])
    await _ok(invoke, ["task", str(TASK), "ref", "add", str(FEATURE)])
    out = await _ran(invoke, ["task", str(TASK), "ref", "rm", f"REV-{REVIEW}"])
    assert out == (0, f"removed TASK-3 → REV-{REVIEW}\n")
    assert (await _show(invoke))["refs"] == [f"FEAT-{FEATURE}"]


async def test_ref_rm_refuses_a_target_that_is_not_an_item_id(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "ref", "rm", "elsewhere"]) == (
        1,
        "error: invalid item id 'elsewhere' (use a bare number or a full ID like TYPE-NNNNNN)\n",
    )


@pytest.mark.covers("<type> ref rm", "--as")
async def test_ref_rm_attributes_the_edit_to_the_named_slug(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "ref", "add", str(REVIEW)])
    await _ok(invoke, ["task", str(TASK), "ref", "rm", str(REVIEW), "--as", "manager"])
    assert (await _actors(invoke, f"TASK-{TASK}", "ref"))[-1] == "manager"


async def test_ref_rm_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    out = await _ran(invoke, ["task", str(TASK), "ref", "rm", str(REVIEW), "--as", "ghost"])
    assert out == (1, "error: unknown slug 'ghost'; valid slugs: manager\n")


# --- refs -----------------------------------------------------------------------------------


@pytest.mark.covers("<type> refs", "--out")
async def test_refs_out_lists_the_refs_the_item_carries(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "ref", "add", str(REVIEW), "--kind", "fixes"])
    await _ok(invoke, ["review", str(REVIEW), "ref", "add", str(FEATURE)])
    out = await _ran(invoke, ["task", str(TASK), "refs", "--out"])
    assert out == (0, f"→ refs      \nID     Kind \nREV-{REVIEW}  fixes\n")


@pytest.mark.covers("<type> refs", "--out", "--in")
async def test_refs_out_with_in_lists_both_directions(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "ref", "add", str(REVIEW), "--kind", "fixes"])
    await _ok(invoke, ["review", str(REVIEW), "ref", "add", str(TASK), "--kind", "addresses"])
    out = await _ran(invoke, ["task", str(TASK), "refs", "--out", "--in"])
    assert out == (
        0,
        f"→ refs      \nID     Kind \nREV-{REVIEW}  fixes\n"
        f"← backrefs      \nID     Kind     \nREV-{REVIEW}  addresses\n",
    )


@pytest.mark.covers("<type> refs", "--in")
async def test_refs_in_lists_the_refs_other_items_carry_to_it(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "ref", "add", str(REVIEW)])
    await _ok(invoke, ["review", str(REVIEW), "ref", "add", str(TASK), "--kind", "addresses"])
    out = await _ran(invoke, ["task", str(TASK), "refs", "--in"])
    assert out == (0, f"← backrefs      \nID     Kind     \nREV-{REVIEW}  addresses\n")


@pytest.mark.covers("<type> refs", "--all")
async def test_refs_all_lists_both_directions(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "ref", "add", str(REVIEW), "--kind", "fixes"])
    out = await _ran(invoke, ["task", str(TASK), "refs", "--all"])
    assert out == (
        0,
        f"→ refs      \nID     Kind \nREV-{REVIEW}  fixes\n← backrefs: none\n",
    )


@pytest.mark.covers("<type> refs", "--json")
async def test_refs_json_prints_an_array_per_direction_shown(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "ref", "add", str(REVIEW), "--kind", "fixes"])
    await _ok(invoke, ["review", str(REVIEW), "ref", "add", str(TASK), "--kind", "addresses"])
    default = json.loads(await _ok(invoke, ["task", str(TASK), "refs", "--json"]))
    both = json.loads(await _ok(invoke, ["task", str(TASK), "refs", "--all", "--json"]))
    assert (default, both) == (
        {"out": [{"id": f"REV-{REVIEW}", "kind": "fixes"}]},
        {
            "out": [{"id": f"REV-{REVIEW}", "kind": "fixes"}],
            "in": [{"id": f"REV-{REVIEW}", "kind": "addresses"}],
        },
    )


# --- comments -------------------------------------------------------------------------------


@pytest.mark.covers("<host> comments", "--json")
async def test_comments_json_prints_one_object_per_comment(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "comments", "--json"]) == (0, "[]\n")
    await _ok(invoke, ["task", str(TASK), "comment", "-m", "Looks good", "--as", "manager"])
    comments = json.loads(await _ok(invoke, ["task", str(TASK), "comments", "--json"]))
    assert [
        {k: c[k] for k in ("author", "author_slug", "ts", "edited_ts", "body")} for c in comments
    ] == [
        {
            "author": "Catherine Manager",
            "author_slug": "manager",
            "ts": FROZEN_STAMP,
            "edited_ts": None,
            "body": "- Looks good",
        }
    ]


# --- view add / view disable ----------------------------------------------------------------


@pytest.mark.covers("<type> view add", "NAME")
async def test_view_add_places_the_declared_view_in_the_body(populated_project, invoke) -> None:
    out = await _ran(invoke, ["task", str(TASK), "view", "add", "milestone_rollup"])
    assert out == (0, "TASK-3: view milestone_rollup placed in sq:body\n")
    assert (await _show(invoke))["views"] == {
        "milestone_rollup": {"delivered": [], "outstanding": [], "settled": []}
    }


async def test_view_add_refuses_a_name_no_view_declares(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "view", "add", "gantt"]) == (
        1,
        "error: no declared view 'gantt' with a resolvable presentation template; "
        "see `sq workflow views` for the declared set\n",
    )


@pytest.mark.covers("<type> view disable", "NAME")
async def test_view_disable_stops_showing_the_view(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "view", "add", "milestone_rollup"])
    out = await _ran(invoke, ["task", str(TASK), "view", "disable", "milestone_rollup"])
    assert out == (0, "TASK-3: view milestone_rollup disabled in sq:body\n")
    assert (await _show(invoke))["views"] == {}


@pytest.mark.covers("<type> view add", "--as")
async def test_view_add_attributes_the_edit_to_the_named_slug(populated_project, invoke) -> None:
    await _ok(invoke, ["task", str(TASK), "view", "add", "milestone_rollup", "--as", "manager"])
    assert await _actors(invoke, f"TASK-{TASK}", "view") == ["manager"]


async def test_view_add_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    out = await _ran(
        invoke, ["task", str(TASK), "view", "add", "milestone_rollup", "--as", "ghost"]
    )
    assert out == (1, "error: unknown slug 'ghost'; valid slugs: manager\n")


@pytest.mark.covers("<type> view disable", "--as")
async def test_view_disable_attributes_the_edit_to_the_named_slug(
    populated_project, invoke
) -> None:
    await _ok(invoke, ["task", str(TASK), "view", "add", "milestone_rollup"])
    await _ok(invoke, ["task", str(TASK), "view", "disable", "milestone_rollup", "--as", "manager"])
    assert await _actors(invoke, f"TASK-{TASK}", "view") == ["system", "manager"]


async def test_view_disable_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    out = await _ran(
        invoke, ["task", str(TASK), "view", "disable", "milestone_rollup", "--as", "ghost"]
    )
    assert out == (1, "error: unknown slug 'ghost'; valid slugs: manager\n")
