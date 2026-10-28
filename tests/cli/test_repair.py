"""`sq repair`: rebuilding the index from the item files, reporting what it found, and
giving a shared number a new one on request."""

import json
from pathlib import Path

import pytest

from tests.cli._squadwide import listed

pytestmark = pytest.mark.anyio

TASK_FILE = "tasks/TASK-000003-build-the-query-parser.md"
ITEMS = [
    ("ROLE-1", "Catherine Manager"),
    ("FEAT-2", "Search"),
    ("TASK-3", "Build the query parser"),
    ("REV-4", "Review the query parser"),
]
TWIN = ("TASK-5", "Build the query parser")


def _add_twin_numbered_two(squad_dir: Path) -> None:
    """Write a second task whose number, 2, is the feature's."""
    original = (squad_dir / TASK_FILE).read_text(encoding="utf-8")
    twin = original.replace("id: TASK-3", "id: TASK-2").replace("sequence_id: 3", "sequence_id: 2")
    (squad_dir / "tasks/TASK-000002-build-the-query-parser.md").write_text(twin, encoding="utf-8")


async def test_repair_rebuilds_a_lost_index_from_the_item_files(populated_project, invoke) -> None:
    (populated_project.squad_dir / ".squads.json").unlink()
    result = await invoke(["repair"])
    assert (result.exit_code, result.output) == (0, "rebuilt index: 4 items, counter=4\n")
    assert await listed(invoke) == ITEMS
    shown = await invoke(["task", "3", "show", "--json"])
    assert [s["local_id"] for s in json.loads(shown.output)["subentities"]] == [
        "ST1",
        "ST2",
    ]


async def test_repair_names_an_indexed_item_whose_file_is_gone_and_keeps_the_counter(
    populated_project, invoke
) -> None:
    (populated_project.squad_dir / "reviews/REV-000004-review-the-query-parser.md").unlink()
    result = await invoke(["repair"])
    assert (result.exit_code, result.output) == (
        0,
        "rebuilt index: 3 items, counter=4\n"
        "warn REV-4: indexed but no markdown file found (deleted?)\n",
    )
    assert [i for i, _ in await listed(invoke)] == ["ROLE-1", "FEAT-2", "TASK-3"]


@pytest.mark.covers("repair", "--renumber")
async def test_renumber_gives_a_shared_number_a_new_one(populated_project, invoke) -> None:
    _add_twin_numbered_two(populated_project.squad_dir)
    result = await invoke(["repair", "--renumber"])
    assert (result.exit_code, result.output) == (0, "rebuilt index: 5 items, counter=5\n")
    assert await listed(invoke) == [*ITEMS, TWIN]


async def test_check_reports_a_shared_number_that_repair_without_renumber_leaves(
    populated_project, invoke
) -> None:
    _add_twin_numbered_two(populated_project.squad_dir)
    await invoke(["repair"])
    checked = await invoke(["check", "--json"])
    assert checked.exit_code == 3
    assert [i for i in json.loads(checked.output) if i["rule"] == "numbers_unique"] == [
        {
            "level": "error",
            "item": "#2",
            "message": "2 files carry number 2 under different ids "
            "(features/FEAT-000002-search.md, tasks/TASK-000002-build-the-query-parser.md); "
            "run `sq repair --renumber` to give one of them a new number",
            "rule": "numbers_unique",
        }
    ]


@pytest.mark.covers("repair", "--renumber")
async def test_renumber_leaves_an_id_two_files_carry_to_be_merged_by_hand(
    populated_project, invoke
) -> None:
    original = (populated_project.squad_dir / TASK_FILE).read_bytes()
    (populated_project.squad_dir / "tasks/TASK-000003-dup.md").write_bytes(original)
    result = await invoke(["repair", "--renumber"])
    assert (result.exit_code, result.output) == (
        1,
        "rebuilt index: 4 items, counter=4\n"
        "error: TASK-000003-build-the-query-parser.md: TASK-3: 2 files carry this id "
        "(tasks/TASK-000003-build-the-query-parser.md, tasks/TASK-000003-dup.md); merge the "
        "content you want into one file, delete the other by hand, then run `sq repair`\n",
    )
    assert await listed(invoke) == ITEMS
