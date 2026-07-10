"""The subtask/story lifecycle helper methods that sit on top of the generic
``update_block``/``set_block_status``: ``set_subtask_done`` toggles between the kind's
completion status and its initial one, ``set_story_status`` delegates the same mechanism to a
story block (and is rejected on a non-feature host), an unknown local id raises, and stories are
refused on a type that doesn't host them (with a spec-resolved hint naming what it does host).
"""

import pytest

from squads._errors import SquadsError

pytestmark = pytest.mark.anyio


async def test_stories_are_refused_on_a_type_that_does_not_host_them(svc):
    task = (await svc.create("task", "t")).item  # tasks host subtasks, not stories
    with pytest.raises(SquadsError, match="does not host"):
        await svc.add_story(task.id, "As a user...")


async def test_subtask_done_toggles_between_the_completion_and_initial_status(svc):
    task = (await svc.create("task", "t")).item
    await svc.add_subtask(task.id, "Validate expiry")

    await svc.set_subtask_done(task.id, "ST1", done=True)
    assert (await svc.list_subtasks(task.id))[0].status == "Done"

    await svc.set_subtask_done(task.id, "ST1", done=False)
    assert (await svc.list_subtasks(task.id))[0].status == "Todo"


async def test_subtask_done_raises_for_an_unknown_local_id(svc):
    task = (await svc.create("task", "t")).item
    with pytest.raises(SquadsError):
        await svc.set_subtask_done(task.id, "ST9")


async def test_set_story_status_delegates_to_the_generic_block_status_setter(svc):
    feat = (await svc.create("feature", "f")).item
    await svc.add_story(feat.id, "reset password")  # US1
    await svc.set_story_status(feat.id, "US1", "InProgress")
    assert (await svc.list_stories(feat.id))[0].status == "InProgress"


async def test_set_story_status_on_the_wrong_host_type_raises(svc):
    """The same delegation, called with a task's own local id — tasks don't host stories at
    all, so this is rejected before any status machine logic runs."""
    task = (await svc.create("task", "t")).item
    await svc.add_subtask(task.id, "Validate")
    with pytest.raises(SquadsError):
        await svc.set_story_status(task.id, "ST1", "Todo")


async def test_subtask_body_set_then_append_joins_with_a_blank_line_not_a_bare_placeholder(svc):
    task = (await svc.create("task", "t")).item
    await svc.add_subtask(task.id, "Validate")

    await svc.set_subtask_body(task.id, "ST1", "First paragraph.")
    await svc.set_subtask_body(task.id, "ST1", "Second paragraph.", append=True)
    assert (await svc.get_subtask(task.id, "ST1")).body == "First paragraph.\n\nSecond paragraph."
