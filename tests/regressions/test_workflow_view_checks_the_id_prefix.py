"""`sq workflow view` refuses an ID whose prefix is not its type's own."""

import pytest

from tests._populated import TASK

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("view", ["memory_skill", "milestone_rollup"])
async def test_workflow_view_refuses_an_id_whose_prefix_is_not_its_owners(
    populated_project, invoke, view: str
) -> None:
    result = await invoke(["workflow", "view", view, f"FEAT-{TASK}"])
    assert (result.exit_code, result.output.strip()) == (
        1,
        f"error: FEAT-{TASK} is TASK-{TASK} (task)",
    )
