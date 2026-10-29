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

from tests._populated import FEATURE, REVIEW, TASK
from tests._profile import selected
from tests.cli._output import unknown_option

P = selected()

pytestmark = pytest.mark.anyio

TASK_PATH = f"{P.ref_folder}/{P.ref_prefix}-000003-build-the-query-parser.md"
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


async def _show(invoke, number: int = TASK, item_type: str = P.ref) -> dict[str, Any]:
    return json.loads(await _ok(invoke, [item_type, str(number), "show", "--json"]))


async def _create_task(invoke, *extra: str) -> int:
    """Create a task with no sub-entities and return its number."""
    output = await _ok(invoke, ["create", P.ref, "Loose end", "--author", "manager", *extra])
    match = re.match(rf"created {P.ref_prefix}-(\d+)", output)
    assert match, output
    return int(match.group(1))


async def _create_feature(invoke) -> int:
    output = await _ok(invoke, ["create", P.host, "Indexing", "--author", "manager"])
    match = re.match(rf"created {P.host_prefix}-(\d+)", output)
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
    by_full_id = json.loads(await _ok(invoke, [P.ref, f"{P.ref_prefix}-{loose}", "show", "--json"]))
    assert (by_number["id"], by_full_id["id"]) == (
        f"{P.ref_prefix}-{loose}",
        f"{P.ref_prefix}-{loose}",
    )


@pytest.mark.covers("<type>", "N")
async def test_the_item_group_refuses_the_number_of_another_type(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(FEATURE), "show"]) == (
        1,
        f"error: {FEATURE} is {P.host_prefix}-{FEATURE} ({P.host}), not of type {P.ref}\n",
    )


@pytest.mark.covers("<type>", "N")
async def test_the_item_group_refuses_a_number_no_item_has(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, "99", "show"]) == (
        1,
        f"error: no item with number 99 (use {P.ref_prefix}-99 or bare 99)\n",
    )


# --- update ---------------------------------------------------------------------------------


@pytest.mark.covers("<type> update", "--title")
async def test_update_replaces_the_title_and_renames_the_file(populated_project, invoke) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), "update", "--title", "Parse the query"])
    assert out == (
        0,
        f"updated {P.ref_prefix}-3  {P.ref_folder}/{P.ref_prefix}-000003-parse-the-query.md\n",
    )
    item = await _show(invoke)
    assert (item["title"], item["path"]) == (
        "Parse the query",
        f"{P.ref_folder}/{P.ref_prefix}-000003-parse-the-query.md",
    )


@pytest.mark.covers("<type> update", "--desc")
async def test_update_sets_the_summary_shown_in_listings(populated_project, invoke) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), "update", "--desc", "Turns text into a tree"])
    assert out == (0, f"updated {P.ref_prefix}-3  {TASK_PATH}\n")
    assert (await _show(invoke))["description"] == "Turns text into a tree"


@pytest.mark.covers("<type> update", "--author")
async def test_update_changes_the_author(populated_project, invoke) -> None:
    slug = await _add_operator(invoke)
    out = await _ran(invoke, [P.ref, str(TASK), "update", "--author", slug])
    assert out == (0, f"updated {P.ref_prefix}-3  {TASK_PATH}\n")
    assert (await _show(invoke))["author"] == slug


@pytest.mark.covers("<type> update", "--author")
async def test_update_refuses_an_author_no_roster_entry_has(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), "update", "--author", "ghost"]) == (
        1,
        "error: unknown slug 'ghost'; valid slugs: manager\n",
    )


@pytest.mark.covers("<type> update", "--status")
async def test_update_moves_to_a_status_the_lifecycle_allows(populated_project, invoke) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), "update", "--status", "Ready"])
    assert out == (0, f"updated {P.ref_prefix}-3  {TASK_PATH}\n")
    assert (await _show(invoke))["status"] == "Ready"


@pytest.mark.covers("<type> update", "--force")
async def test_update_forces_a_status_the_lifecycle_refuses(populated_project, invoke) -> None:
    refused = await _ran(invoke, [P.ref, str(TASK), "update", "--status", "Done"])
    assert refused == (1, f"error: {P.ref} cannot move Draft → Done (use --force to override)\n")
    assert (await _show(invoke))["status"] == "Draft"
    forced = await _ran(invoke, [P.ref, str(TASK), "update", "--status", "Done", "--force"])
    assert forced == (0, f"updated {P.ref_prefix}-3  {TASK_PATH}\n")
    assert (await _show(invoke))["status"] == "Done"


@pytest.mark.covers("<type> update", "--parent")
async def test_update_moves_the_task_under_another_parent(populated_project, invoke) -> None:
    loose = await _create_task(invoke, "--parent", str(FEATURE))
    other = await _create_feature(invoke)
    out = await _ran(invoke, [P.ref, str(loose), "update", "--parent", str(other)])
    assert out == (
        0,
        f"updated {P.ref_prefix}-{loose}  {P.ref_folder}/{P.ref_prefix}-00000{loose}-loose-end.md\n",
    )
    assert (await _show(invoke, loose))["parent"] == f"{P.host_prefix}-{other}"


@pytest.mark.covers("<type> update", "--parent")
async def test_update_refuses_a_parent_that_lacks_the_story_a_subtask_maps_to(
    populated_project, invoke
) -> None:
    other = await _create_feature(invoke)
    assert await _ran(invoke, [P.ref, str(TASK), "update", "--parent", str(other)]) == (
        1,
        f"error: {P.kind} {P.kind_prefix}1 maps to {P.target_kind} {P.target_prefix}1, missing from {P.host_prefix}-{other}\n",
    )


@pytest.mark.covers("<type> update", "--parent")
async def test_update_refuses_a_parent_no_item_has(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), "update", "--parent", "99"]) == (
        1,
        "error: no item with number 99 (use a full ID like TYPE-99 or bare 99)\n",
    )


@pytest.mark.covers("<type> update", "--no-parent")
async def test_update_clears_the_parent(populated_project, invoke) -> None:
    loose = await _create_task(invoke, "--parent", str(FEATURE))
    out = await _ran(invoke, [P.ref, str(loose), "update", "--no-parent"])
    assert out == (
        0,
        f"updated {P.ref_prefix}-{loose}  {P.ref_folder}/{P.ref_prefix}-00000{loose}-loose-end.md\n",
    )
    assert (await _show(invoke, loose))["parent"] is None


@pytest.mark.covers("<type> update", "--no-parent")
async def test_update_refuses_to_clear_the_parent_a_mapped_subtask_needs(
    populated_project, invoke
) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), "update", "--no-parent"]) == (
        1,
        f"error: {P.kind} maps to {P.target_kind} sub-entities but {P.ref_prefix}-3 has no {P.host} parent\n",
    )


@pytest.mark.covers("<type> update", "--assignee")
async def test_update_assigns_the_item(populated_project, invoke) -> None:
    slug = await _add_operator(invoke)
    out = await _ran(invoke, [P.ref, str(TASK), "update", "--assignee", slug])
    assert out == (0, f"updated {P.ref_prefix}-3  {TASK_PATH}\n")
    assert (await _show(invoke))["assignee"] == slug


@pytest.mark.covers("<type> update", "--assignee")
async def test_update_refuses_an_assignee_no_roster_entry_has(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), "update", "--assignee", "ghost"]) == (
        1,
        "error: unknown slug 'ghost'; valid slugs: manager\n",
    )


@pytest.mark.covers("<type> update", "--clear-assignee")
async def test_update_clears_the_assignee(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), "update", "--assignee", "manager"])
    out = await _ran(invoke, [P.ref, str(TASK), "update", "--clear-assignee"])
    assert out == (0, f"updated {P.ref_prefix}-3  {TASK_PATH}\n")
    assert (await _show(invoke))["assignee"] is None


@pytest.mark.covers("<type> update", "--<field>")
async def test_update_sets_the_priority(populated_project, invoke) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), "update", "--priority", "high"])
    assert out == (0, f"updated {P.ref_prefix}-3  {TASK_PATH}\n")
    assert (await _show(invoke))["priority"] == "high"


@pytest.mark.covers("<type> update", "--<field>")
async def test_update_refuses_a_priority_outside_the_declared_ones(
    populated_project, invoke
) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), "update", "--priority", "soon"]) == (
        1,
        "error: invalid priority 'soon' (one of: urgent, high, medium, low)\n",
    )


@pytest.mark.covers("<type> update", "--no-<field>")
async def test_update_clears_the_priority(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), "update", "--priority", "high"])
    out = await _ran(invoke, [P.ref, str(TASK), "update", "--no-priority"])
    assert out == (0, f"updated {P.ref_prefix}-3  {TASK_PATH}\n")
    assert "priority" not in await _show(invoke)


@pytest.mark.covers("<type> update", "--<field>")
@pytest.mark.covers("<type> update", "--no-<field>")
async def test_update_sets_and_clears_a_field_only_some_types_declare(
    populated_project, invoke
) -> None:
    await _ok(invoke, ["create", "bug", "Crash", "--author", "manager"])
    await _ok(invoke, ["bug", "5", "update", "--severity", "high"])
    assert (await _show(invoke, 5, "bug"))["severity"] == "high"
    await _ok(invoke, ["bug", "5", "update", "--no-severity"])
    assert "severity" not in (await _show(invoke, 5, "bug"))["badges"]
    refused = await _ran(invoke, [P.ref, str(TASK), "update", "--severity", "high"])
    assert refused == (
        2,
        unknown_option(
            f"{P.ref} N update [OPTIONS]",
            f"{P.ref} N update",
            "--severity",
            " ('(Possible options: --priority, --set)',)",
        ),
    )


@pytest.mark.covers("<type> update", "--json")
async def test_update_takes_a_flag_per_declared_field_and_a_negation_per_optional_one(
    override_project, invoke
) -> None:
    initiative = await _ok(invoke, ["initiative", "8", "update", "--urgency", "later", "--json"])
    assert json.loads(initiative)["entry"]["badges"] == {"urgency": "later"}
    job = await _ok(invoke, ["job", "9", "update", "--work-size", "l", "--json"])
    assert json.loads(job)["entry"]["badges"] == {"work_size": "l"}
    cleared = await _ok(invoke, ["job", "9", "update", "--no-work-size", "--json"])
    assert json.loads(cleared)["entry"]["badges"] == {}
    both = await _ran(invoke, ["job", "9", "update", "--work-size", "s", "--no-work-size"])
    assert both == (1, "error: use either --work-size or --no-work-size, not both\n")
    for flag, hint in (
        ("--priority", ""),
        ("--no-priority", " ('(Possible options: --no-parent)',)"),
    ):
        refused = await _ran(invoke, ["initiative", "8", "update", flag])
        assert refused == (
            2,
            unknown_option("initiative N update [OPTIONS]", "initiative N update", flag, hint),
        )


@pytest.mark.covers("<type> update", "--<field>")
async def test_update_refuses_an_empty_priority_even_beside_another_change(
    populated_project, invoke
) -> None:
    assert await _ran(
        invoke, [P.ref, str(TASK), "update", "--priority", "", "--title", "Renamed"]
    ) == (1, "error: invalid priority '' (one of: urgent, high, medium, low)\n")


@pytest.mark.covers("<type> update", "--<field>", "--no-<field>")
@pytest.mark.covers("<type> update", "--set")
async def test_update_logs_each_badge_change_in_the_reflog_delta(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), "update", "--priority", "high"])
    await _ok(invoke, [P.ref, str(TASK), "update", "--set", "priority=low"])
    await _ok(invoke, [P.ref, str(TASK), "update", "--no-priority"])
    entries = json.loads(
        await _ok(
            invoke, ["reflog", "--item", f"{P.ref_prefix}-{TASK}", "--op", "update", "--json"]
        )
    )
    assert [e["delta"] for e in entries] == [
        {"priority": "high"},
        {"priority": "low"},
        {"priority": None},
    ]


@pytest.mark.covers("<type> update", "--<field>", "--no-<field>")
async def test_update_refuses_a_flag_and_its_negation_together(populated_project, invoke) -> None:
    assert await _ran(
        invoke, [P.ref, str(TASK), "update", "--priority", "high", "--no-priority"]
    ) == (1, "error: use either --priority or --no-priority, not both\n")


@pytest.mark.covers("<type> update", "--add-label")
async def test_update_adds_each_repeated_label_once(populated_project, invoke) -> None:
    out = await _ran(
        invoke,
        [
            P.ref,
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
    assert out == (0, f"updated {P.ref_prefix}-3  {TASK_PATH}\n")
    assert (await _show(invoke))["labels"] == ["api", "ui"]


@pytest.mark.covers("<type> update", "--rm-label")
async def test_update_removes_a_label(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), "update", "--add-label", "api", "--add-label", "ui"])
    out = await _ran(invoke, [P.ref, str(TASK), "update", "--rm-label", "api"])
    assert out == (0, f"updated {P.ref_prefix}-3  {TASK_PATH}\n")
    assert (await _show(invoke))["labels"] == ["ui"]


@pytest.mark.covers("<type> update", "--set")
async def test_update_sets_a_declared_attribute(populated_project, invoke) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), "update", "--set", "priority=low"])
    assert out == (0, f"updated {P.ref_prefix}-3  {TASK_PATH}\n")
    assert (await _show(invoke))["priority"] == "low"


@pytest.mark.covers("<type> update", "--set")
async def test_update_stores_a_field_an_override_declares_under_its_code(
    populated_project, invoke
) -> None:
    overrides = populated_project.squad_dir / ".overrides"
    overrides.mkdir()
    (overrides / "workflow.toml").write_text(
        f"# squads:override-base:0.19.0\n[items.{P.ref}]\nfields = [\n"
        '  { code = "urgency", label = "Urgency", collection = "priority" },\n]\n',
        encoding="utf-8",
    )
    await _ok(invoke, [P.ref, str(TASK), "update", "--set", "urgency=high"])

    shown = await _show(invoke)
    assert shown["urgency"] == "high"
    assert shown["badges"] == {"urgency": "high"}
    assert shown["display"]["badges"]["urgency"]["label"] == "Urgency"


@pytest.mark.covers("<type> update", "--set")
async def test_update_refuses_a_set_that_is_not_key_equals_value(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), "update", "--set", "priority"]) == (
        1,
        "error: --set expects key=value, got 'priority'\n",
    )


@pytest.mark.covers("<type> update", "--set")
async def test_update_refuses_to_set_an_attribute_the_type_does_not_declare(
    populated_project, invoke
) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), "update", "--set", "colour=red"]) == (
        1,
        f"error: 'colour' is not a settable field of {P.ref} items; valid: priority\n",
    )


@pytest.mark.covers("<type> update", "--unset")
async def test_update_unsets_a_declared_attribute(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), "update", "--priority", "high"])
    out = await _ran(invoke, [P.ref, str(TASK), "update", "--unset", "priority"])
    assert out == (0, f"updated {P.ref_prefix}-3  {TASK_PATH}\n")
    assert "priority" not in await _show(invoke)


@pytest.mark.covers("<type> update", "--unset")
async def test_update_refuses_to_unset_an_attribute_the_type_does_not_declare(
    populated_project, invoke
) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), "update", "--unset", "colour"]) == (
        1,
        f"error: 'colour' is not a settable field of {P.ref} items; valid: priority\n",
    )


@pytest.mark.covers("<type> update", "--as")
async def test_update_attributes_the_edit_to_the_named_slug(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), "update", "--title", "Quiet", "--as", "manager"])
    await _ok(invoke, [P.ref, str(TASK), "update", "--title", "Anonymous"])
    assert await _actors(invoke, f"{P.ref_prefix}-{TASK}", "update") == ["manager", "system"]


@pytest.mark.covers("<type> update", "--as")
async def test_update_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), "update", "--title", "T", "--as", "ghost"]) == (
        1,
        "error: unknown slug 'ghost'; valid slugs: manager\n",
    )


@pytest.mark.covers("<type> update")
async def test_update_refuses_a_call_that_changes_nothing(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), "update"]) == (
        1,
        "error: nothing to update (pass at least one field, e.g. --title/--status)\n",
    )


@pytest.mark.covers("<type> update", "--parent", "--no-parent")
async def test_update_refuses_parent_with_no_parent(populated_project, invoke) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), "update", "--parent", str(FEATURE), "--no-parent"])
    assert out == (1, "error: use either --parent or --no-parent, not both\n")


@pytest.mark.covers("<type> update", "--assignee", "--clear-assignee")
async def test_update_refuses_assignee_with_clear_assignee(populated_project, invoke) -> None:
    out = await _ran(
        invoke, [P.ref, str(TASK), "update", "--assignee", "manager", "--clear-assignee"]
    )
    assert out == (1, "error: use --assignee or --clear-assignee, not both\n")


@pytest.mark.covers("<type> update", "--<field>", "--no-<field>")
async def test_update_refuses_priority_with_no_priority(populated_project, invoke) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), "update", "--priority", "high", "--no-priority"])
    assert out == (1, "error: use either --priority or --no-priority, not both\n")


@pytest.mark.covers("<type> update", "--add-label", "--rm-label")
async def test_update_removes_a_label_that_is_added_and_removed_in_one_call(
    populated_project, invoke
) -> None:
    await _ok(invoke, [P.ref, str(TASK), "update", "--add-label", "keep"])
    out = await _ran(
        invoke,
        [P.ref, str(TASK), "update", "--add-label", "tmp", "--rm-label", "tmp", "--rm-label", "x"],
    )
    assert out == (0, f"updated {P.ref_prefix}-3  {TASK_PATH}\n")
    assert (await _show(invoke))["labels"] == ["keep"]


@pytest.mark.covers("<type> update", "--set", "--unset")
async def test_update_unsets_an_attribute_that_is_set_and_unset_in_one_call(
    populated_project, invoke
) -> None:
    out = await _ran(
        invoke,
        [P.ref, str(TASK), "update", "--set", "priority=low", "--unset", "priority"],
    )
    assert out == (0, f"updated {P.ref_prefix}-3  {TASK_PATH}\n")
    assert "priority" not in await _show(invoke)


# --- show -----------------------------------------------------------------------------------

SHOWN_HEAD = [
    "╭───────────────────────────────────────────────────╮",
    f"│ {P.ref_prefix}-3  ({P.ref})                                    │",
    "│ title: Build the query parser                     │",
    "│ status: Draft                                     │",
    f"│ parent: {P.host_prefix}-2                                    │",
    "│ author: manager                                   │",
    f"│ file: {P.ref_folder}/{P.ref_prefix}-000003-build-the-query-parser.md │",
    "╰───────────────────────────────────────────────────╯",
    "",
    "## Description",
    "",
    f"_TODO: describe this {P.ref}._",
    "",
    "Subtask  Status  Assignee  Title                Story",
    f"{P.kind_prefix}1      Todo              Tokenise the input   {P.target_prefix}1  ",
    f"{P.kind_prefix}2      Todo              Parse the operators       ",
]
PLACEHOLDER = f"_Describe this {P.kind} here — free-form paragraphs or bullet lists._"


def _subtask_json(local_id: str, title: str, story: str | None) -> dict[str, Any]:
    status = {"badge": "⚪ Todo", "intent": "neutral"}
    return {
        "local_id": local_id,
        "title": title,
        "status": "Todo",
        "assignee": None,
        "maps_to": story,
        "deferred_to": None,
        "body": PLACEHOLDER,
        "badges": {},
        "discussion": [],
        "display": {
            "type": "Subtask",
            "status": status,
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
        },
    }


@pytest.mark.covers("<type> show", "--json")
async def test_show_json_prints_the_item_as_one_object(populated_project, invoke) -> None:
    body = f"## Description\n\n_TODO: describe this {P.ref}._"
    expected = {
        "sequence_id": 3,
        "type": P.ref,
        "title": "Build the query parser",
        "slug": "build-the-query-parser",
        "status": "Draft",
        "description": "",
        "parent": f"{P.host_prefix}-2",
        "author": "manager",
        "assignee": None,
        "labels": [],
        "refs": [],
        "subentities": [
            _subtask_json(f"{P.kind_prefix}1", "Tokenise the input", f"{P.target_prefix}1"),
            _subtask_json(f"{P.kind_prefix}2", "Parse the operators", None),
        ],
        "path": TASK_PATH,
        "created_at": FROZEN_STAMP,
        "updated_at": FROZEN_STAMP,
        "created_session": None,
        "modified_session": None,
        "id": f"{P.ref_prefix}-3",
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
                "kind": P.kind,
                "columns": ["Subtask", "Status", "Assignee", "Title", "Story"],
                "rows": [
                    [f"{P.kind_prefix}1", "Todo", "", "Tokenise the input", f"{P.target_prefix}1"],
                    [f"{P.kind_prefix}2", "Todo", "", "Parse the operators", ""],
                ],
            },
            "attributes": [],
        },
    }
    # Compared as text, so the key order is held as well as the content.
    output = await _ok(invoke, [P.ref, str(TASK), "show", "--json"])
    assert output == json.dumps(expected, indent=2) + "\n"


MILESTONE = 5
MILESTONE_SCOPE = (
    "## Objective\n\n_TODO: what reaching this milestone means — the outcome it marks, in "
    "one or two sentences._\n\n## Scope boundary\n\n_TODO: what counts toward this milestone "
    "and what doesn't. Membership itself is never listed\nhere — join work to it with `ref "
    "add MILE-… --kind targets` and read `sq milestone <n> show`\nfor the current roll-up, "
    "computed fresh from the corpus every time._\n\n"
)
MILESTONE_ROLLUP = (
    "## Delivered (0)\n\n_(none yet)_\n\n## Outstanding (0)\n\n_(nothing outstanding)_"
    "\n\n## Settled without delivering (0)\n\n_(none)_"
)


async def _milestone_with_a_target_date(invoke) -> None:
    """Create milestone 5 and set its declared, labelled `target_date` attribute."""
    await _ok(invoke, ["create", "milestone", "Beta", "--author", "manager"])
    await _ok(invoke, ["milestone", str(MILESTONE), "update", "--set", "target_date=2026-12-01"])


@pytest.mark.covers("<type> show")
async def test_show_prints_a_declared_attribute_under_its_label(populated_project, invoke) -> None:
    await _milestone_with_a_target_date(invoke)
    shown = await _ok(invoke, ["milestone", str(MILESTONE), "show"])
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


@pytest.mark.covers("<type> show", "--json")
async def test_show_json_lists_a_declared_attribute_with_its_label(
    populated_project, invoke
) -> None:
    await _milestone_with_a_target_date(invoke)
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
        "body": MILESTONE_SCOPE + "<!-- sq:view:milestone_rollup -->",
        "views": {"milestone_rollup": {"delivered": [], "outstanding": [], "settled": []}},
        "discussion": [],
        "badges": {},
        "display": {
            "type": "Milestone",
            "status": {"badge": "⚪ Draft", "intent": "neutral"},
            "badges": {},
            "assignee": None,
            "body": MILESTONE_SCOPE + MILESTONE_ROLLUP,
            "summary": None,
            "attributes": [{"key": "target_date", "label": "target date", "value": "2026-12-01"}],
        },
    }
    output = await _ok(invoke, ["milestone", str(MILESTONE), "show", "--json"])
    assert output == json.dumps(expected, indent=2) + "\n"


@pytest.mark.covers("<type> show", "--raw")
async def test_show_raw_prints_a_declared_attribute_under_its_label(
    populated_project, invoke
) -> None:
    await _milestone_with_a_target_date(invoke)
    raw = await _ok(invoke, ["milestone", str(MILESTONE), "show", "--raw"])
    assert raw.splitlines() == [
        "# MILE-5 — Beta",
        "",
        "- **status:** Draft",
        "- **target date:** 2026-12-01",
        "- **author:** manager",
        "",
        *(MILESTONE_SCOPE + MILESTONE_ROLLUP).splitlines(),
    ]


@pytest.mark.covers("<type> show", "--raw")
async def test_show_raw_prints_plain_markdown(populated_project, invoke) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), "show", "--raw"])
    assert out == (
        0,
        f"# {P.ref_prefix}-3 — Build the query parser\n\n"
        f"- **status:** Draft\n- **parent:** {P.host_prefix}-2\n- **author:** manager\n\n"
        f"## Description\n\n_TODO: describe this {P.ref}._\n",
    )


@pytest.mark.covers("<type> show", "--full")
async def test_show_full_adds_one_pane_per_subtask(populated_project, invoke) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), "show", "--full"])
    assert out == (
        0,
        "\n".join(
            [
                *SHOWN_HEAD,
                f"=== {P.kind_prefix}1 — Tokenise the input  ⚪ Todo  {P.target_prefix}1 ===",
                PLACEHOLDER,
                "",
                f"=== {P.kind_prefix}2 — Parse the operators  ⚪ Todo ===",
                PLACEHOLDER,
                "",
                "",
            ]
        ),
    )


@pytest.mark.covers("<type> show", "--comments")
async def test_show_comments_appends_the_discussion(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), "comment", "-m", "Looks good", "--as", "manager"])
    short = json.loads(await _ok(invoke, [P.ref, str(TASK), "comments", "--json"]))[0]["short_hash"]
    out = await _ran(invoke, [P.ref, str(TASK), "show", "--comments"])
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
    assert await _ran(invoke, [P.ref, str(TASK), "status", "Ready"]) == (
        0,
        f"{P.ref_prefix}-3 → Ready\n",
    )
    assert (await _show(invoke))["status"] == "Ready"


@pytest.mark.covers("<type> status", "STATUS")
async def test_status_refuses_a_transition_the_lifecycle_does_not_allow(
    populated_project, invoke
) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), "status", "Done"]) == (
        1,
        f"error: {P.ref} cannot move Draft → Done (use --force to override)\n",
    )
    assert (await _show(invoke))["status"] == "Draft"


@pytest.mark.covers("<type> status", "STATUS")
async def test_status_refuses_a_status_no_lifecycle_declares(populated_project, invoke) -> None:
    code, output = await _ran(invoke, [P.ref, str(TASK), "status", "Sleeping"])
    assert (code, output.split(" (one of:")[0]) == (1, "error: unknown status 'Sleeping'")


@pytest.mark.covers("<type> status", "--force")
async def test_status_force_makes_a_transition_the_lifecycle_refuses(
    populated_project, invoke
) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), "status", "Done", "--force"]) == (
        0,
        f"{P.ref_prefix}-3 → Done\n",
    )
    assert (await _show(invoke))["status"] == "Done"


@pytest.mark.covers("<type> status", "--as")
async def test_status_attributes_the_move_to_the_named_slug(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), "status", "Ready", "--as", "manager"])
    await _ok(invoke, [P.ref, str(TASK), "status", "InProgress"])
    assert await _actors(invoke, f"{P.ref_prefix}-{TASK}", "status") == ["manager", "system"]


@pytest.mark.covers("<type> status", "--json")
async def test_status_json_prints_the_moved_items_row(populated_project, invoke) -> None:
    moved = await _ok(invoke, [P.ref, str(TASK), "status", "Ready", "--json"])
    # Compared as text, so the key order is held as well as the content.
    assert (
        moved
        == json.dumps(
            {
                "entry": {
                    "sequence_id": 3,
                    "type": P.ref,
                    "title": "Build the query parser",
                    "slug": "build-the-query-parser",
                    "status": "Ready",
                    "description": "",
                    "parent": f"{P.host_prefix}-2",
                    "author": "manager",
                    "assignee": None,
                    "labels": [],
                    "refs": [],
                    "subentities": [
                        {
                            "local_id": f"{P.kind_prefix}1",
                            "title": "Tokenise the input",
                            "status": "Todo",
                            "assignee": None,
                            "maps_to": f"{P.target_prefix}1",
                            "deferred_to": None,
                            "badges": {},
                        },
                        {
                            "local_id": f"{P.kind_prefix}2",
                            "title": "Parse the operators",
                            "status": "Todo",
                            "assignee": None,
                            "maps_to": None,
                            "deferred_to": None,
                            "badges": {},
                        },
                    ],
                    "path": TASK_PATH,
                    "created_at": FROZEN_STAMP,
                    "updated_at": FROZEN_STAMP,
                    "created_session": None,
                    "modified_session": None,
                    "id": f"{P.ref_prefix}-3",
                    "badges": {},
                    "display": {
                        "type": "Task",
                        "status": {"badge": "⚪ Ready", "intent": "neutral"},
                        "badges": {},
                        "assignee": None,
                    },
                },
            },
            indent=2,
        )
        + "\n"
    )
    assert (await _show(invoke))["status"] == "Ready"


@pytest.mark.covers("<type> status", "--as")
async def test_status_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), "status", "Ready", "--as", "ghost"]) == (
        1,
        "error: unknown slug 'ghost'; valid slugs: manager\n",
    )


# --- body -----------------------------------------------------------------------------------


@pytest.mark.covers("<type> body", "--message")
async def test_body_sets_each_message_as_a_paragraph(populated_project, invoke) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), "body", "-m", "First", "-m", "Second"])
    assert out == (0, f"{P.ref_prefix}-3: body set\n")
    assert (await _show(invoke))["body"] == "First\n\nSecond"


@pytest.mark.covers("<type> body")
async def test_body_refuses_a_call_with_no_text(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), "body"]) == (
        1,
        "error: provide the body via -m (repeatable) or --file PATH ('-' for stdin)\n",
    )


@pytest.mark.covers("<type> body", "--file")
async def test_body_reads_the_text_from_a_file(populated_project, invoke) -> None:
    _write_body_file()
    assert await _ran(invoke, [P.ref, str(TASK), "body", "--file", "body.md"]) == (
        0,
        f"{P.ref_prefix}-3: body set\n",
    )
    assert (await _show(invoke))["body"] == "From a file"


@pytest.mark.covers("<type> body", "--file")
async def test_body_reads_the_text_from_stdin_for_a_dash(populated_project, invoke) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), "body", "--file", "-"], input="Piped in\n")
    assert out == (0, f"{P.ref_prefix}-3: body set\n")
    assert (await _show(invoke))["body"] == "Piped in"


def _write_bytes(raw: bytes) -> None:
    Path("body.md").write_bytes(raw)


@pytest.mark.covers("<type> body", "--file")
async def test_body_refuses_a_file_that_is_not_utf8(populated_project, invoke) -> None:
    _write_bytes(b"ok\xff\xfe")
    assert await _ran(invoke, [P.ref, str(TASK), "body", "--file", "body.md"]) == (
        1,
        "error: cannot read file 'body.md': not valid utf-8 (invalid start byte at byte 2)\n",
    )


@pytest.mark.covers("<type> body", "--file")
async def test_body_refuses_a_file_that_does_not_exist(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), "body", "--file", "missing.md"]) == (
        1,
        "error: cannot read file 'missing.md': No such file or directory\n",
    )


@pytest.mark.covers("<type> body", "--message", "--file")
async def test_body_refuses_message_with_file(populated_project, invoke) -> None:
    _write_body_file()
    out = await _ran(invoke, [P.ref, str(TASK), "body", "-m", "Text", "--file", "body.md"])
    assert out == (1, "error: provide the body via -m or --file, not both\n")


@pytest.mark.covers("<type> body", "--append")
async def test_body_append_adds_after_the_existing_body(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), "body", "-m", "First"])
    out = await _ran(invoke, [P.ref, str(TASK), "body", "-m", "Second", "--append"])
    assert out == (0, f"{P.ref_prefix}-3: body appended\n")
    assert (await _show(invoke))["body"] == "First\n\nSecond"


@pytest.mark.covers("<type> body", "--force")
async def test_body_force_replaces_a_body_already_written(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), "body", "-m", "First"])
    refused = await _ran(invoke, [P.ref, str(TASK), "body", "-m", "Second"])
    assert refused == (
        1,
        f"error: {P.ref_prefix}-3 already has a body (1 line); setting one would discard it:\n\n"
        "    First\n\n"
        "Nothing was written. Add to it with `--append`, or pass `--force` to replace it.\n",
    )
    forced = await _ran(invoke, [P.ref, str(TASK), "body", "-m", "Second", "--force"])
    assert forced == (0, f"{P.ref_prefix}-3: body set\n")
    assert (await _show(invoke))["body"] == "Second"


@pytest.mark.covers("<type> body", "--as")
async def test_body_attributes_the_edit_to_the_named_slug(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), "body", "-m", "First", "--as", "manager"])
    await _ok(invoke, [P.ref, str(TASK), "body", "-m", "Second", "--append"])
    assert await _actors(invoke, f"{P.ref_prefix}-{TASK}", "body") == ["manager", "system"]


@pytest.mark.covers("<type> body", "--as")
async def test_body_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), "body", "-m", "x", "--as", "ghost"]) == (
        1,
        "error: unknown slug 'ghost'; valid slugs: manager\n",
    )


# --- retype ---------------------------------------------------------------------------------


@pytest.mark.covers("<type> retype", "NEW-TYPE")
async def test_retype_reclassifies_the_item_and_keeps_its_number(populated_project, invoke) -> None:
    loose = await _create_task(invoke)
    out = await _ran(invoke, [P.ref, str(loose), "retype", "bug"])
    assert out == (
        0,
        f"retyped {P.ref_prefix}-{loose} → BUG-{loose}  bugs/BUG-00000{loose}-loose-end.md\n"
        "  status reset: Draft → Open (workflows differ)\n",
    )
    moved = await _show(invoke, loose, "bug")
    assert (moved["id"], moved["status"]) == (f"BUG-{loose}", "Open")


@pytest.mark.covers("<type> retype", "NEW-TYPE")
async def test_retype_refuses_an_item_that_holds_sub_entities(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), "retype", "bug"]) == (
        1,
        f"error: cannot retype {P.ref_prefix}-3: it has sub-entities. "
        "Clear or move all sub-entities first, then retype.\n",
    )


@pytest.mark.covers("<type> retype", "NEW-TYPE")
async def test_retype_refuses_the_type_the_item_already_has(populated_project, invoke) -> None:
    loose = await _create_task(invoke)
    assert await _ran(invoke, [P.ref, str(loose), "retype", P.ref]) == (
        1,
        f"error: {P.ref_prefix}-{loose} is already of type {P.ref}\n",
    )


@pytest.mark.covers("<type> retype", "NEW-TYPE")
async def test_retype_refuses_a_roster_type(populated_project, invoke) -> None:
    loose = await _create_task(invoke)
    assert await _ran(invoke, [P.ref, str(loose), "retype", "role"]) == (
        1,
        "error: cannot retype to 'role'; valid targets: "
        f"bug, contract, decision, epic, {P.host}, guide, milestone, {P.third}, {P.ref}\n",
    )


@pytest.mark.covers("<type> retype", "NEW-TYPE")
async def test_retype_refuses_a_type_the_spec_does_not_declare(populated_project, invoke) -> None:
    loose = await _create_task(invoke)
    assert await _ran(invoke, [P.ref, str(loose), "retype", P.target_kind]) == (
        1,
        f"error: unknown type '{P.target_kind}' (one of: bug, contract, decision, epic, {P.host}, guide, "
        f"milestone, operator, {P.third}, role, skill, {P.ref})\n",
    )


@pytest.mark.covers("<type> retype", "--as")
async def test_retype_attributes_the_edit_to_the_named_slug(populated_project, invoke) -> None:
    loose = await _create_task(invoke)
    await _ok(invoke, [P.ref, str(loose), "retype", "bug", "--as", "manager"])
    assert await _actors(invoke, f"BUG-{loose}", "retype") == ["manager"]


@pytest.mark.covers("<type> retype", "--as")
async def test_retype_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    loose = await _create_task(invoke)
    assert await _ran(invoke, [P.ref, str(loose), "retype", "bug", "--as", "ghost"]) == (
        1,
        "error: unknown slug 'ghost'; valid slugs: manager\n",
    )


# --- remove ---------------------------------------------------------------------------------


@pytest.mark.covers("<type> remove", "--yes")
async def test_remove_yes_deletes_the_item_without_asking(populated_project, invoke) -> None:
    loose = await _create_task(invoke)
    assert await _ran(invoke, [P.ref, str(loose), "remove", "--yes"]) == (
        0,
        f"removed {P.ref_prefix}-{loose}\n",
    )
    assert (await _ran(invoke, [P.ref, str(loose), "show"]))[0] == 1


@pytest.mark.covers("<type> remove")
async def test_remove_asks_for_confirmation_and_keeps_the_item_when_declined(
    populated_project, invoke
) -> None:
    loose = await _create_task(invoke)
    out = await _ran(invoke, [P.ref, str(loose), "remove"], input="n\n")
    assert out == (1, f"Remove {P.ref_prefix}-{loose}? This cannot be undone. [y/N]: n\nAborted.\n")
    assert (await _show(invoke, loose))["id"] == f"{P.ref_prefix}-{loose}"


@pytest.mark.covers("<type> remove", "--yes")
async def test_remove_refuses_an_item_other_items_reference(populated_project, invoke) -> None:
    loose = await _create_task(invoke)
    await _ok(invoke, [P.ref, str(TASK), "ref", "add", str(loose)])
    assert await _ran(invoke, [P.ref, str(loose), "remove", "--yes"]) == (
        1,
        f"error: cannot remove {P.ref_prefix}-{loose}: it is referenced by: {P.ref_prefix}-3. "
        "Re-parent/remove those items first, or re-run with --force to sever them.\n",
    )


@pytest.mark.covers("<type> remove", "--force")
async def test_remove_force_cuts_the_refs_other_items_carry(populated_project, invoke) -> None:
    loose = await _create_task(invoke)
    await _ok(invoke, [P.ref, str(TASK), "ref", "add", str(loose)])
    out = await _ran(invoke, [P.ref, str(loose), "remove", "--yes", "--force"])
    assert out == (0, f"removed {P.ref_prefix}-{loose}\n  severed refs in: {P.ref_prefix}-3\n")
    assert (await _show(invoke))["refs"] == []


@pytest.mark.covers("<type> remove", "--json")
async def test_remove_json_prints_the_removed_id_and_the_cut_refs(
    populated_project, invoke
) -> None:
    loose = await _create_task(invoke)
    await _ok(invoke, [P.ref, str(TASK), "ref", "add", str(loose)])
    out = await _ran(invoke, [P.ref, str(loose), "remove", "--yes", "--force", "--json"])
    assert (out[0], json.loads(out[1])) == (
        0,
        {"removed_id": f"{P.ref_prefix}-{loose}", "severed_refs": [f"{P.ref_prefix}-3"]},
    )


@pytest.mark.covers("<type> remove", "--as")
async def test_remove_attributes_the_deletion_to_the_named_slug(populated_project, invoke) -> None:
    loose = await _create_task(invoke)
    await _ok(invoke, [P.ref, str(loose), "remove", "--yes", "--as", "manager"])
    assert await _actors(invoke, f"{P.ref_prefix}-{loose}", "remove") == ["manager"]


@pytest.mark.covers("<type> remove", "--as")
async def test_remove_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    loose = await _create_task(invoke)
    assert await _ran(invoke, [P.ref, str(loose), "remove", "--yes", "--as", "ghost"]) == (
        1,
        "error: unknown slug 'ghost'; valid slugs: manager\n",
    )


# --- ref add / ref rm -----------------------------------------------------------------------


@pytest.mark.covers("<type> ref add", "TARGET")
async def test_ref_add_links_the_item_to_the_target_as_related(populated_project, invoke) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), "ref", "add", f"{P.third_prefix}-{REVIEW}"])
    assert out == (0, f"{P.ref_prefix}-3 → {P.third_prefix}-{REVIEW} (related)\n")
    assert (await _show(invoke))["refs"] == [f"{P.third_prefix}-{REVIEW}"]


@pytest.mark.covers("<type> ref add", "TARGET")
async def test_ref_add_refuses_a_target_that_is_not_an_item_id(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), "ref", "add", "elsewhere"]) == (
        1,
        "error: invalid item id 'elsewhere' (use a bare number or a full ID like TYPE-NNNNNN)\n",
    )


@pytest.mark.covers("<type> ref add", "--kind")
async def test_ref_add_kind_names_the_relation(populated_project, invoke) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), "ref", "add", str(REVIEW), "--kind", "fixes"])
    assert out == (0, f"{P.ref_prefix}-3 → {P.third_prefix}-{REVIEW} (fixes)\n")
    assert (await _show(invoke))["refs"] == [f"{P.third_prefix}-{REVIEW}:fixes"]


@pytest.mark.covers("<type> ref add", "--kind")
async def test_ref_add_refuses_a_kind_the_spec_does_not_declare(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), "ref", "add", str(REVIEW), "--kind", "likes"]) == (
        1,
        "error: unknown ref kind 'likes'. Valid kinds: addresses, blocks, depends-on, "
        "duplicates, fixes, implements, related, scopes, supersedes, targets\n",
    )


@pytest.mark.covers("<type> ref add", "--as")
async def test_ref_add_attributes_the_edit_to_the_named_slug(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), "ref", "add", str(REVIEW), "--as", "manager"])
    await _ok(invoke, [P.ref, str(TASK), "ref", "add", str(FEATURE)])
    assert await _actors(invoke, f"{P.ref_prefix}-{TASK}", "ref") == ["manager", "system"]


@pytest.mark.covers("<type> ref add", "--as")
async def test_ref_add_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), "ref", "add", str(REVIEW), "--as", "ghost"])
    assert out == (1, "error: unknown slug 'ghost'; valid slugs: manager\n")


@pytest.mark.covers("<type> ref rm", "TARGET")
async def test_ref_rm_drops_every_ref_to_the_target(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), "ref", "add", str(REVIEW), "--kind", "fixes"])
    await _ok(invoke, [P.ref, str(TASK), "ref", "add", str(REVIEW), "--kind", "related"])
    await _ok(invoke, [P.ref, str(TASK), "ref", "add", str(FEATURE)])
    out = await _ran(invoke, [P.ref, str(TASK), "ref", "rm", f"{P.third_prefix}-{REVIEW}"])
    assert out == (0, f"removed {P.ref_prefix}-3 → {P.third_prefix}-{REVIEW}\n")
    assert (await _show(invoke))["refs"] == [f"{P.host_prefix}-{FEATURE}"]


@pytest.mark.covers("<type> ref rm", "TARGET")
async def test_ref_rm_refuses_a_target_the_item_has_no_ref_to(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), "ref", "rm", str(REVIEW)]) == (
        1,
        f"error: {P.ref_prefix}-3 has no ref to {P.third_prefix}-{REVIEW}\n",
    )


@pytest.mark.covers("<type> ref rm", "TARGET")
async def test_ref_rm_refuses_a_target_that_is_not_an_item_id(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), "ref", "rm", "elsewhere"]) == (
        1,
        "error: invalid item id 'elsewhere' (use a bare number or a full ID like TYPE-NNNNNN)\n",
    )


@pytest.mark.covers("<type> ref rm", "--as")
async def test_ref_rm_attributes_the_edit_to_the_named_slug(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), "ref", "add", str(REVIEW)])
    await _ok(invoke, [P.ref, str(TASK), "ref", "rm", str(REVIEW), "--as", "manager"])
    assert (await _actors(invoke, f"{P.ref_prefix}-{TASK}", "ref"))[-1] == "manager"


@pytest.mark.covers("<type> ref rm", "--as")
async def test_ref_rm_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), "ref", "rm", str(REVIEW), "--as", "ghost"])
    assert out == (1, "error: unknown slug 'ghost'; valid slugs: manager\n")


# --- refs -----------------------------------------------------------------------------------


@pytest.mark.covers("<type> refs", "--out")
async def test_refs_out_lists_the_refs_the_item_carries(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), "ref", "add", str(REVIEW), "--kind", "fixes"])
    await _ok(invoke, [P.third, str(REVIEW), "ref", "add", str(FEATURE)])
    out = await _ran(invoke, [P.ref, str(TASK), "refs", "--out"])
    assert out == (0, f"→ refs      \nID     Kind \nREV-{REVIEW}  fixes\n")


@pytest.mark.covers("<type> refs", "--out", "--in")
async def test_refs_out_with_in_lists_both_directions(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), "ref", "add", str(REVIEW), "--kind", "fixes"])
    await _ok(invoke, [P.third, str(REVIEW), "ref", "add", str(TASK), "--kind", "addresses"])
    out = await _ran(invoke, [P.ref, str(TASK), "refs", "--out", "--in"])
    assert out == (
        0,
        f"→ refs      \nID     Kind \nREV-{REVIEW}  fixes\n"
        f"← backrefs      \nID     Kind     \nREV-{REVIEW}  addresses\n",
    )


@pytest.mark.covers("<type> refs", "--in")
async def test_refs_in_lists_the_refs_other_items_carry_to_it(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), "ref", "add", str(REVIEW)])
    await _ok(invoke, [P.third, str(REVIEW), "ref", "add", str(TASK), "--kind", "addresses"])
    out = await _ran(invoke, [P.ref, str(TASK), "refs", "--in"])
    assert out == (0, f"← backrefs      \nID     Kind     \nREV-{REVIEW}  addresses\n")


@pytest.mark.covers("<type> refs", "--all")
async def test_refs_all_lists_both_directions(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), "ref", "add", str(REVIEW), "--kind", "fixes"])
    out = await _ran(invoke, [P.ref, str(TASK), "refs", "--all"])
    assert out == (
        0,
        f"→ refs      \nID     Kind \nREV-{REVIEW}  fixes\n← backrefs: none\n",
    )


@pytest.mark.covers("<type> refs", "--json")
async def test_refs_json_prints_an_array_per_direction_shown(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), "ref", "add", str(REVIEW), "--kind", "fixes"])
    await _ok(invoke, [P.third, str(REVIEW), "ref", "add", str(TASK), "--kind", "addresses"])
    default = await _ok(invoke, [P.ref, str(TASK), "refs", "--json"])
    both = await _ok(invoke, [P.ref, str(TASK), "refs", "--all", "--json"])
    fixes = {"id": f"{P.third_prefix}-{REVIEW}", "kind": "fixes", "display": {"kind": "Fixes"}}
    addresses = {
        "id": f"{P.third_prefix}-{REVIEW}",
        "kind": "addresses",
        "display": {"kind": "Addresses"},
    }
    # Compared as text, so the key order is held as well as the content.
    assert (default, both) == (
        json.dumps({"out": [fixes]}, indent=2) + "\n",
        json.dumps({"out": [fixes], "in": [addresses]}, indent=2) + "\n",
    )


# --- comments -------------------------------------------------------------------------------


@pytest.mark.covers("<host> comments", "--json")
async def test_comments_json_prints_one_object_per_comment(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), "comments", "--json"]) == (0, "[]\n")
    await _ok(invoke, [P.ref, str(TASK), "comment", "-m", "Looks good", "--as", "manager"])
    comments = json.loads(await _ok(invoke, [P.ref, str(TASK), "comments", "--json"]))
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
    out = await _ran(invoke, [P.ref, str(TASK), "view", "add", "milestone_rollup"])
    assert out == (0, f"{P.ref_prefix}-3: view milestone_rollup placed in sq:body\n")
    assert (await _show(invoke))["views"] == {
        "milestone_rollup": {"delivered": [], "outstanding": [], "settled": []}
    }


@pytest.mark.covers("<type> view add", "NAME")
async def test_view_add_refuses_a_name_no_view_declares(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), "view", "add", "gantt"]) == (
        1,
        "error: no declared view 'gantt' with a resolvable presentation template; "
        "see `sq workflow views` for the declared set\n",
    )


@pytest.mark.covers("<type> view disable", "NAME")
async def test_view_disable_stops_showing_the_view(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), "view", "add", "milestone_rollup"])
    out = await _ran(invoke, [P.ref, str(TASK), "view", "disable", "milestone_rollup"])
    assert out == (0, f"{P.ref_prefix}-3: view milestone_rollup disabled in sq:body\n")
    assert (await _show(invoke))["views"] == {}


@pytest.mark.covers("<type> view add", "--as")
async def test_view_add_attributes_the_edit_to_the_named_slug(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), "view", "add", "milestone_rollup", "--as", "manager"])
    assert await _actors(invoke, f"{P.ref_prefix}-{TASK}", "view") == ["manager"]


@pytest.mark.covers("<type> view add", "--as")
async def test_view_add_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    out = await _ran(invoke, [P.ref, str(TASK), "view", "add", "milestone_rollup", "--as", "ghost"])
    assert out == (1, "error: unknown slug 'ghost'; valid slugs: manager\n")


@pytest.mark.covers("<type> view disable", "--as")
async def test_view_disable_attributes_the_edit_to_the_named_slug(
    populated_project, invoke
) -> None:
    await _ok(invoke, [P.ref, str(TASK), "view", "add", "milestone_rollup"])
    await _ok(invoke, [P.ref, str(TASK), "view", "disable", "milestone_rollup", "--as", "manager"])
    assert await _actors(invoke, f"{P.ref_prefix}-{TASK}", "view") == ["system", "manager"]


@pytest.mark.covers("<type> view disable", "--as")
async def test_view_disable_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    out = await _ran(
        invoke, [P.ref, str(TASK), "view", "disable", "milestone_rollup", "--as", "ghost"]
    )
    assert out == (1, "error: unknown slug 'ghost'; valid slugs: manager\n")


# --- the written row, with --json -------------------------------------------------------------


def _task_row(*, labels: list[str] | None = None, refs: list[str] | None = None) -> dict[str, Any]:
    """The populated task's row before its display, with *labels* and *refs*."""

    def subtask(local_id: str, title: str, maps_to: str | None) -> dict[str, Any]:
        return {
            "local_id": local_id,
            "title": title,
            "status": "Todo",
            "assignee": None,
            "maps_to": maps_to,
            "deferred_to": None,
            "badges": {},
        }

    return {
        "sequence_id": 3,
        "type": P.ref,
        "title": "Build the query parser",
        "slug": "build-the-query-parser",
        "status": "Draft",
        "description": "",
        "parent": f"{P.host_prefix}-2",
        "author": "manager",
        "assignee": None,
        "labels": labels or [],
        "refs": refs or [],
        "subentities": [
            subtask(f"{P.kind_prefix}1", "Tokenise the input", f"{P.target_prefix}1"),
            subtask(f"{P.kind_prefix}2", "Parse the operators", None),
        ],
        "path": TASK_PATH,
        "created_at": FROZEN_STAMP,
        "updated_at": FROZEN_STAMP,
        "created_session": None,
        "modified_session": None,
        "id": f"{P.ref_prefix}-3",
        "badges": {},
    }


def _written(row: dict[str, Any], **outcome: Any) -> str:
    """*row* as the written entry with the task's display, and the write's *outcome* beside it, as
    `--json` prints it: compared as text, so the key order is held as well as the content."""
    shown = {
        "type": "Task",
        "status": {"badge": "⚪ Draft", "intent": "neutral"},
        "badges": {},
        "assignee": None,
    }
    return json.dumps({"entry": {**row, "display": shown}, **outcome}, indent=2) + "\n"


@pytest.mark.covers("<type> update", "--json")
async def test_update_json_prints_the_items_row_after_the_update(populated_project, invoke) -> None:
    printed = await _ok(invoke, [P.ref, str(TASK), "update", "--add-label", "x", "--json"])
    assert printed == _written(_task_row(labels=["x"]), nothing_to_clear=False)


@pytest.mark.covers("<type> body", "--json")
async def test_body_json_prints_the_items_row_after_the_write(populated_project, invoke) -> None:
    printed = await _ok(invoke, [P.ref, str(TASK), "body", "-m", "Text", "--json"])
    assert printed == _written(_task_row())
    assert (await _show(invoke))["body"] == "Text"


@pytest.mark.covers("<type> retype", "--json")
async def test_retype_json_prints_the_items_row_under_its_new_type(
    populated_project, invoke
) -> None:
    number = await _create_task(invoke)
    printed = await _ok(invoke, [P.ref, str(number), "retype", "bug", "--json"])
    retyped = {
        "sequence_id": number,
        "type": "bug",
        "title": "Loose end",
        "slug": "loose-end",
        "status": "Open",
        "description": "",
        "parent": None,
        "author": "manager",
        "assignee": None,
        "labels": [],
        "refs": [],
        "subentities": [],
        "path": f"bugs/BUG-{number:06d}-loose-end.md",
        "created_at": FROZEN_STAMP,
        "updated_at": FROZEN_STAMP,
        "created_session": None,
        "modified_session": None,
        "id": f"BUG-{number}",
        "badges": {},
        "display": {
            "type": "Bug",
            "status": {"badge": "🔴 Open", "intent": "danger"},
            "badges": {},
            "assignee": None,
        },
    }
    outcome = {
        "old_id": f"{P.ref_prefix}-{number}",
        "old_status": "Draft",
        "status_reset": True,
        "rewritten": [],
    }
    assert printed == json.dumps({"entry": retyped, **outcome}, indent=2) + "\n"


@pytest.mark.covers("<type> ref add", "--json")
async def test_ref_add_json_prints_the_items_row_with_the_ref(populated_project, invoke) -> None:
    printed = await _ok(invoke, [P.ref, str(TASK), "ref", "add", str(REVIEW), "--json"])
    expected = _written(
        _task_row(refs=[f"{P.third_prefix}-4"]), target=f"{P.third_prefix}-4", kind="related"
    )
    assert printed == expected


@pytest.mark.covers("<type> ref rm", "--json")
async def test_ref_rm_json_prints_the_items_row_without_the_ref(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), "ref", "add", str(REVIEW)])
    printed = await _ok(invoke, [P.ref, str(TASK), "ref", "rm", str(REVIEW), "--json"])
    assert printed == _written(_task_row(), target=f"{P.third_prefix}-4", kinds=["related"])


@pytest.mark.covers("<type> view add", "--json")
async def test_view_add_json_prints_the_items_row_and_the_tag_change(
    populated_project, invoke
) -> None:
    printed = await _ok(invoke, [P.ref, str(TASK), "view", "add", "item_skill", "--json"])
    expected = _written(_task_row(), view="item_skill", changed=True, was_present=False)
    assert printed == expected


@pytest.mark.covers("<type> view disable", "--json")
async def test_view_disable_json_prints_the_items_row_and_the_tag_change(
    populated_project, invoke
) -> None:
    await _ok(invoke, [P.ref, str(TASK), "view", "add", "item_skill"])
    printed = await _ok(invoke, [P.ref, str(TASK), "view", "disable", "item_skill", "--json"])
    expected = _written(_task_row(), view="item_skill", changed=True, was_present=True)
    assert printed == expected


@pytest.mark.covers("<type> remove", "--json")
async def test_remove_json_asks_on_stderr_and_prints_only_the_document_on_stdout(
    populated_project, invoke
) -> None:
    loose = await _create_task(invoke)
    result = await invoke([P.ref, str(loose), "remove", "--json"], input="y\n")
    assert result.exit_code == 0, result.output
    expected = {"removed_id": f"{P.ref_prefix}-{loose}", "severed_refs": []}
    assert result.stdout == json.dumps(expected, indent=2) + "\n"
    assert result.stderr == f"Remove {P.ref_prefix}-{loose}? This cannot be undone. [y/N]: "
