"""`sq workflow`: the cheatsheet, each vocabulary listing in text and JSON, a declared view
resolved against an item, and the override lint."""

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from tests._helpers import create_item, make_service
from tests._squads import paths_of
from tests.cli._readable import init_readable, lines

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


async def _json(invoke, *args: str) -> list[dict[str, Any]]:
    result = await invoke(["workflow", *args, "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def _named(entries: list[dict[str, Any]], key: str) -> list[str]:
    return [entry[key] for entry in entries]


def _one(entries: list[dict[str, Any]], key: str, value: str) -> dict[str, Any]:
    return next(entry for entry in entries if entry[key] == value)


# --- the cheatsheet -------------------------------------------------------------------------


async def test_workflow_prints_the_rendered_cheatsheet(project, invoke) -> None:
    code, out = await _run(invoke)
    assert (code, out[:5]) == (0, RENDERED_HEAD)
    assert await _run(invoke, "show") == (code, out)


@pytest.mark.covers("workflow", "--raw")
async def test_the_group_raw_prints_the_cheatsheet_as_plain_markdown(project, invoke) -> None:
    code, out = await _run(invoke, "--raw")
    assert (code, out[:4]) == (0, CHEATSHEET_HEAD)


@pytest.mark.covers("workflow show", "--raw")
async def test_show_raw_prints_the_cheatsheet_as_plain_markdown(project, invoke) -> None:
    assert await _run(invoke, "show", "--raw") == await _run(invoke, "--raw")


# --- the vocabulary listings ----------------------------------------------------------------


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
async def test_types_json_prints_one_object_per_type(project, invoke) -> None:
    entries = await _json(invoke, "types")
    assert _named(entries, "type") == [
        "epic",
        "feature",
        "task",
        "bug",
        "decision",
        "contract",
        "milestone",
        "review",
        "guide",
        "role",
        "skill",
        "operator",
    ]
    assert _one(entries, "type", "task") == {
        "type": "task",
        "order": 30.0,
        "prefix": "TASK",
        "reserved": False,
        "category": "work",
        "subentity_kind": "subtask",
        "lifecycle": "work",
        "fields": [{"code": "priority", "label": "Priority", "collection": "priority"}],
        "attributes": {},
        "labels": {
            "singular": "Task",
            "plural": "Tasks",
            "singular_lower": "task",
            "plural_lower": "tasks",
        },
    }


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
async def test_subentity_kinds_json_prints_one_object_per_kind(project, invoke) -> None:
    entries = await _json(invoke, "subentity-kinds")
    assert _named(entries, "subentity_kind") == ["finding", "story", "subtask"]
    assert _one(entries, "subentity_kind", "finding") == {
        "subentity_kind": "finding",
        "lifecycle": "finding",
        "plural": "findings",
        "local_prefix": "F",
        "container_heading": "Findings",
        "completion": "Fixed",
        "maps_parent_story": False,
        "fields": [{"code": "severity", "label": "Severity", "collection": "severity"}],
    }


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
async def test_lifecycles_json_prints_one_object_per_lifecycle(project, invoke) -> None:
    entries = await _json(invoke, "lifecycles")
    assert _named(entries, "lifecycle") == [
        "adr",
        "agent",
        "bug",
        "contract",
        "finding",
        "guide",
        "milestone",
        "review",
        "subentity",
        "work",
    ]
    assert _one(entries, "lifecycle", "agent") == {
        "lifecycle": "agent",
        "initial": "Active",
        "states": ["Active", "Archived"],
        "transitions": [
            {"from": "Active", "to": "Archived"},
            {"from": "Archived", "to": "Active"},
        ],
    }


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
async def test_collections_json_prints_one_object_per_collection(project, invoke) -> None:
    entries = await _json(invoke, "collections")
    assert _named(entries, "collection") == ["priority", "severity"]
    assert _one(entries, "collection", "severity") == {
        "collection": "severity",
        "label": "Severity",
        "ordered": True,
        "default": "medium",
        "badges": [
            {"code": "critical", "label": "Critical", "emoji": "🔴"},
            {"code": "high", "label": "High", "emoji": "🟠"},
            {"code": "medium", "label": "Medium", "emoji": "🟡"},
            {"code": "low", "label": "Low", "emoji": "🟢"},
            {"code": "info", "label": "Info", "emoji": "🔵"},
        ],
    }


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
    entries = await _json(invoke, "statuses")
    assert len(entries) == 25
    assert _one(entries, "status", "Blocked") == {
        "status": "Blocked",
        "role": "blocked",
        "badge": "🔴",
    }


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
    entries = await _json(invoke, "roles")
    assert _named(entries, "role") == [
        "active",
        "attention",
        "blocked",
        "deferred",
        "done",
        "in_force",
        "pending",
        "retired",
        "superseded",
    ]
    assert _one(entries, "role", "blocked") == {
        "role": "blocked",
        "settled": False,
        "hidden": False,
        "color": "danger",
        "live": False,
        "blocked": True,
        "deferred": False,
    }


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
async def test_ref_kinds_json_prints_one_object_per_ref_kind(project, invoke) -> None:
    entries = await _json(invoke, "ref-kinds")
    assert _named(entries, "kind") == [
        "addresses",
        "blocks",
        "depends-on",
        "duplicates",
        "fixes",
        "implements",
        "related",
        "scopes",
        "supersedes",
        "targets",
    ]
    assert _one(entries, "kind", "blocks") == {
        "kind": "blocks",
        "label": "Blocks",
        "hint": "A is blocking B; B cannot proceed while A is open",
        "role": "dependency",
        "direction": "blocker",
    }


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
async def test_views_json_prints_one_object_per_view(project, invoke) -> None:
    entries = await _json(invoke, "views")
    assert _named(entries, "view") == [
        "greeting_skill",
        "item_skill",
        "memory_skill",
        "milestone_rollup",
        "role_definition",
        "squads_skill",
    ]
    assert _one(entries, "view", "milestone_rollup") == {
        "view": "milestone_rollup",
        "source_kind": "ref",
        "source_name": "targets",
        "transform": {"module": "squads._view_transforms", "function": "milestone_rollup"},
    }


# --- view -----------------------------------------------------------------------------------


@pytest.mark.covers("workflow view", "NAME")
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


async def test_view_refuses_a_name_no_view_declares(milestone_project, invoke) -> None:
    assert await _run(invoke, "view", "ghost", "8") == (
        1,
        ["error: no declared view 'ghost'; see `sq workflow views` for the declared set"],
    )


async def test_view_refuses_an_item_the_index_lacks(milestone_project, invoke) -> None:
    assert await _run(invoke, "view", "milestone_rollup", "99") == (
        1,
        ["error: no item '99' in the index"],
    )


@pytest.mark.covers("workflow view", "--json")
async def test_view_json_prints_the_records_the_view_resolves(milestone_project, invoke) -> None:
    result = await invoke(["workflow", "view", "milestone_rollup", "8", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == [
        {
            "id": "TASK-3",
            "type": "task",
            "title": "Parse queries",
            "status": "Done",
            "priority": "urgent",
            "assignee": "manager",
            "blocked": False,
            "badges": {"priority": "urgent"},
            "anchor": False,
            "children": [],
        },
        {
            "id": "TASK-4",
            "type": "task",
            "title": "Rank results",
            "status": "Draft",
            "priority": "low",
            "assignee": None,
            "blocked": False,
            "badges": {"priority": "low"},
            "anchor": False,
            "children": [],
        },
    ]


# --- lint -----------------------------------------------------------------------------------


@pytest.mark.covers("workflow lint")
async def test_lint_accepts_a_squad_with_no_override(project, invoke) -> None:
    assert await _run(invoke, "lint") == (
        0,
        ["workflow spec OK — no override file found; using the bundled default."],
    )
