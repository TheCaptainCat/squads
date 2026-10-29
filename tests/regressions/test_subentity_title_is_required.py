import json

import pytest

from tests.cli._populated import TASK, init_populated

pytestmark = pytest.mark.anyio


@pytest.fixture
def populated_project(copy_squad):
    return copy_squad("populated", init_populated)


async def _titles(invoke) -> list[str]:
    out = await invoke(["task", str(TASK), "subtasks", "--json"])
    return [row["title"] for row in json.loads(out.output)]


async def test_a_subtask_cannot_be_added_without_a_title_or_with_a_blank_one(
    populated_project, invoke
) -> None:
    before = await _titles(invoke)
    missing = await invoke(["task", str(TASK), "add-subtask"])
    blank = await invoke(["task", str(TASK), "add-subtask", "   "])
    assert missing.exit_code == 2
    assert (blank.exit_code, blank.output) == (1, "error: title must not be empty\n")
    assert await _titles(invoke) == before


async def test_a_subtask_title_cannot_be_updated_to_a_blank_one(populated_project, invoke) -> None:
    before = await _titles(invoke)
    result = await invoke(["task", str(TASK), "subtask", "1", "update", "--title", " "])
    assert (result.exit_code, result.output) == (1, "error: title must not be empty\n")
    assert await _titles(invoke) == before
