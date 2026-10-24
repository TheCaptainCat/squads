"""A subtask, an operator-assigned one included, closes straight from Todo without `--force`."""

import pytest

from _helpers import create_item

pytestmark = pytest.mark.anyio


async def test_a_subtask_goes_from_todo_to_done_without_force(svc) -> None:
    task = (await create_item(svc, "task", "Parent")).item
    subtask = await svc.add_block(task.id, "subtask", "Close me")

    await svc.set_block_status(task.id, "subtask", subtask.local_id, "Done")

    (stored,) = await svc.list_blocks(task.id, "subtask")
    assert stored.status == "Done"
