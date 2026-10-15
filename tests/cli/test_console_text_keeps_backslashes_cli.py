import re

import pytest

pytestmark = pytest.mark.anyio


async def test_an_error_echoes_a_backslash_before_a_bracket_as_typed(project, invoke) -> None:
    created = await invoke(["create", "task", "t", "--author", "manager"])
    assert created.exit_code == 0, created.output
    match = re.search(r"TASK-(\d+)", created.output)
    assert match
    story = r"\[A-Z]+-\d+\]"
    result = await invoke(["task", match.group(1), "add-subtask", "x", "--story", story])
    assert result.exit_code == 1, result.output
    assert story.upper() in result.output.replace("\n", "")
