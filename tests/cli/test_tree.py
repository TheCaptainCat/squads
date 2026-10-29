"""`sq tree`: the root argument, each filter alone, the sort, the depth and the JSON form, plus the
interactions between the priority options, between the badge options and between sort and JSON."""

import json
from typing import Any

import pytest

from tests.cli._output import json_text
from tests.cli._readable import init_readable, lines

pytestmark = pytest.mark.anyio

FEATURE = "FEAT-2 🟠 high · Search (Draft)"
PARSER = "TASK-3 🔴 urgent · Parse queries (InProgress)"
RANKING = "TASK-4 🟢 low · Rank results (Draft)"
ROLE = "ROLE-1 Catherine Manager (Active)"
DECISION = "ADR-5 Pick an index (Proposed)"
BUG = "BUG-6 🟡 medium · Empty query crash (Verified)"
REVIEW = "REV-7 Review the parser (Requested)"


@pytest.fixture
def readable(copy_squad):
    return copy_squad("readable", init_readable)


async def _tree(invoke, *args: str) -> tuple[int, list[str]]:
    result = await invoke(["tree", *args])
    return result.exit_code, lines(result.output)


async def _roots(invoke, *args: str) -> list[str]:
    result = await invoke(["tree", "--json", *args])
    assert result.exit_code == 0, result.output
    return [node["id"] for node in json.loads(result.output)]


def _drawn(*rows: str) -> list[str]:
    """The tree text for *rows*, which are already prefixed with their branch drawing."""
    return ["squad", *rows]


@pytest.mark.covers("tree")
async def test_tree_draws_the_open_items_under_their_parents(readable, invoke) -> None:
    assert await _tree(invoke) == (
        0,
        _drawn(
            f"├── {ROLE}",
            f"├── {FEATURE}",
            f"│   ├── {PARSER}",
            f"│   └── {RANKING}",
            f"├── {DECISION}",
            f"└── {REVIEW}",
        ),
    )


@pytest.mark.covers("tree", "ROOT_ID")
async def test_root_id_draws_one_item_and_what_is_below_it(readable, invoke) -> None:
    assert await _tree(invoke, "2") == (
        0,
        _drawn(f"└── {FEATURE}", f"    ├── {PARSER}", f"    └── {RANKING}"),
    )
    assert await _tree(invoke, "TASK-3") == (0, _drawn(f"└── {PARSER}"))


@pytest.mark.covers("tree", "ROOT_ID")
async def test_root_id_refuses_a_number_no_item_has(readable, invoke) -> None:
    assert await _tree(invoke, "99") == (
        1,
        ["error: no item with number 99 (use a full ID like TYPE-99 or bare 99)"],
    )


@pytest.mark.covers("tree", "--type")
async def test_type_keeps_one_type_in_context(readable, invoke) -> None:
    assert await _tree(invoke, "--type", "task") == (
        0,
        _drawn(f"└── {FEATURE}", f"    ├── {PARSER}", f"    └── {RANKING}"),
    )


@pytest.mark.covers("tree", "--type")
async def test_type_refuses_an_unknown_type(readable, invoke) -> None:
    assert await _tree(invoke, "--type", "ghost") == (
        1,
        [
            "error: unknown type 'ghost' (one of: bug, contract, decision, epic, feature, "
            "guide, milestone, operator, review, role, skill, task)"
        ],
    )


@pytest.mark.covers("tree", "--status")
async def test_status_keeps_one_status_even_when_it_is_closed(readable, invoke) -> None:
    assert await _tree(invoke, "--status", "Verified") == (0, _drawn(f"└── {BUG}"))


@pytest.mark.covers("tree", "--status")
async def test_a_node_leads_with_its_first_badge_field_when_a_second_is_set(
    readable, invoke
) -> None:
    updated = await invoke(["bug", "6", "update", "--set", "severity=high"])
    assert updated.exit_code == 0, updated.output
    assert await _tree(invoke, "--status", "Verified") == (0, _drawn(f"└── {BUG}"))


@pytest.mark.covers("tree", "--status")
async def test_status_refuses_an_unknown_status(readable, invoke) -> None:
    code, out = await _tree(invoke, "--status", "Ghost")
    assert (code, out[0][:34]) == (1, "error: unknown status 'Ghost' (one")


@pytest.mark.covers("tree", "--assignee")
async def test_assignee_keeps_the_items_assigned_to_the_slug_in_context(readable, invoke) -> None:
    assert await _tree(invoke, "--assignee", "manager") == (
        0,
        _drawn(f"└── {FEATURE}", f"    └── {PARSER}"),
    )


@pytest.mark.covers("tree", "--assignee")
async def test_assignee_refuses_a_slug_no_roster_entry_has(readable, invoke) -> None:
    assert await _tree(invoke, "--assignee", "ghost") == (
        1,
        ["error: unknown slug 'ghost'; valid slugs: manager"],
    )


@pytest.mark.covers("tree", "--label")
async def test_label_keeps_the_items_carrying_it(readable, invoke) -> None:
    assert await _tree(invoke, "--label", "core") == (0, _drawn(f"└── {FEATURE}"))


@pytest.mark.covers("tree", "--category")
async def test_category_keeps_one_category(readable, invoke) -> None:
    assert await _tree(invoke, "--category", "roster") == (0, _drawn(f"└── {ROLE}"))


@pytest.mark.covers("tree", "--category")
async def test_category_refuses_an_unknown_category(readable, invoke) -> None:
    assert await _tree(invoke, "--category", "ghost") == (
        1,
        ["error: unknown category 'ghost' (one of: roster, work, records)"],
    )


@pytest.mark.covers("tree", "--priority")
async def test_priority_keeps_the_items_of_exactly_that_priority_in_context(
    readable, invoke
) -> None:
    assert await _tree(invoke, "--priority", "low") == (
        0,
        _drawn(f"└── {FEATURE}", f"    └── {RANKING}"),
    )


@pytest.mark.covers("tree", "--priority")
async def test_priority_refuses_an_unknown_code(readable, invoke) -> None:
    assert await _tree(invoke, "--priority", "ghost") == (
        1,
        ["error: unknown priority 'ghost' (one of: urgent, high, medium, low)"],
    )


@pytest.mark.covers("tree", "--min-priority")
async def test_min_priority_keeps_the_items_at_least_that_urgent_in_context(
    readable, invoke
) -> None:
    assert await _tree(invoke, "--min-priority", "urgent") == (
        0,
        _drawn(f"└── {FEATURE}", f"    └── {PARSER}"),
    )


@pytest.mark.covers("tree", "--min-priority")
async def test_min_priority_refuses_an_unknown_code(readable, invoke) -> None:
    assert await _tree(invoke, "--min-priority", "ghost") == (
        1,
        ["error: unknown priority 'ghost' (one of: urgent, high, medium, low)"],
    )


@pytest.mark.covers("tree", "--badge")
async def test_badge_keeps_the_items_whose_field_has_the_value_in_context(readable, invoke) -> None:
    assert await _tree(invoke, "--badge", "priority=low") == (
        0,
        _drawn(f"└── {FEATURE}", f"    └── {RANKING}"),
    )


@pytest.mark.covers("tree", "--badge")
async def test_badge_refuses_a_pair_without_a_value(readable, invoke) -> None:
    assert await _tree(invoke, "--badge", "priority") == (
        1,
        ["error: expected CODE=VALUE, got 'priority'"],
    )


@pytest.mark.covers("tree", "--min-badge")
async def test_min_badge_keeps_the_items_at_least_that_rank_in_context(readable, invoke) -> None:
    assert await _tree(invoke, "--min-badge", "priority=urgent") == (
        0,
        _drawn(f"└── {FEATURE}", f"    └── {PARSER}"),
    )


@pytest.mark.covers("tree", "--min-badge")
async def test_min_badge_refuses_a_pair_without_a_value(readable, invoke) -> None:
    assert await _tree(invoke, "--min-badge", "priority") == (
        1,
        ["error: expected CODE=VALUE, got 'priority'"],
    )


@pytest.mark.covers("tree", "--sort")
async def test_sort_orders_each_level_by_the_rank_of_the_badge_field(readable, invoke) -> None:
    assert await _tree(invoke, "--sort", "priority") == (
        0,
        _drawn(
            f"├── {FEATURE}",
            f"│   ├── {PARSER}",
            f"│   └── {RANKING}",
            f"├── {ROLE}",
            f"├── {DECISION}",
            f"└── {REVIEW}",
        ),
    )


@pytest.mark.covers("tree", "--depth")
async def test_depth_cuts_the_levels_below_the_root(readable, invoke) -> None:
    assert await _tree(invoke, "--depth", "0") == (
        0,
        _drawn(f"├── {ROLE}", f"├── {FEATURE}", f"├── {DECISION}", f"└── {REVIEW}"),
    )
    assert await _tree(invoke, "2", "--depth", "0") == (0, _drawn(f"└── {FEATURE}"))


@pytest.mark.covers("tree", "--depth")
async def test_depth_refuses_a_value_that_is_not_an_integer(readable, invoke) -> None:
    assert await _tree(invoke, "--depth", "deep") == (
        2,
        [
            "Usage: sq tree [OPTIONS] [ROOT_ID]",
            "Try 'sq tree --help' for help.",
            "╭─ Error ──────────────────────────────────────────────────────────────────────╮",
            "│ Invalid value for '--depth': 'deep' is not a valid integer.                  │",
            "╰──────────────────────────────────────────────────────────────────────────────╯",
        ],
    )


@pytest.mark.covers("tree", "--all")
async def test_all_includes_the_closed_items(readable, invoke) -> None:
    assert await _tree(invoke, "--all") == (
        0,
        _drawn(
            f"├── {ROLE}",
            f"├── {FEATURE}",
            f"│   ├── {PARSER}",
            f"│   └── {RANKING}",
            f"├── {DECISION}",
            f"├── {BUG}",
            f"└── {REVIEW}",
        ),
    )


@pytest.mark.covers("tree", "--type")
async def test_a_filter_that_matches_only_closed_items_prints_a_hint(readable, invoke) -> None:
    assert await _tree(invoke, "--type", "bug") == (0, ["1 closed items hidden — use --all"])


@pytest.mark.covers("tree", "--json")
async def test_json_prints_the_root_nodes_with_their_children(readable, invoke) -> None:
    result = await invoke(["tree", "2", "--json", "--depth", "1"])
    expected = [
        {
            "id": "FEAT-2",
            "type": "feature",
            "title": "Search",
            "status": "Draft",
            "priority": "high",
            "assignee": "manager",
            "blocked": False,
            "badges": {"priority": "high"},
            "anchor": False,
            "children": [
                {
                    "id": "TASK-3",
                    "type": "task",
                    "title": "Parse queries",
                    "status": "InProgress",
                    "priority": "urgent",
                    "assignee": "manager",
                    "blocked": False,
                    "badges": {"priority": "urgent"},
                    "anchor": False,
                    "children": [],
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
                        "dimmed": False,
                        "anchor": None,
                        "pronouns": None,
                    },
                    "notebook": None,
                    "closed": False,
                    "updated_at": "2026-06-07T10:00:00Z",
                },
                {
                    "id": "TASK-4",
                    "type": "task",
                    "title": "Rank results",
                    "status": "Draft",
                    "priority": "low",
                    "assignee": None,
                    "blocked": True,
                    "badges": {"priority": "low"},
                    "anchor": False,
                    "children": [],
                    "display": {
                        "type": "Task",
                        "status": {"badge": "⚪ Draft", "intent": "neutral"},
                        "badges": {
                            "priority": {
                                "label": "Priority",
                                "badge": "🟢 low",
                                "badge_label": "🟢 Low",
                            }
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
            ],
            "display": {
                "type": "Feature",
                "status": {"badge": "⚪ Draft", "intent": "neutral"},
                "badges": {
                    "priority": {"label": "Priority", "badge": "🟠 high", "badge_label": "🟠 High"}
                },
                "assignee": "Catherine Manager",
                "dimmed": False,
                "anchor": None,
                "pronouns": None,
            },
            "notebook": None,
            "closed": False,
            "updated_at": "2026-06-07T10:00:00Z",
        }
    ]
    # Compared as text, so the key order is held as well as the content.
    assert (result.exit_code, result.output) == (0, json_text(expected))


async def _give_the_manager_pronouns(invoke) -> None:
    updated = await invoke(["role", "manager", "update", "--pronouns", "she/her"])
    assert updated.exit_code == 0, updated.output


@pytest.mark.covers("tree", "--json")
async def test_json_shows_a_roles_pronouns_on_its_node(readable, invoke) -> None:
    await _give_the_manager_pronouns(invoke)
    shown = await invoke(["tree", "--json", "--category", "roster"])
    assert (shown.exit_code, shown.output) == (0, json_text([_role_node("she/her")]))


@pytest.mark.covers("tree", "--json")
async def test_json_leaves_the_pronouns_out_when_the_display_setting_turns_them_off(
    readable, invoke
) -> None:
    await _give_the_manager_pronouns(invoke)
    # No command writes `[display]`, so the setting is arranged in the configuration file.
    config = readable.config_path.read_text(encoding="utf-8")
    readable.config_path.write_text(config + "\n[display]\npronouns = false\n", encoding="utf-8")
    hidden = await invoke(["tree", "--json", "--category", "roster"])
    assert (hidden.exit_code, hidden.output) == (0, json_text([_role_node(None)]))


@pytest.mark.covers("tree", "--json")
async def test_json_gives_a_skill_sharing_a_roles_slug_neither_its_notebook_nor_its_pronouns(
    readable, invoke
) -> None:
    await _give_the_manager_pronouns(invoke)
    added = await invoke(["skill", "add", "Manager"])
    assert added.exit_code == 0, added.output
    shown = await invoke(["tree", "--json", "--category", "roster"])
    skill = {"id": "SKILL-8", "type": "skill", "title": "Manager", "status": "Active"}
    skill_node = {
        **skill,
        "priority": None,
        "assignee": None,
        "blocked": False,
        "badges": {},
        "anchor": False,
        "children": [],
        "display": {
            "type": "Skill",
            "status": {"badge": "⚪ Active", "intent": "positive"},
            "badges": {},
            "assignee": None,
            "dimmed": False,
            "anchor": None,
            "pronouns": None,
        },
        "notebook": None,
        "closed": False,
        "updated_at": "2026-06-07T10:00:00Z",
    }
    assert (shown.exit_code, shown.output) == (0, json_text([_role_node("she/her"), skill_node]))


def _role_node(pronouns: str | None) -> dict[str, Any]:
    """The `manager` role's root node, showing *pronouns*."""
    return {
        "id": "ROLE-1",
        "type": "role",
        "title": "Catherine Manager",
        "status": "Active",
        "priority": None,
        "assignee": None,
        "blocked": False,
        "badges": {},
        "anchor": False,
        "children": [],
        "display": {
            "type": "Role",
            "status": {"badge": "⚪ Active", "intent": "positive"},
            "badges": {},
            "assignee": None,
            "dimmed": False,
            "anchor": None,
            "pronouns": pronouns,
        },
        "notebook": "manager",
        "closed": False,
        "updated_at": "2026-06-07T10:00:00Z",
    }


# --- interactions ---------------------------------------------------------------------------


@pytest.mark.covers("tree", "--priority", "--min-priority")
async def test_priority_and_min_priority_both_apply_to_one_tree(readable, invoke) -> None:
    both = await _tree(invoke, "--priority", "urgent", "--min-priority", "high")
    assert both == (0, _drawn(f"└── {FEATURE}", f"    └── {PARSER}"))
    below = await _tree(invoke, "--priority", "low", "--min-priority", "high")
    assert below == (0, ["no items"])


@pytest.mark.covers("tree", "--badge", "--min-badge")
async def test_badge_and_min_badge_both_apply_to_one_tree(readable, invoke) -> None:
    both = await _tree(invoke, "--badge", "priority=urgent", "--min-badge", "priority=high")
    assert both == (0, _drawn(f"└── {FEATURE}", f"    └── {PARSER}"))
    below = await _tree(invoke, "--badge", "priority=low", "--min-badge", "priority=high")
    assert below == (0, ["no items"])


@pytest.mark.covers("tree", "--sort", "--json")
async def test_sort_decides_the_order_of_the_json_roots(readable, invoke) -> None:
    assert await _roots(invoke, "--sort", "priority") == ["FEAT-2", "ROLE-1", "ADR-5", "REV-7"]
    assert await _roots(invoke) == ["ROLE-1", "FEAT-2", "ADR-5", "REV-7"]
