import pytest

from tests.cli._populated import TASK, init_populated

pytestmark = pytest.mark.anyio


@pytest.fixture
def populated_project(copy_squad):
    return copy_squad("populated", init_populated)


async def test_a_comment_on_a_subtask_the_item_lacks_names_the_subtask(
    populated_project, invoke
) -> None:
    for local_id in ("9", "ST9"):
        result = await invoke(
            ["task", str(TASK), "subtask", local_id, "comment", "-m", "x", "--as", "manager"]
        )
        assert (result.exit_code, result.output) == (1, "error: no subtask ST9 in TASK-3\n")
