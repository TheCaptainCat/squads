"""`sq workflow`: the cheatsheet, each vocabulary listing in text and JSON, a declared view
resolved against an item, and the override lint."""

import asyncio
import json
from pathlib import Path

import pytest

from tests._helpers import create_item, make_service
from tests._readable import init_readable, lines
from tests._squads import paths_of
from tests.cli import _bundled_documents as documents
from tests.cli._output import json_text, printed, read_json

pytestmark = pytest.mark.anyio

CHEATSHEET_HEAD = [
    "## Team workflow",
    "",
    "- Items are addressed as `sq <type> <number> <verb>` (e.g. `sq task 35 show`);",
    "  create with `sq create <type>`. Run `sq <type> --help` / `sq <type> <n> --help` to explore.",
]
RENDERED_HEAD = [
    "Team workflow",
    "",
    " • Items are addressed as sq <type> <number> <verb> (e.g. sq task 35 show);",
    "   create with sq create <type>. Run sq <type> --help / sq <type> <n> --help to",
    "   explore.",
]


async def _populate_milestone(root: Path) -> None:
    svc = make_service(paths_of(root))
    milestone = await create_item(svc, "milestone", "Ship search")
    await svc.add_ref("TASK-3", milestone.item.id, kind="targets")
    await svc.add_ref("TASK-4", milestone.item.id, kind="targets")
    await svc.set_status("TASK-3", "Done", force=True)


def init_with_milestone(root: Path) -> None:
    """The readable squad plus a milestone that one done task and one open task target."""
    init_readable(root)
    asyncio.run(_populate_milestone(root))


@pytest.fixture
def milestone_project(copy_squad):
    return copy_squad("milestone", init_with_milestone)


async def _run(invoke, *args: str) -> tuple[int, list[str]]:
    result = await invoke(["workflow", *args])
    return result.exit_code, lines(result.output)


# --- the cheatsheet -------------------------------------------------------------------------


@pytest.mark.covers("workflow show")
@pytest.mark.bundled_only("prints the bundled vocabulary")
async def test_workflow_prints_the_rendered_cheatsheet(project, invoke) -> None:
    code, out = await _run(invoke)
    assert (code, out[:5]) == (0, RENDERED_HEAD)
    assert await _run(invoke, "show") == (code, out)


@pytest.mark.covers("workflow", "--raw")
@pytest.mark.bundled_only("lists the bundled vocabulary")
async def test_the_group_raw_prints_the_cheatsheet_as_plain_markdown(project, invoke) -> None:
    code, out = await _run(invoke, "--raw")
    assert (code, out[:4]) == (0, CHEATSHEET_HEAD)


@pytest.mark.covers("workflow show", "--raw")
async def test_show_raw_prints_the_cheatsheet_as_plain_markdown(project, invoke) -> None:
    assert await _run(invoke, "show", "--raw") == await _run(invoke, "--raw")


# --- the vocabulary listings ----------------------------------------------------------------


@pytest.mark.covers("workflow types")
@pytest.mark.bundled_only("prints the bundled vocabulary")
async def test_types_lists_every_declared_type(project, invoke) -> None:
    assert await _run(invoke, "types") == (
        0,
        [
            "Type       Order  Prefix  Reserved  Category",
            "epic       10     EPIC              work",
            "feature    20     FEAT              work",
            "task       30     TASK              work",
            "bug        40     BUG               work",
            "decision   50     ADR               records",
            "contract   55     PRD               records",
            "milestone  57     MILE              records",
            "review     60     REV               work",
            "guide      70     GUIDE             records",
            "role       80     ROLE    yes       roster",
            "skill      90     SKILL   yes       roster",
            "operator   100    OP      yes       roster",
        ],
    )


@pytest.mark.covers("workflow types", "--json")
@pytest.mark.bundled_only("prints the bundled vocabulary")
async def test_types_json_prints_one_object_per_type(project, invoke) -> None:
    output = await printed(invoke, ["workflow", "types", "--json"])
    assert output == json_text(documents.TYPES)


@pytest.mark.covers("workflow subentity-kinds")
@pytest.mark.bundled_only("lists the bundled vocabulary")
async def test_subentity_kinds_lists_every_declared_kind(project, invoke) -> None:
    assert await _run(invoke, "subentity-kinds") == (
        0,
        [
            "Kind     Lifecycle  Plural    Prefix  Heading       Completion  Fields",
            "finding  finding    findings  F       Findings      Fixed       severity",
            "story    subentity  stories   US      User Stories  Done",
            "subtask  subentity  subtasks  ST      Subtasks      Done",
        ],
    )


@pytest.mark.covers("workflow subentity-kinds", "--json")
@pytest.mark.bundled_only("prints the bundled vocabulary")
async def test_subentity_kinds_json_prints_one_object_per_kind(project, invoke) -> None:
    output = await printed(invoke, ["workflow", "subentity-kinds", "--json"])
    assert output == json_text(documents.SUBENTITY_KINDS)


@pytest.mark.covers("workflow lifecycles")
@pytest.mark.bundled_only("lists the bundled vocabulary")
async def test_lifecycles_lists_every_declared_lifecycle(project, invoke) -> None:
    code, out = await _run(invoke, "lifecycles")
    assert (code, out[:3]) == (
        0,
        [
            "Lifecycle  Initial    States                        Transitions",
            "adr        Proposed   Proposed, Accepted,           Proposed → Accepted,",
            "                      Rejected, Superseded,         Proposed → Rejected,",
        ],
    )


@pytest.mark.covers("workflow lifecycles", "--json")
@pytest.mark.bundled_only("prints the bundled vocabulary")
async def test_lifecycles_json_prints_one_object_per_lifecycle(project, invoke) -> None:
    output = await printed(invoke, ["workflow", "lifecycles", "--json"])
    assert output == json_text(documents.LIFECYCLES)


@pytest.mark.covers("workflow collections")
@pytest.mark.bundled_only("lists the bundled vocabulary")
async def test_collections_lists_every_declared_badge_collection(project, invoke) -> None:
    code, out = await _run(invoke, "collections")
    assert (code, out[:2]) == (
        0,
        [
            "Collection  Label     Ordered  Default  Badges",
            "priority    Priority  yes               🔴 urgent, 🟠 high, 🟡 medium, 🟢 low",
        ],
    )


@pytest.mark.covers("workflow collections", "--json")
@pytest.mark.bundled_only("prints the bundled vocabulary")
async def test_collections_json_prints_one_object_per_collection(project, invoke) -> None:
    output = await printed(invoke, ["workflow", "collections", "--json"])
    assert output == json_text(documents.COLLECTIONS)


@pytest.mark.covers("workflow statuses")
async def test_statuses_lists_every_declared_status_with_its_role(project, invoke) -> None:
    code, out = await _run(invoke, "statuses")
    assert (code, out[:3], out[-1]) == (
        0,
        [
            "Status            Role        Badge",
            "Accepted          in_force",
            "Active            active",
        ],
        "WontFix           retired     ⚫",
    )


@pytest.mark.covers("workflow statuses", "--json")
async def test_statuses_json_prints_one_object_per_status(project, invoke) -> None:
    output = await printed(invoke, ["workflow", "statuses", "--json"])
    assert output == json_text(documents.STATUSES)


@pytest.mark.covers("workflow roles")
async def test_roles_lists_every_status_role(project, invoke) -> None:
    assert await _run(invoke, "roles") == (
        0,
        [
            "Role        Settled  Hidden  Color     Live  Blocked  Deferred",
            "active                       positive  yes",
            "attention                    danger",
            "blocked                      danger          yes",
            "deferred    yes      yes     info                     yes",
            "done        yes      yes     positive",
            "in_force    yes              info",
            "pending                      neutral",
            "retired     yes      yes     muted",
            "superseded  yes      yes     muted",
        ],
    )


@pytest.mark.covers("workflow roles", "--json")
async def test_roles_json_prints_one_object_per_status_role(project, invoke) -> None:
    output = await printed(invoke, ["workflow", "roles", "--json"])
    assert output == json_text(documents.ROLES)


@pytest.mark.covers("workflow ref-kinds")
@pytest.mark.bundled_only("prints the bundled vocabulary")
async def test_ref_kinds_lists_every_declared_ref_kind(project, invoke) -> None:
    code, out = await _run(invoke, "ref-kinds")
    assert (code, out[:2]) == (
        0,
        [
            "Kind        Label       Hint                             Role          Direction",
            "addresses   Addresses   A (the resolving work)",
        ],
    )


@pytest.mark.covers("workflow ref-kinds", "--json")
@pytest.mark.bundled_only("prints the bundled vocabulary")
async def test_ref_kinds_json_prints_one_object_per_ref_kind(project, invoke) -> None:
    output = await printed(invoke, ["workflow", "ref-kinds", "--json"])
    assert output == json_text(documents.REF_KINDS)


@pytest.mark.covers("workflow views")
@pytest.mark.bundled_only("lists the bundled vocabulary")
async def test_views_lists_every_declared_view(project, invoke) -> None:
    assert await _run(invoke, "views") == (
        0,
        [
            "View              Source kind  Source name",
            "greeting_skill    self",
            "item_skill        playbook",
            "memory_skill      self",
            "milestone_rollup  ref          targets",
            "role_definition   role",
            "squads_skill      playbook",
        ],
    )


@pytest.mark.covers("workflow views", "--json")
@pytest.mark.bundled_only("prints the bundled vocabulary")
async def test_views_json_prints_one_object_per_view(project, invoke) -> None:
    output = await printed(invoke, ["workflow", "views", "--json"])
    assert output == json_text(documents.VIEWS)


# --- view -----------------------------------------------------------------------------------


@pytest.mark.covers("workflow view", "name")
@pytest.mark.covers("workflow view", "ID")
async def test_view_resolves_a_declared_view_against_the_item(milestone_project, invoke) -> None:
    expected = (
        0,
        [
            "## Delivered (1)",
            "",
            "- **TASK-3** (task) Done — Parse queries — manager",
            "",
            "## Outstanding (1)",
            "",
            "- **TASK-4** (task) Draft — Rank results",
            "",
            "## Settled without delivering (0)",
            "",
            "_(none)_",
            "",
        ],
    )
    assert await _run(invoke, "view", "milestone_rollup", "8") == expected
    assert await _run(invoke, "view", "milestone_rollup", "MILE-8") == expected


@pytest.mark.covers("workflow view", "name")
async def test_view_refuses_a_name_no_view_declares(milestone_project, invoke) -> None:
    assert await _run(invoke, "view", "ghost", "8") == (
        1,
        ["error: no declared view 'ghost'; see `sq workflow views` for the declared set"],
    )


@pytest.mark.covers("workflow view", "ID")
async def test_view_refuses_an_item_the_index_lacks(milestone_project, invoke) -> None:
    assert await _run(invoke, "view", "milestone_rollup", "99") == (
        1,
        ["error: no item with number 99 (use a full ID like TYPE-99 or bare 99)"],
    )


@pytest.mark.covers("workflow view", "ID")
@pytest.mark.parametrize("view", ["milestone_rollup", "memory_skill"])
async def test_view_refuses_an_id_whose_prefix_is_not_its_owners(
    milestone_project, invoke, view: str
) -> None:
    assert await _run(invoke, "view", view, "TASK-8") == (
        1,
        ["error: TASK-8 is MILE-8 (milestone)"],
    )


@pytest.mark.covers("workflow view", "--json")
async def test_view_json_prints_the_records_the_view_resolves(milestone_project, invoke) -> None:
    result = await invoke(["workflow", "view", "milestone_rollup", "8", "--json"])
    assert result.exit_code == 0, result.output
    expected = [
        {
            "id": "TASK-3",
            "type": "task",
            "title": "Parse queries",
            "status": "Done",
            "assignee": "manager",
            "blocked": False,
            "badges": {"priority": "urgent"},
            "anchor": False,
            "children": [],
            "display": {
                "type": "Task",
                "status": {"badge": "🟢 Done", "intent": "positive"},
                "badges": {
                    "priority": {
                        "label": "Priority",
                        "badge": "🔴 urgent",
                        "badge_label": "🔴 Urgent",
                    }
                },
                "assignee": "Catherine Manager",
                "dimmed": False,
                "anchor": None,
                "pronouns": None,
            },
            "notebook": None,
            "closed": True,
            "updated_at": "2026-06-07T10:00:00Z",
        },
        {
            "id": "TASK-4",
            "type": "task",
            "title": "Rank results",
            "status": "Draft",
            "assignee": None,
            "blocked": False,
            "badges": {"priority": "low"},
            "anchor": False,
            "children": [],
            "display": {
                "type": "Task",
                "status": {"badge": "⚪ Draft", "intent": "neutral"},
                "badges": {
                    "priority": {"label": "Priority", "badge": "🟢 low", "badge_label": "🟢 Low"}
                },
                "assignee": None,
                "dimmed": False,
                "anchor": None,
                "pronouns": None,
            },
            "notebook": None,
            "closed": False,
            "updated_at": "2026-06-07T10:00:00Z",
        },
    ]
    # Compared as text, so the key order is held as well as the content.
    assert result.output == json.dumps(expected, indent=2) + "\n"


# --- lint -----------------------------------------------------------------------------------


@pytest.mark.covers("workflow lint")
@pytest.mark.bundled_only("prints the bundled vocabulary")
async def test_lint_accepts_a_squad_with_no_override(project, invoke) -> None:
    assert await _run(invoke, "lint") == (
        0,
        ["workflow spec OK — no override file found; using the bundled default."],
    )


# --- json documents -------------------------------------------------------------------------


@pytest.mark.covers("workflow show", "--json")
@pytest.mark.bundled_only("prints the bundled vocabulary")
async def test_show_json_prints_the_cheatsheet_as_markdown(project, invoke) -> None:
    raw = await invoke(["workflow", "show", "--raw"])
    result = await invoke(["workflow", "show", "--json"])
    assert result.exit_code == 0, result.output
    markdown = raw.output.removesuffix("\n")
    assert markdown.splitlines()[:4] == CHEATSHEET_HEAD
    assert result.output == json.dumps({"markdown": markdown}, indent=2) + "\n"


@pytest.mark.covers("workflow lint", "--json")
@pytest.mark.bundled_only("prints the bundled vocabulary")
async def test_lint_json_prints_each_error_with_its_location_and_fix(project, invoke) -> None:
    (project.squad_dir / ".overrides").mkdir()
    (project.squad_dir / ".overrides" / "workflow.toml").write_text(
        "[statuses.Parked]\nrole = 'nowhere'\n", encoding="utf-8"
    )
    result = await invoke(["workflow", "lint", "--json"])
    assert result.exit_code == 1
    assert (
        result.output
        == json.dumps(
            {
                "override": True,
                "errors": [
                    {
                        "location": ".overrides/workflow.toml",
                        "message": "status 'Parked': role 'nowhere' not declared in roles",
                        "fix_hint": "Fix the referenced key in .overrides/workflow.toml, or add it "
                        "back (directly or via `selected`), and re-run `sq workflow lint`.",
                    }
                ],
                "warnings": [],
            },
            indent=2,
        )
        + "\n"
    )


async def _lint_messages(project, invoke, override: str) -> list[str]:
    """The messages `workflow lint --json` prints for a workflow override of *override*."""
    folder = project.squad_dir / ".overrides"
    folder.mkdir()
    (folder / "workflow.toml").write_text(
        f"# squads:override-base:0.19.0\n{override}", encoding="utf-8"
    )
    result = await invoke(["workflow", "lint", "--json"])
    assert result.exit_code == 1, result.output
    return [e["message"] for e in json.loads(result.output)["errors"]]


@pytest.mark.covers("workflow lint", "--json")
@pytest.mark.bundled_only("prints the bundled vocabulary")
async def test_lint_refuses_an_item_field_code_equal_to_a_core_key(project, invoke) -> None:
    assert await _lint_messages(
        project,
        invoke,
        '[items.task]\nfields = [{ code = "status", label = "S", collection = "priority" }]\n',
    ) == [
        "'task': field code 'status' shadows a reserved frontmatter key — rename the field in "
        "the workflow override"
    ]


@pytest.mark.covers("workflow lint", "--json")
@pytest.mark.bundled_only("prints the bundled vocabulary")
async def test_lint_refuses_a_kind_field_code_a_sub_entity_object_adds(project, invoke) -> None:
    assert await _lint_messages(
        project,
        invoke,
        '[subentity_kinds.finding]\nfields = [{ code = "badges", label = "B", '
        'collection = "severity" }]\n',
    ) == [
        "'finding': field code 'badges' shadows a reserved key every --json sub-entity object "
        "adds — rename the field in the workflow override"
    ]


@pytest.mark.covers("workflow lint", "--json")
@pytest.mark.bundled_only("prints the bundled vocabulary")
async def test_lint_refuses_a_field_code_equal_to_an_option_of_the_command_it_derives_onto(
    project, invoke
) -> None:
    messages = await _lint_messages(
        project,
        invoke,
        '[items.task]\nfields = [{ code = "force", label = "F", collection = "priority" },'
        ' { code = "sort", label = "S", collection = "priority" }]\n',
    )
    assert messages == [
        "task update: field 'force' gives --force, which task update already takes — rename it "
        "in the workflow override",
        "list: field 'sort' gives --sort, which list already takes — rename it in the workflow "
        "override",
        "tree: field 'sort' gives --sort, which tree already takes — rename it in the workflow "
        "override",
    ]


@pytest.mark.covers("workflow lint", "--json")
@pytest.mark.bundled_only("prints the bundled vocabulary")
async def test_lint_refuses_a_field_whose_import_key_equals_a_fixed_key_of_its_op(
    project, invoke
) -> None:
    messages = await _lint_messages(
        project,
        invoke,
        '[subentity_kinds.finding]\nfields = [{ code = "handle", label = "H",'
        ' collection = "severity" }]\n',
    )
    assert messages == [
        "import op add-finding: field 'handle' gives handle, which import op add-finding "
        "already takes — rename it in the workflow override"
    ]


@pytest.mark.covers("workflow lint", "--json")
@pytest.mark.bundled_only("prints the bundled vocabulary")
async def test_lint_refuses_two_fields_that_give_one_flag(project, invoke) -> None:
    messages = await _lint_messages(
        project,
        invoke,
        '[items.task]\nfields = [{ code = "x", label = "X", collection = "priority" },'
        ' { code = "no_x", label = "N", collection = "priority" }]\n',
    )
    assert messages == [
        "task update: field 'no_x' and field 'x' both give --no-x — rename one in the workflow "
        "override"
    ]


@pytest.mark.covers("workflow lint", "--json")
@pytest.mark.bundled_only("prints the bundled vocabulary")
async def test_lint_refuses_a_target_kind_equal_to_an_option_of_the_command_it_derives_onto(
    project, invoke
) -> None:
    messages = await _lint_messages(
        project,
        invoke,
        '[items.feature]\nsubentity_kind = "status"\n'
        '[subentity_kinds.status]\nlifecycle = "subentity"\ncompletion = "Done"\n'
        'plural = "statuses"\nlocal_prefix = "SS"\nplaceholder = "_text_"\n',
    )
    assert messages == [
        "add-subtask: target kind 'status' gives --status, which add-subtask already takes — "
        "rename it in the workflow override",
        "subtask update: target kind 'status' gives --status, which subtask update already takes "
        "— rename it in the workflow override",
        "import op add-subtask: target kind 'status' gives status, which import op add-subtask "
        "already takes — rename it in the workflow override",
    ]


@pytest.mark.covers("workflow lint", "--json")
@pytest.mark.bundled_only("prints the bundled vocabulary")
async def test_lint_refuses_a_kind_named_like_a_key_of_the_comment_op(project, invoke) -> None:
    messages = await _lint_messages(
        project,
        invoke,
        '[subentity_kinds.target]\nlifecycle = "subentity"\ncompletion = "Done"\n'
        'plural = "targets"\nlocal_prefix = "TG"\nplaceholder = "_text_"\n',
    )
    assert messages == [
        "import op comment: kind 'target' gives target, which import op comment already takes "
        "— rename it in the workflow override"
    ]


@pytest.mark.covers("workflow lint", "--json")
@pytest.mark.bundled_only("prints the bundled vocabulary")
async def test_lint_refuses_a_kind_named_like_the_generic_selector(project, invoke) -> None:
    messages = await _lint_messages(
        project,
        invoke,
        '[subentity_kinds.sub]\nlifecycle = "subentity"\ncompletion = "Done"\n'
        'plural = "subs"\nlocal_prefix = "SB"\nplaceholder = "_text_"\n',
    )
    assert messages == [
        "subentity kind 'sub': the name is the generic sub-entity verb; rename the kind in the "
        "workflow override"
    ]


@pytest.mark.covers("workflow lint", "--json")
async def test_lint_json_refuses_outside_a_squad_on_stderr(invoke) -> None:
    result = await invoke(["workflow", "lint", "--json"])
    assert (result.exit_code, result.stdout) == (1, "")
    assert result.stderr == (
        "error: no .squads.toml found in this or any parent directory — run `sq init`\n"
    )


#: The `role_definition` view's source on the seeded squad: the `manager` role, its own tag left
#: unexpanded in the body.
MANAGER_ROLE_SOURCE = {
    "slug": "manager",
    "id": "ROLE-1",
    "activated": True,
    "origin": "system",
    "full_name": "Catherine Manager",
    "pronouns": None,
    "title": "manager",
    "mission": "Be the operator's first point of contact and run the work loop: understand the "
    "intent, delegate to the right specialists, integrate what they return, and drive "
    "each feature to done — keeping everything tracked in squads.",
    "model": "opus",
    "is_default": True,
    "can_spawn": True,
    "capabilities": [],
    "create_lane": [],
    "responsibilities": [
        "Triage incoming requests and clarify intent",
        "Delegate work to the right specialist agents and integrate their results",
        "Drive features through the loop (implement → review → fix) until done",
        "Keep the backlog and statuses honest",
        "Summarise progress for the operator",
    ],
    "skills": ["squads", "greeting", "sq-memory"],
    "display": {
        "name": "Catherine Manager",
        "pronouns": None,
        "color": "cyan",
        "body": "<!-- sq:view:role_definition -->",
        "empty_hint": "(empty — run `sq sync`; if it stays empty, declare the definition in "
        "`.overrides/roles.toml`, or `.overrides/roles/<slug>.toml`, or run "
        "`sq role manager view add role_definition`)",
        "definition_resolves": True,
        "change_hint": "To change its mission or responsibilities: `sq override scaffold "
        "--role manager`, edit the file, then `sq sync`. To change its model: "
        "`sq role manager update --model …`.",
        "discussion": [],
    },
}
#: The `greeting_skill` view's source on the seeded squad: the `greeting` skill, its own tag left
#: unexpanded in the body.
GREETING_SKILL_SOURCE = {
    "sequence_id": 2,
    "type": "skill",
    "title": "greeting",
    "slug": "greeting",
    "status": "Active",
    "description": "Start of a conversation with a human: detect & register the operator, then "
    "greet them — match their tone, say how you help, and give a quick read of the project. "
    "Use when a person opens a session; skip it when spawned as a subagent for a job.",
    "parent": None,
    "author": "greeting",
    "assignee": None,
    "labels": [],
    "refs": [],
    "subentities": [],
    "path": "agents/skills/SKILL-000002-greeting.md",
    "created_at": "2026-06-07T10:00:00Z",
    "updated_at": "2026-06-07T10:00:00Z",
    "created_session": None,
    "modified_session": None,
    "id": "SKILL-2",
    "origin": "system",
    "body": "<!-- sq:view:greeting_skill -->",
    "views": {},
    "discussion": [],
    "badges": {},
    "spec": {
        "schema_version": "0.19",
        "override": False,
        "digest": "e194337afd5234e8a7376fdb05c2c54868a65f4d6803e980b572093ac0e8646b",
    },
    "display": {
        "type": "Skill",
        "status": {"badge": "⚪ Active", "intent": "positive"},
        "badges": {},
        "assignee": None,
        "body": "<!-- sq:view:greeting_skill -->",
        "summary": None,
        "attributes": [],
    },
}


@pytest.mark.covers("workflow view", "--json")
@pytest.mark.bundled_only("prints the bundled vocabulary")
async def test_view_json_leaves_the_views_own_tag_unexpanded_in_its_source(
    seeded_project, invoke
) -> None:
    role = await printed(invoke, ["workflow", "view", "role_definition", "ROLE-1", "--json"])
    assert role == json_text(MANAGER_ROLE_SOURCE)
    skill = await printed(invoke, ["workflow", "view", "greeting_skill", "SKILL-2", "--json"])
    assert skill == json_text(GREETING_SKILL_SOURCE)


# --- the override squad and the grammar an override spells ------------------------------------


def _write_override(project, text: str) -> None:
    overrides = project.squad_dir / ".overrides"
    overrides.mkdir(exist_ok=True)
    (overrides / "workflow.toml").write_text(text, encoding="utf-8")


async def _lint_errors(invoke) -> str:
    """The messages `sq workflow lint` refuses the override with, as one string."""
    result = await invoke(["workflow", "lint", "--json"])
    assert result.exit_code == 1, result.output
    return "\n".join(e["message"] for e in json.loads(result.output)["errors"])


@pytest.mark.covers("check")
@pytest.mark.covers("workflow types", "--json")
@pytest.mark.covers("workflow subentity-kinds", "--json")
async def test_the_override_squad_checks_clean_and_lists_only_its_own_vocabulary(
    override_project, invoke
) -> None:
    checked = await invoke(["check"])
    assert (checked.exit_code, checked.output) == (0, "✓ no issues\n")
    types = await read_json(invoke, ["workflow", "types", "--json"])
    kinds = await read_json(invoke, ["workflow", "subentity-kinds", "--json"])
    assert sorted(t["type"] for t in types) == [
        "initiative",
        "job",
        "operator",
        "record",
        "role",
        "skill",
    ]
    assert sorted(k["subentity_kind"] for k in kinds) == ["action", "outcome"]
    assert {k["subentity_kind"]: k["label"] for k in kinds} == {
        "action": "Action",
        "outcome": "Desired outcome",
    }


@pytest.mark.covers("workflow lint", "--json")
@pytest.mark.parametrize(
    ("override", "refusal"),
    [
        (
            "[subentity_kinds.subtask]\nmaps_parent_story = true\n",
            "'maps_parent_story' was renamed 'maps_to_parent'",
        ),
        (
            "[items.task]\nvalidators = ['subtask_story_mapping@warn']\n",
            "'subtask_story_mapping@warn' was renamed 'subentity_mapping'",
        ),
        (
            "[views.milestone_rollup]\n"
            "transform = { module = 'squads._view_transforms', function = 'milestone_rollup' }\n",
            "'milestone_rollup' was renamed 'status_rollup'",
        ),
    ],
)
async def test_an_override_spelling_a_renamed_grammar_name_is_refused_naming_the_new_one(
    project, invoke, override: str, refusal: str
) -> None:
    _write_override(project, override)
    assert refusal in await _lint_errors(invoke)


@pytest.mark.covers("workflow lint", "--json")
@pytest.mark.parametrize(
    ("override", "cause", "remedy"),
    [
        (
            "[items.bug]\nsubentity_kind = 'subtask'\n",
            "'bug' has no parent_required",
            "declare parent_required on 'bug'",
        ),
        (
            "[items.bug]\nsubentity_kind = 'subtask'\nparent_required = 'epic'\n",
            "its parent_required type 'epic' hosts no sub-entity kind",
            "declare subentity_kind on 'epic'",
        ),
    ],
)
async def test_a_mapping_kind_without_a_target_is_refused_naming_both_remedies(
    project, invoke, override: str, cause: str, remedy: str
) -> None:
    _write_override(project, override)
    refusal = await _lint_errors(invoke)
    assert cause in refusal
    assert remedy in refusal
    assert "drop maps_to_parent on 'subtask'" in refusal


@pytest.mark.covers("workflow subentity-kinds", "--json")
async def test_a_container_heading_is_the_declared_text_or_the_title_cased_plural(
    override_project, invoke
) -> None:
    kinds = await read_json(invoke, ["workflow", "subentity-kinds", "--json"])
    assert {k["subentity_kind"]: k["container_heading"] for k in kinds} == {
        "outcome": "Desired Outcomes",
        "action": "Actions",
    }
    initiative = next((override_project.squad_dir / "initiatives").glob("INI-*.md"))
    job = next((override_project.squad_dir / "jobs").glob("JOB-*.md"))
    assert "\n## Desired Outcomes\n" in initiative.read_text(encoding="utf-8")
    assert "\n## Actions\n" in job.read_text(encoding="utf-8")
