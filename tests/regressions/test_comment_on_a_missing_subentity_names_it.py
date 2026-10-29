"""A comment on a sub-entity the item lacks is refused naming it."""

import pytest

from tests._populated import TASK

pytestmark = pytest.mark.anyio


async def test_a_comment_on_a_subtask_the_item_lacks_names_the_subtask(
    populated_project, invoke
) -> None:
    for local_id in ("9", "ST9"):
        result = await invoke(
            ["task", str(TASK), "subtask", local_id, "comment", "-m", "x", "--as", "manager"]
        )
        assert (result.exit_code, result.output) == (1, "error: no subtask ST9 in TASK-3\n")
