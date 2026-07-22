"""A handful of ``Service`` primitives that have no dedicated CLI surface of their own —
``link``/``unlink``, ``regen`` on a type without a backend entry, and a purging ``remove_item``
— plus the compound scenario where unlinking a task from its feature parent breaks a
subtask's story mapping and ``sq check`` catches it.
"""

import pytest

from squads._errors import SquadsError

pytestmark = pytest.mark.anyio


async def test_link_sets_the_parent_and_unlink_clears_it(svc):
    feat = (await svc.create("feature", "f")).item
    task = (await svc.create("task", "t")).item

    await svc.link(task.id, feat.id)
    assert (await svc.get(task.id)).parent == feat.id

    await svc.unlink(task.id)
    assert (await svc.get(task.id)).parent is None


async def test_regen_raises_for_a_type_with_no_backend_entry(svc):
    task = (await svc.create("task", "t")).item
    with pytest.raises(SquadsError, match="only roles/skills have entries"):
        await svc.regen(task.id)


async def test_remove_item_with_purge_deletes_the_markdown_file_and_its_pointer(svc):
    skill = await svc.add_skill("Temp skill")
    path = svc.paths.abspath(skill.path)
    pointer_dir = svc.paths.root / ".claude" / "skills" / "temp-skill"
    assert path.exists() and pointer_dir.exists()

    await svc.remove_item(skill.id, purge=True)

    assert skill.sequence_id not in (await svc.store.load()).items
    assert not path.exists()
    assert not pointer_dir.exists()


async def test_check_flags_a_subtask_story_mapping_once_its_task_is_unlinked_from_the_feature(
    svc,
):
    feat = (await svc.create("feature", "f")).item
    await svc.add_story(feat.id, "login")
    task = (await svc.create("task", "t", parent=feat.id)).item
    await svc.add_subtask(task.id, "impl", story="US1")

    await svc.unlink(task.id)  # breaks the spine: the subtask still points at a story id

    issues = await svc.check()
    errors = [i for i in issues if i.level == "error" and i.item == task.id]
    assert any(
        "story" in i.message.lower() or "feature parent" in i.message.lower() for i in errors
    ), f"expected a story/feature-parent error for {task.id}, got: {errors}"
