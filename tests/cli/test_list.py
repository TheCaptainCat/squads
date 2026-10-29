"""`sq list`: each filter alone, the sort, the closed-item rule and the output forms, plus the
interactions between the priority options, between the badge options and between sort and JSON."""

import json
import re

import pytest

from tests._readable import init_readable, lines
from tests.cli._output import unknown_option

pytestmark = pytest.mark.anyio

HEADER = "ID      Type      Status      Priority   Title              Parent  Assignee"
ROLE = "ROLE-1  role      Active                 Catherine Manager"
FEATURE = "FEAT-2  feature   Draft       🟠 high    Search                     manager"
PARSER = "TASK-3  task      InProgress  🔴 urgent  Parse queries      FEAT-2  manager"
RANKING = "TASK-4  task      Draft       🟢 low     Rank results       FEAT-2"
DECISION = "ADR-5   decision  Proposed               Pick an index"
REVIEW = "REV-7   review    Requested              Review the parser"
ALL_OPEN = [HEADER, ROLE, FEATURE, PARSER, RANKING, DECISION, REVIEW]


@pytest.fixture
def readable(copy_squad):
    return copy_squad("readable", init_readable)


async def _list(invoke, *args: str) -> tuple[int, list[str]]:
    result = await invoke(["list", *args])
    return result.exit_code, lines(result.output)


async def _ids(invoke, *args: str) -> list[str]:
    result = await invoke(["list", "--json", *args])
    assert result.exit_code == 0, result.output
    return [item["id"] for item in json.loads(result.output)]


@pytest.mark.covers("list")
async def test_list_hides_closed_items_by_default(readable, invoke) -> None:
    assert await _list(invoke) == (0, ALL_OPEN)


@pytest.mark.covers("list", "--all")
async def test_all_includes_the_closed_items(readable, invoke) -> None:
    assert await _list(invoke, "--all") == (
        0,
        [
            *ALL_OPEN[:-1],
            "BUG-6   bug       Verified    🟡 medium  Empty query crash          manager",
            REVIEW,
        ],
    )


@pytest.mark.covers("list", "--type")
async def test_type_keeps_one_type(readable, invoke) -> None:
    assert await _list(invoke, "--type", "task") == (
        0,
        [
            "ID      Type  Status      Priority   Title          Parent  Assignee",
            "TASK-3  task  InProgress  🔴 urgent  Parse queries  FEAT-2  manager",
            "TASK-4  task  Draft       🟢 low     Rank results   FEAT-2",
        ],
    )


@pytest.mark.covers("list", "--type")
async def test_type_refuses_an_unknown_type(readable, invoke) -> None:
    assert await _list(invoke, "--type", "ghost") == (
        1,
        [
            "error: unknown type 'ghost' (one of: bug, contract, decision, epic, feature, "
            "guide, milestone, operator, review, role, skill, task)"
        ],
    )


@pytest.mark.covers("list", "--status")
async def test_status_keeps_one_status_even_when_it_is_closed(readable, invoke) -> None:
    assert await _list(invoke, "--status", "Verified") == (
        0,
        [
            "ID     Type  Status    Priority   Title              Parent  Assignee",
            "BUG-6  bug   Verified  🟡 medium  Empty query crash          manager",
        ],
    )


@pytest.mark.covers("list", "--status")
async def test_status_refuses_an_unknown_status(readable, invoke) -> None:
    code, out = await _list(invoke, "--status", "Ghost")
    assert (code, out[0][:34]) == (1, "error: unknown status 'Ghost' (one")


@pytest.mark.covers("list", "--parent")
async def test_parent_keeps_the_direct_children(readable, invoke) -> None:
    assert await _list(invoke, "--parent", "2") == (
        0,
        [
            "ID      Type  Status      Priority   Title          Parent  Assignee",
            "TASK-3  task  InProgress  🔴 urgent  Parse queries  FEAT-2  manager",
            "TASK-4  task  Draft       🟢 low     Rank results   FEAT-2",
        ],
    )


@pytest.mark.covers("list", "--parent")
async def test_parent_accepts_the_full_id(readable, invoke) -> None:
    assert await _ids(invoke, "--parent", "FEAT-2") == ["TASK-3", "TASK-4"]


@pytest.mark.covers("list", "--parent")
async def test_parent_refuses_a_number_no_item_has(readable, invoke) -> None:
    assert await _list(invoke, "--parent", "99") == (
        1,
        ["error: no item with number 99 (use a full ID like TYPE-99 or bare 99)"],
    )


@pytest.mark.covers("list", "--label")
async def test_label_keeps_the_items_carrying_it(readable, invoke) -> None:
    assert await _list(invoke, "--label", "core") == (
        0,
        [
            "ID      Type     Status  Priority  Title   Parent  Assignee",
            "FEAT-2  feature  Draft   🟠 high   Search          manager",
        ],
    )


@pytest.mark.covers("list", "--assignee")
async def test_assignee_keeps_the_items_assigned_to_the_slug(readable, invoke) -> None:
    assert await _list(invoke, "--assignee", "manager") == (
        0,
        [
            "ID      Type     Status      Priority   Title          Parent  Assignee",
            "FEAT-2  feature  Draft       🟠 high    Search                 manager",
            "TASK-3  task     InProgress  🔴 urgent  Parse queries  FEAT-2  manager",
        ],
    )


@pytest.mark.covers("list", "--assignee")
async def test_assignee_refuses_a_slug_no_roster_entry_has(readable, invoke) -> None:
    assert await _list(invoke, "--assignee", "ghost") == (
        1,
        ["error: unknown slug 'ghost'; valid slugs: manager"],
    )


@pytest.mark.covers("list", "--category")
async def test_category_keeps_one_category(readable, invoke) -> None:
    assert await _list(invoke, "--category", "roster") == (
        0,
        [
            "ID      Type  Status  Priority  Title              Parent  Assignee",
            "ROLE-1  role  Active            Catherine Manager",
        ],
    )


@pytest.mark.covers("list", "--category")
async def test_category_refuses_an_unknown_category(readable, invoke) -> None:
    assert await _list(invoke, "--category", "ghost") == (
        1,
        ["error: unknown category 'ghost' (one of: roster, work, records)"],
    )


@pytest.mark.covers("list", "--<field>")
async def test_priority_keeps_the_items_of_exactly_that_priority(readable, invoke) -> None:
    assert await _list(invoke, "--priority", "low") == (
        0,
        [
            "ID      Type  Status  Priority  Title         Parent  Assignee",
            "TASK-4  task  Draft   🟢 low    Rank results  FEAT-2",
        ],
    )


@pytest.mark.covers("list", "--<field>")
async def test_priority_refuses_an_unknown_code(readable, invoke) -> None:
    assert await _list(invoke, "--priority", "ghost") == (
        1,
        ["error: unknown priority 'ghost' (one of: urgent, high, medium, low)"],
    )


@pytest.mark.covers("list", "--min-<field>")
async def test_min_priority_keeps_the_items_at_least_that_urgent(readable, invoke) -> None:
    assert await _list(invoke, "--min-priority", "high") == (
        0,
        [
            "ID      Type     Status      Priority   Title          Parent  Assignee",
            "FEAT-2  feature  Draft       🟠 high    Search                 manager",
            "TASK-3  task     InProgress  🔴 urgent  Parse queries  FEAT-2  manager",
        ],
    )


@pytest.mark.covers("list", "--min-<field>")
async def test_min_priority_refuses_an_unknown_code(readable, invoke) -> None:
    assert await _list(invoke, "--min-priority", "ghost") == (
        1,
        ["error: unknown priority 'ghost' (one of: urgent, high, medium, low)"],
    )


@pytest.mark.covers("list", "--badge")
async def test_badge_keeps_the_items_whose_field_has_the_value(readable, invoke) -> None:
    assert await _list(invoke, "--badge", "priority=high") == (
        0,
        [
            "ID      Type     Status  Priority  Title   Parent  Assignee",
            "FEAT-2  feature  Draft   🟠 high   Search          manager",
        ],
    )


@pytest.mark.covers("list", "--badge")
async def test_badge_refuses_a_pair_without_a_value(readable, invoke) -> None:
    assert await _list(invoke, "--badge", "priority") == (
        1,
        ["error: expected CODE=VALUE, got 'priority'"],
    )


@pytest.mark.covers("list", "--min-badge")
async def test_min_badge_keeps_the_items_at_least_that_rank(readable, invoke) -> None:
    assert await _list(invoke, "--min-badge", "priority=high") == (
        0,
        [
            "ID      Type     Status      Priority   Title          Parent  Assignee",
            "FEAT-2  feature  Draft       🟠 high    Search                 manager",
            "TASK-3  task     InProgress  🔴 urgent  Parse queries  FEAT-2  manager",
        ],
    )


@pytest.mark.covers("list", "--min-badge")
async def test_min_badge_refuses_a_pair_without_a_value(readable, invoke) -> None:
    assert await _list(invoke, "--min-badge", "priority") == (
        1,
        ["error: expected CODE=VALUE, got 'priority'"],
    )


@pytest.mark.covers("list", "--sort")
async def test_sort_orders_the_rows_by_the_rank_of_the_badge_field(readable, invoke) -> None:
    assert await _list(invoke, "--sort", "priority") == (
        0,
        [HEADER, PARSER, FEATURE, RANKING, ROLE, DECISION, REVIEW],
    )


@pytest.mark.covers("list", "--compact")
async def test_compact_prints_one_line_per_item(readable, invoke) -> None:
    result = await invoke(["list", "--compact"])
    assert (result.exit_code, result.output) == (
        0,
        "ROLE-1  Active  Catherine Manager\n"
        "FEAT-2  Draft  Search\n"
        "TASK-3  InProgress  Parse queries\n"
        "TASK-4  Draft  Rank results\n"
        "ADR-5  Proposed  Pick an index\n"
        "REV-7  Requested  Review the parser\n",
    )


@pytest.mark.covers("list", "--json")
async def test_json_prints_one_object_per_item(readable, invoke) -> None:
    result = await invoke(["list", "--json", "--type", "decision"])
    assert result.exit_code == 0, result.output
    # Compared as text, so the key order is held as well as the content.
    assert (
        result.output
        == json.dumps(
            [
                {
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
                    "badges": {},
                    "display": {
                        "type": "Decision",
                        "status": {"badge": "⚪ Proposed", "intent": "neutral"},
                        "badges": {},
                        "assignee": None,
                    },
                }
            ],
            indent=2,
        )
        + "\n"
    )


def _crash_row(assignee_name: str) -> dict[str, object]:
    """The closed bug's row, its assignee shown as *assignee_name*."""
    return {
        "sequence_id": 6,
        "type": "bug",
        "title": "Empty query crash",
        "slug": "empty-query-crash",
        "status": "Verified",
        "description": "",
        "parent": None,
        "author": "manager",
        "assignee": "manager",
        "labels": [],
        "refs": [],
        "subentities": [],
        "path": "bugs/BUG-000006-empty-query-crash.md",
        "created_at": "2026-06-07T10:00:00Z",
        "updated_at": "2026-06-07T10:00:00Z",
        "created_session": None,
        "modified_session": None,
        "id": "BUG-6",
        "priority": "medium",
        "severity": "medium",
        "badges": {"priority": "medium", "severity": "medium"},
        "display": {
            "type": "Bug",
            "status": {"badge": "🟢 Verified", "intent": "positive"},
            "badges": {
                "priority": {"label": "Priority", "badge": "🟡 medium", "badge_label": "🟡 Medium"},
                "severity": {"label": "Severity", "badge": "🟡 medium", "badge_label": "🟡 Medium"},
            },
            "assignee": assignee_name,
        },
    }


@pytest.mark.covers("list", "--json")
async def test_json_names_the_assignee_with_pronouns_unless_the_squad_hides_them(
    readable, invoke
) -> None:
    await invoke(["role", "manager", "update", "--pronouns", "she/her"])
    shown = await invoke(["list", "--json", "--type", "bug", "--all"])
    assert shown.output == json.dumps([_crash_row("Catherine Manager (she/her)")], indent=2) + "\n"
    config = readable.config_path.read_text(encoding="utf-8")
    readable.config_path.write_text(config + "\n[display]\npronouns = false\n", encoding="utf-8")
    hidden = await invoke(["list", "--json", "--type", "bug", "--all"])
    assert hidden.output == json.dumps([_crash_row("Catherine Manager")], indent=2) + "\n"


# --- interactions ---------------------------------------------------------------------------


@pytest.mark.covers("list", "--type")
async def test_a_closed_item_is_hidden_with_a_hint_until_all_is_given(readable, invoke) -> None:
    hidden = await invoke(["list", "--type", "bug"])
    assert (hidden.exit_code, hidden.output) == (0, "1 closed items hidden — use --all\n")


@pytest.mark.covers("list", "--compact", "--json")
async def test_compact_refuses_json(readable, invoke) -> None:
    assert await _list(invoke, "--compact", "--json") == (
        2,
        [
            "Usage: sq list [OPTIONS]",
            "Try 'sq list --help' for help.",
            "╭─ Error ──────────────────────────────────────────────────────────────────────╮",
            "│ Invalid value: --compact and --json are mutually exclusive                   │",
            "╰──────────────────────────────────────────────────────────────────────────────╯",
        ],
    )


@pytest.mark.covers("list", "--<field>")
@pytest.mark.covers("list", "--min-<field>")
async def test_a_field_only_some_types_declare_filters_exactly_and_by_threshold(
    readable, invoke
) -> None:
    assert await _ids(invoke, "--all", "--severity", "medium") == ["BUG-6"]
    assert await _ids(invoke, "--all", "--min-severity", "medium") == ["BUG-6"]
    assert await _ids(invoke, "--all", "--min-severity", "high") == []
    assert await _list(invoke, "--severity", "ghost") == (
        1,
        ["error: unknown severity 'ghost' (one of: critical, high, medium, low, info)"],
    )


@pytest.mark.covers("list", "--json")
async def test_a_derived_filter_means_exactly_its_generic_form(override_project, invoke) -> None:
    created = await invoke(
        ["create", "initiative", "Later one", "--author", "manager", "--urgency", "later"]
    )
    assert created.exit_code == 0, created.output
    for derived, generic in (
        (["--urgency", "now"], ["--badge", "urgency=now"]),
        (["--min-urgency", "soon"], ["--min-badge", "urgency=soon"]),
    ):
        derived_ids = await _ids(invoke, *derived)
        assert derived_ids == await _ids(invoke, *generic)
        assert derived_ids == ["INI-8"]
    assert await _ids(invoke, "--urgency", "later") == ["INI-11"]
    refused = await invoke(["list", "--json", "--priority", "high"])
    assert (refused.exit_code, refused.output) == (
        2,
        unknown_option("list [OPTIONS]", "list", "--priority", " ('(Possible options: --sort)',)"),
    )


@pytest.mark.covers("list", "--json")
async def test_a_generic_form_refuses_a_code_no_type_declares_naming_the_declared_ones(
    override_project, invoke
) -> None:
    declared = "(one of: urgency, work_size)"
    for option, value, what in (
        ("--badge", "priority=high", "badge field"),
        ("--min-badge", "priority=high", "badge field"),
        ("--sort", "priority", "sort field"),
    ):
        result = await invoke(["list", "--json", option, value])
        assert (result.exit_code, result.output) == (
            1,
            f"error: unknown {what} 'priority' {declared}\n",
        )


@pytest.mark.covers("list")
async def test_the_badge_column_is_the_first_ordered_field_headed_by_its_label(
    override_project, invoke
) -> None:
    result = await invoke(["list"])
    assert result.exit_code == 0, result.output
    header = lines(result.output)[0].split()
    assert header[:4] == ["ID", "Type", "Status", "Urgency"]
    assert "Priority" not in header


@pytest.mark.covers("list")
async def test_a_squad_declaring_no_field_lists_no_badge_column(override_project, invoke) -> None:
    override = override_project.squad_dir / ".overrides" / "workflow.toml"
    text = override.read_text(encoding="utf-8")
    text = re.sub(r"^fields = \[.*?\]\n", "fields = []\n", text, flags=re.M | re.S)
    override.write_text(text, encoding="utf-8")
    result = await invoke(["list"])
    assert result.exit_code == 0, result.output
    assert lines(result.output)[0].split()[:4] == ["ID", "Type", "Status", "Title"]


@pytest.mark.covers("list", "--<field>", "--min-<field>")
async def test_priority_and_min_priority_both_apply_to_one_listing(readable, invoke) -> None:
    both = await _list(invoke, "--priority", "urgent", "--min-priority", "high")
    assert both == (
        0,
        [
            "ID      Type  Status      Priority   Title          Parent  Assignee",
            "TASK-3  task  InProgress  🔴 urgent  Parse queries  FEAT-2  manager",
        ],
    )
    below = await _list(invoke, "--priority", "low", "--min-priority", "high")
    assert below == (0, ["no items"])


@pytest.mark.covers("list", "--badge", "--min-badge")
async def test_badge_and_min_badge_both_apply_to_one_listing(readable, invoke) -> None:
    both = await _list(invoke, "--badge", "priority=urgent", "--min-badge", "priority=high")
    assert both == (
        0,
        [
            "ID      Type  Status      Priority   Title          Parent  Assignee",
            "TASK-3  task  InProgress  🔴 urgent  Parse queries  FEAT-2  manager",
        ],
    )
    below = await _list(invoke, "--badge", "priority=low", "--min-badge", "priority=high")
    assert below == (0, ["no items"])


@pytest.mark.covers("list", "--sort", "--json")
async def test_sort_decides_the_order_of_the_json_array(readable, invoke) -> None:
    assert await _ids(invoke, "--sort", "priority") == [
        "TASK-3",
        "FEAT-2",
        "TASK-4",
        "ROLE-1",
        "ADR-5",
        "REV-7",
    ]
    assert await _ids(invoke) == ["ROLE-1", "FEAT-2", "TASK-3", "TASK-4", "ADR-5", "REV-7"]


@pytest.mark.covers("list", "--sort")
async def test_sort_refuses_a_field_that_is_not_an_ordered_badge_field(readable, invoke) -> None:
    assert await _list(invoke, "--sort", "ghost") == (
        1,
        ["error: unknown sort field 'ghost' (one of: priority, severity)"],
    )


@pytest.mark.covers("list", "--badge")
@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("priority=ghost", "unknown priority 'ghost' (one of: urgent, high, medium, low)"),
        ("ghost=x", "unknown badge field 'ghost' (one of: priority, severity)"),
    ],
)
async def test_badge_refuses_an_unknown_field_or_value(readable, invoke, value, message) -> None:
    assert await _list(invoke, "--badge", value) == (1, [f"error: {message}"])


@pytest.mark.covers("list", "--min-badge")
async def test_min_badge_refuses_an_unknown_value(readable, invoke) -> None:
    assert await _list(invoke, "--min-badge", "priority=ghost") == (
        1,
        ["error: unknown priority 'ghost' (one of: urgent, high, medium, low)"],
    )


@pytest.mark.covers("list", "--json")
@pytest.mark.covers("list", "--all")
async def test_the_item_row_carries_a_stored_field_by_its_code_and_no_other(
    override_project, invoke
) -> None:
    rows = {
        row["id"]: row for row in json.loads((await invoke(["list", "--json", "--all"])).output)
    }
    assert rows["INI-8"]["urgency"] == "now"
    assert rows["INI-8"]["badges"] == {"urgency": "now"}
    assert rows["JOB-9"]["work_size"] == "m"
    assert "urgency" not in rows["JOB-9"]
    assert not {"priority", "severity"} & set(rows["INI-8"])
    assert not {"priority", "severity"} & set(rows["REC-10"])
