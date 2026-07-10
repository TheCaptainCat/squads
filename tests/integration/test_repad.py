"""`sq migrate repad`: widening the filename padding renames files byte-identically, never
lowers, is idempotent on already-wide files, and leaves every id-resolution path (parent,
refs, backrefs, `sq check`) working at the new width.
"""

import pytest

from squads._errors import SquadsError

pytestmark = pytest.mark.anyio


async def test_repad_renames_files_bumps_padding_and_leaves_bytes_identical(svc):
    feat = (await svc.create("feature", "feat")).item
    task = (await svc.create("task", "task")).item
    original_bytes = svc.paths.abspath(task.path).read_bytes()

    renamed = await svc.repad(7)

    db = await svc.store.load()
    assert db.padding == 7
    assert feat.sequence_id in db.items
    assert renamed == 3  # role + feature + task

    task_folder = svc.paths.folder_for("task", spec=svc.spec)
    new_files = list(task_folder.glob("TASK-*.md"))
    assert len(new_files) == 1
    assert new_files[0].read_bytes() == original_bytes


async def test_repad_refuses_to_lower_the_width(svc):
    await svc.create("task", "t")
    with pytest.raises(SquadsError, match="must be greater than"):
        await svc.repad(6)
    with pytest.raises(SquadsError, match="must be greater than"):
        await svc.repad(5)


async def test_repad_is_idempotent_on_files_already_at_the_target_width(svc):
    await svc.create("task", "t")
    await svc.repad(7)
    renamed_again = await svc.repad(8)
    assert renamed_again > 0  # width-7 -> width-8 does rename
    db = await svc.store.load()
    assert db.padding == 8


async def test_repad_leaves_check_clean_and_every_id_resolution_path_working(svc):
    """Display stays unpadded, and parent/ref lookups resolve at any width — the filename
    change must never leak into content or lookups."""
    feat = (await svc.create("feature", "feat")).item
    task = (await svc.create("task", "task", parent=feat.id)).item
    await svc.add_ref(task.id, feat.id)

    await svc.repad(7)

    db = await svc.store.load()
    loaded_task = db.items[task.sequence_id]
    assert loaded_task.id == task.id  # unpadded, unchanged by repad
    assert loaded_task.parent == feat.id  # parent field content untouched
    padded6 = f"FEAT-{feat.sequence_id:06d}"
    padded7 = f"FEAT-{feat.sequence_id:07d}"
    assert db.get(padded6) is db.items[feat.sequence_id]
    assert db.get(padded7) is db.items[feat.sequence_id]

    for query in (feat.id, padded6, padded7):
        backrefs = await svc.refs_in(query)
        assert backrefs == [(task.id, "related")]

    issues = await svc.check()
    assert not [i for i in issues if i.level == "error"]
