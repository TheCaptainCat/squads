"""A sub-entity cannot be added without a title or retitled to a blank one."""

import json

import pytest

from tests._populated import TASK

pytestmark = pytest.mark.anyio


async def _titles(invoke) -> list[str]:
    out = await invoke(["task", str(TASK), "subtasks", "--json"])
    return [row["title"] for row in json.loads(out.output)]


async def test_a_subtask_cannot_be_added_without_a_title_or_with_a_blank_one(
    populated_project, invoke
) -> None:
    before = await _titles(invoke)
    missing = await invoke(["task", str(TASK), "add-subtask"])
    blank = await invoke(["task", str(TASK), "add-subtask", "   "])
    assert (missing.exit_code, missing.output) == (
        2,
        "Usage: sq task N add-subtask [OPTIONS] TITLE\n"
        "Try 'sq task N add-subtask --help' for help.\n"
        "╭─ Error ──────────────────────────────────────────────────────────────────────╮\n"
        "│ Missing argument 'TITLE'.                                                    │\n"
        "╰──────────────────────────────────────────────────────────────────────────────╯\n",
    )
    assert (blank.exit_code, blank.output) == (1, "error: title must not be empty\n")
    assert await _titles(invoke) == before


async def test_a_subtask_title_cannot_be_updated_to_a_blank_one(populated_project, invoke) -> None:
    before = await _titles(invoke)
    result = await invoke(["task", str(TASK), "subtask", "1", "update", "--title", " "])
    assert (result.exit_code, result.output) == (1, "error: title must not be empty\n")
    assert await _titles(invoke) == before
