"""`sq renumber`: moving this branch's item numbers past another branch's counter, with every
reference to a moved item rewritten."""

import json

import pytest

from tests.cli._squadwide import listed

pytestmark = pytest.mark.anyio

USAGE = "Usage: sq renumber [OPTIONS]\nTry 'sq renumber --help' for help.\n"
BOTH_OR_NEITHER = (
    USAGE + "╭─ Error ──────────────────────────────────────────────────────────────────────╮\n"
    "│ Invalid value: provide exactly one of --onto or --by                         │\n"
    "╰──────────────────────────────────────────────────────────────────────────────╯\n"
)
UNCERTIFIED = (
    "warning: sq cannot certify this offset clears the OTHER branch's counter without --onto — "
    "that guarantee is yours to make on this path.\n"
)


@pytest.mark.covers("renumber", "--by")
async def test_by_adds_its_value_to_every_number_from_the_lowest_moved(
    populated_project, invoke
) -> None:
    result = await invoke(["renumber", "--from", "2", "--by", "10"])
    assert (result.exit_code, result.output) == (
        0,
        UNCERTIFIED + "renumbered 3 item(s); counter=14\n"
        "  FEAT-2 -> FEAT-12\n  REV-4 -> REV-14\n  TASK-3 -> TASK-13\n",
    )
    assert await listed(invoke) == [
        ("ROLE-1", "Catherine Manager"),
        ("FEAT-12", "Search"),
        ("TASK-13", "Build the query parser"),
        ("REV-14", "Review the query parser"),
    ]


@pytest.mark.covers("renumber", "--by")
async def test_by_rewrites_the_references_to_a_moved_item(populated_project, invoke) -> None:
    result = await invoke(["renumber", "--from", "2", "--by", "10"])
    assert result.exit_code == 0, result.output
    shown = await invoke(["task", "13", "show", "--json"])
    task = json.loads(shown.output)
    assert (task["parent"], task["subentities"][0]["story"]) == ("FEAT-12", "US1")


@pytest.mark.covers("renumber", "--by")
async def test_by_refuses_an_offset_that_does_not_clear_the_branch_counter(
    populated_project, invoke
) -> None:
    result = await invoke(["renumber", "--from", "2", "--by", "1"])
    assert (result.exit_code, result.output) == (
        1,
        "error: --by 1 is unsafe: 2 + 1 = 3 does not clear this branch's own counter (4); "
        "minimum safe offset is 3. sq cannot certify this offset clears the OTHER branch's "
        "counter without --onto — that guarantee is yours to make on this path.\n",
    )
    assert [i for i, _ in await listed(invoke)] == ["ROLE-1", "FEAT-2", "TASK-3", "REV-4"]


@pytest.mark.covers("renumber", "--onto")
async def test_onto_moves_the_items_from_the_lowest_just_past_the_other_counter(
    populated_project, invoke
) -> None:
    result = await invoke(["renumber", "--from", "3", "--onto", "20"])
    assert (result.exit_code, result.output) == (
        0,
        "renumbered 2 item(s); counter=22\n  REV-4 -> REV-22\n  TASK-3 -> TASK-21\n",
    )
    assert await listed(invoke) == [
        ("ROLE-1", "Catherine Manager"),
        ("FEAT-2", "Search"),
        ("TASK-21", "Build the query parser"),
        ("REV-22", "Review the query parser"),
    ]


@pytest.mark.covers("renumber", "--onto")
async def test_onto_reports_when_no_item_is_at_or_above_from(populated_project, invoke) -> None:
    result = await invoke(["renumber", "--from", "30", "--onto", "40"])
    assert (result.exit_code, result.output) == (
        0,
        "nothing to renumber — no local item at or above --from\n",
    )


@pytest.mark.covers("renumber", "--onto", "--by")
async def test_onto_refuses_by(populated_project, invoke) -> None:
    result = await invoke(["renumber", "--from", "2", "--onto", "9", "--by", "3"])
    assert (result.exit_code, result.output) == (2, BOTH_OR_NEITHER)
    assert [i for i, _ in await listed(invoke)] == ["ROLE-1", "FEAT-2", "TASK-3", "REV-4"]


@pytest.mark.covers("renumber", "--from")
async def test_renumber_refuses_to_run_with_neither_onto_nor_by(populated_project, invoke) -> None:
    result = await invoke(["renumber", "--from", "2"])
    assert (result.exit_code, result.output) == (2, BOTH_OR_NEITHER)


@pytest.mark.covers("renumber", "--from")
async def test_from_is_required(populated_project, invoke) -> None:
    result = await invoke(["renumber", "--onto", "9"])
    assert (result.exit_code, result.output) == (
        2,
        USAGE + "╭─ Error ──────────────────────────────────────────────────────────────────────╮\n"
        "│ Missing option '--from'.                                                     │\n"
        "╰──────────────────────────────────────────────────────────────────────────────╯\n",
    )


@pytest.mark.covers("renumber", "--from")
async def test_from_refuses_a_value_that_is_not_an_integer(populated_project, invoke) -> None:
    result = await invoke(["renumber", "--from", "x", "--by", "10"])
    assert (result.exit_code, result.output) == (
        2,
        USAGE + "╭─ Error ──────────────────────────────────────────────────────────────────────╮\n"
        "│ Invalid value for '--from': 'x' is not a valid integer.                      │\n"
        "╰──────────────────────────────────────────────────────────────────────────────╯\n",
    )
