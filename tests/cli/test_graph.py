"""`sq graph`: the tree of items linked by refs, its depth, kind, direction and closed-item
options and its dot, mermaid and JSON forms."""

import json

import pytest

from tests.cli._readable import init_readable, lines

pytestmark = pytest.mark.anyio

ROOT = "TASK-4 🟢 low · Draft"
PARSER = "TASK-3 🔴 urgent · InProgress"
REVIEW = "REV-7 Requested"
BUG = "BUG-6 🟡 medium · Verified"


@pytest.fixture
def readable(copy_squad):
    return copy_squad("readable", init_readable)


async def _graph(invoke, *args: str) -> tuple[int, list[str]]:
    result = await invoke(["graph", *args])
    return result.exit_code, lines(result.output)


@pytest.mark.covers("graph", "ID")
async def test_graph_draws_the_items_linked_to_the_item_a_few_levels_out(readable, invoke) -> None:
    expected = (
        0,
        [
            ROOT,
            f"├──  (depends on) {PARSER}",
            f"│   └──  (required by) {ROOT} (seen)",
            f"└──  (related) {REVIEW}",
            f"    └──  (related) {ROOT} (seen)",
        ],
    )
    assert await _graph(invoke, "4") == expected
    assert await _graph(invoke, "TASK-4") == expected


@pytest.mark.covers("graph", "ID")
async def test_graph_refuses_a_number_no_item_has(readable, invoke) -> None:
    assert await _graph(invoke, "99") == (
        1,
        ["error: no item with number 99 (use a full ID like TYPE-99 or bare 99)"],
    )


@pytest.mark.covers("graph", "--depth")
async def test_depth_cuts_the_levels_below_the_root(readable, invoke) -> None:
    assert await _graph(invoke, "4", "--depth", "1") == (
        0,
        [ROOT, f"├──  (depends on) {PARSER}", f"└──  (related) {REVIEW}"],
    )
    assert await _graph(invoke, "4", "--depth", "0") == (0, [ROOT])


@pytest.mark.covers("graph", "--depth")
async def test_depth_refuses_a_value_that_is_not_an_integer(readable, invoke) -> None:
    assert await _graph(invoke, "4", "--depth", "deep") == (
        2,
        [
            "Usage: sq graph [OPTIONS] ID",
            "Try 'sq graph --help' for help.",
            "╭─ Error ──────────────────────────────────────────────────────────────────────╮",
            "│ Invalid value for '--depth' / '-d': 'deep' is not a valid integer.           │",
            "╰──────────────────────────────────────────────────────────────────────────────╯",
        ],
    )


@pytest.mark.covers("graph", "--kind")
async def test_kind_follows_only_the_named_ref_kind(readable, invoke) -> None:
    assert await _graph(invoke, "4", "--kind", "related") == (
        0,
        [ROOT, f"└──  (related) {REVIEW}", f"    └──  (related) {ROOT} (seen)"],
    )


@pytest.mark.covers("graph", "--kind")
async def test_kind_may_be_repeated(readable, invoke) -> None:
    assert await _graph(invoke, "4", "--kind", "related", "--kind", "depends-on") == await _graph(
        invoke, "4"
    )


@pytest.mark.covers("graph", "--kind")
async def test_kind_refuses_a_kind_the_workflow_does_not_declare(readable, invoke) -> None:
    assert await _graph(invoke, "4", "--kind", "ghost") == (
        1,
        [
            "error: unknown ref kind(s): ghost. Valid kinds: addresses, blocks, depends-on, "
            "duplicates, fixes, implements, related, scopes, supersedes, targets"
        ],
    )


@pytest.mark.covers("graph", "--direction")
async def test_direction_out_follows_only_the_refs_the_item_holds(readable, invoke) -> None:
    assert await _graph(invoke, "4", "--direction", "out") == (
        0,
        [ROOT, f"├──  (depends on) {PARSER}", f"└──  (related) {REVIEW}"],
    )


@pytest.mark.covers("graph", "--direction")
async def test_direction_in_follows_only_the_refs_to_the_item(readable, invoke) -> None:
    assert await _graph(invoke, "3", "--direction", "in") == (
        0,
        [PARSER, f"└──  (required by) {ROOT}"],
    )
    assert await _graph(invoke, "3", "--direction", "out") == (0, [PARSER])


@pytest.mark.covers("graph", "--direction")
async def test_direction_refuses_a_value_other_than_out_in_or_both(readable, invoke) -> None:
    assert await _graph(invoke, "4", "--direction", "sideways") == (
        1,
        ["error: invalid direction 'sideways'; expected 'out', 'in', or 'both'"],
    )


@pytest.mark.covers("graph", "--all")
async def test_all_follows_the_links_to_closed_items(readable, invoke) -> None:
    assert await _graph(invoke, "7") == (
        0,
        [
            REVIEW,
            f"└──  (related) {ROOT}",
            f"    ├──  (depends on) {PARSER}",
            f"    └──  (related) {REVIEW} (seen)",
        ],
    )
    assert await _graph(invoke, "7", "--all") == (
        0,
        [
            REVIEW,
            f"├──  (related) {ROOT}",
            f"│   ├──  (depends on) {PARSER}",
            f"│   └──  (related) {REVIEW} (seen)",
            f"└──  (related) {BUG}",
            f"    └──  (related) {REVIEW} (seen)",
        ],
    )


@pytest.mark.covers("graph", "--format")
async def test_format_dot_prints_the_graph_as_dot_text(readable, invoke) -> None:
    result = await invoke(["graph", "4", "--format", "dot"])
    assert (result.exit_code, result.output) == (
        0,
        'digraph {\n    "REV-7";\n    "TASK-3";\n    "TASK-4";\n'
        '    "REV-7" -> "TASK-4" [label="related"];\n'
        '    "TASK-3" -> "TASK-4" [label="required by"];\n'
        '    "TASK-4" -> "REV-7" [label="related"];\n'
        '    "TASK-4" -> "TASK-3" [label="depends on"];\n}\n',
    )


@pytest.mark.covers("graph", "--format")
async def test_format_mermaid_prints_the_graph_as_a_flowchart(readable, invoke) -> None:
    result = await invoke(["graph", "4", "--format", "mermaid"])
    assert (result.exit_code, result.output) == (0, MERMAID)


@pytest.mark.covers("graph", "--format")
async def test_format_mermaid_md_wraps_the_flowchart_in_a_fence(readable, invoke) -> None:
    result = await invoke(["graph", "4", "--format", "mermaid-md"])
    assert (result.exit_code, result.output) == (0, f"```mermaid\n{MERMAID}```\n")


@pytest.mark.covers("graph", "--format")
async def test_format_refuses_a_name_other_than_dot_mermaid_or_mermaid_md(readable, invoke) -> None:
    assert await _graph(invoke, "4", "--format", "ghost") == (
        1,
        ["error: invalid --format 'ghost'; expected one of ('dot', 'mermaid', 'mermaid-md')"],
    )


@pytest.mark.covers("graph", "--json")
async def test_json_prints_the_root_with_its_nested_children(readable, invoke) -> None:
    result = await invoke(["graph", "4", "--depth", "1", "--json"])
    assert result.exit_code == 0, result.output
    # Compared as text, so the key order is held as well as the content.
    expected = {
        "id": "TASK-4",
        "type": "task",
        "status": "Draft",
        "priority": "low",
        "badges": {"priority": "low"},
        "assignee": None,
        "edge_kind": None,
        "edge_semantic": None,
        "direction": None,
        "seen": False,
        "children": [
            {
                "id": "TASK-3",
                "type": "task",
                "status": "InProgress",
                "priority": "urgent",
                "badges": {"priority": "urgent"},
                "assignee": "manager",
                "edge_kind": "depends-on",
                "edge_semantic": "dependency",
                "direction": "out",
                "seen": False,
                "children": [],
                "display": {
                    "type": "Task",
                    "status": {"badge": "🟡 In Progress", "intent": "positive"},
                    "badges": {"priority": _badge("🔴", "urgent")},
                    "assignee": "Catherine Manager",
                    "edge": "depends on",
                    "edge_label": "Depends on",
                },
            },
            {
                "id": "REV-7",
                "type": "review",
                "status": "Requested",
                "priority": None,
                "badges": {},
                "assignee": None,
                "edge_kind": "related",
                "edge_semantic": "default",
                "direction": "out",
                "seen": False,
                "children": [],
                "display": {
                    "type": "Review",
                    "status": {"badge": "⚪ Requested", "intent": "neutral"},
                    "badges": {},
                    "assignee": None,
                    "edge": "related",
                    "edge_label": "Related",
                },
            },
        ],
        "display": {
            "type": "Task",
            "status": {"badge": "⚪ Draft", "intent": "neutral"},
            "badges": {"priority": _badge("🟢", "low")},
            "assignee": None,
            "edge": None,
            "edge_label": None,
        },
    }
    assert result.output == json.dumps(expected, indent=2) + "\n"


def _badge(emoji: str, code: str) -> dict[str, str]:
    """A priority badge's display."""
    return {
        "label": "Priority",
        "badge": f"{emoji} {code}",
        "badge_label": f"{emoji} {code.title()}",
    }


MERMAID = (
    "flowchart LR\n"
    '    REV_002d7["REV-7"]\n'
    '    TASK_002d3["TASK-3"]\n'
    '    TASK_002d4["TASK-4"]\n'
    "    REV_002d7 -->|related| TASK_002d4\n"
    "    TASK_002d3 -->|required by| TASK_002d4\n"
    "    TASK_002d4 -->|related| REV_002d7\n"
    "    TASK_002d4 -->|depends on| TASK_002d3\n"
)


@pytest.mark.covers("graph", "--depth")
async def test_depth_refuses_a_negative_value(readable, invoke) -> None:
    assert await _graph(invoke, "4", "--depth", "-1") == (
        2,
        [
            "Usage: sq graph [OPTIONS] ID",
            "Try 'sq graph --help' for help.",
            "╭─ Error ──────────────────────────────────────────────────────────────────────╮",
            "│ Invalid value for '--depth' / '-d': must be 0 or more                        │",
            "╰──────────────────────────────────────────────────────────────────────────────╯",
        ],
    )
