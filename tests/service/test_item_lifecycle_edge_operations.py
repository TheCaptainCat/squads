"""A handful of ``Service`` primitives that have no dedicated CLI surface of their own —
``link``/``unlink``, ``regen`` on a type without a backend entry, and a purging ``remove_item``
— plus the compound scenario where unlinking a task from its feature parent breaks a
subtask's story mapping and ``sq check`` catches it.
"""

import pytest

from _helpers import create_item
from squads._errors import SquadsError
from squads._services._service import Service
from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import WorkflowSpec

pytestmark = pytest.mark.anyio


def _spec_with_renamed_story_and_subtask_kinds() -> WorkflowSpec:
    """The bundled spec with ``feature``'s and ``task``'s hosted sub-entity kinds renamed
    (``story`` -> ``userstory``, ``subtask`` -> ``checklist``) — everything else stays exactly
    as bundled, so only the kind KEY differs from the literal a spec-blind check might compare
    against."""
    base = load_workflow_spec()
    return base.model_copy(
        update={
            "items": {
                **base.items,
                "feature": base.items["feature"].model_copy(update={"subentity_kind": "userstory"}),
                "task": base.items["task"].model_copy(update={"subentity_kind": "checklist"}),
            },
            "subentity_kinds": {
                **{k: v for k, v in base.subentity_kinds.items() if k not in ("story", "subtask")},
                "userstory": base.subentity_kinds["story"].model_copy(),
                "checklist": base.subentity_kinds["subtask"].model_copy(),
            },
        }
    )


async def test_link_sets_the_parent_and_unlink_clears_it(svc):
    feat = (await create_item(svc, "feature", "f")).item
    task = (await create_item(svc, "task", "t")).item

    await svc.link(task.id, feat.id)
    assert (await svc.get(task.id)).parent == feat.id

    await svc.unlink(task.id)
    assert (await svc.get(task.id)).parent is None


async def test_regen_raises_for_a_type_with_no_backend_entry(svc):
    task = (await create_item(svc, "task", "t")).item
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
    feat = (await create_item(svc, "feature", "f")).item
    await svc.add_story(feat.id, "login")
    task = (await create_item(svc, "task", "t", parent=feat.id)).item
    await svc.add_subtask(task.id, "impl", story="US1")

    await svc.unlink(task.id)  # breaks the spine: the subtask still points at a story id

    issues = await svc.check()
    errors = [i for i in issues if i.level == "error" and i.item == task.id]
    assert any(
        "story" in i.message.lower() or "feature parent" in i.message.lower() for i in errors
    ), f"expected a story/feature-parent error for {task.id}, got: {errors}"


async def test_check_flags_the_same_dangling_mapping_after_the_story_and_subtask_kinds_are_renamed(
    project,
):
    """The renamed-kind counterpart to the test above: the validator must be driven by the
    spec's ``maps_parent_story`` flag (as ``_check_maps_parent_story`` already is), not a
    ``kind != "subtask"`` literal — otherwise a project that renames the built-in kinds loses
    ``sq check``'s dangling-story-mapping detection entirely."""
    svc = Service(project, spec=_spec_with_renamed_story_and_subtask_kinds())
    feat = (await create_item(svc, "feature", "f")).item
    story = await svc.add_block(feat.id, "userstory", "login")
    task = (await create_item(svc, "task", "t", parent=feat.id)).item
    await svc.add_block(task.id, "checklist", "impl", story=story.local_id)

    await svc.unlink(task.id)  # breaks the spine: the checklist item still points at a story id

    issues = await svc.check()
    errors = [i for i in issues if i.level == "error" and i.item == task.id]
    assert any(
        "story" in i.message.lower() or "feature parent" in i.message.lower() for i in errors
    ), f"expected a story/feature-parent error for {task.id}, got: {errors}"
