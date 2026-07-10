"""``Service.remove_work_item()``: hard delete, ref/child guards, and the sequence-number gap
they leave behind. The unlink-before-commit crash-safety ordering is a distinct property and
lives in tests/integration/test_remove_crash_safety.py.
"""

import pytest

from squads._errors import SquadsError

pytestmark = pytest.mark.anyio


async def test_remove_deletes_the_file_and_index_entry_without_shrinking_the_counter(svc):
    task = (await svc.create("task", "Oops")).item
    seq = task.sequence_id
    path = svc.paths.abspath(task.path)
    counter_before = (await svc.store.load()).counter

    res = await svc.remove_work_item(task.id, force=False)

    assert res.removed_id == task.id
    assert res.severed_refs == []
    assert not path.exists()
    db = await svc.store.load()
    assert seq not in db.items
    assert db.counter == counter_before


async def test_removed_sequence_number_is_never_reissued_even_after_repair(svc):
    task = (await svc.create("task", "Gone")).item
    removed_seq = task.sequence_id

    await svc.remove_work_item(task.id)
    await svc.repair()
    db_after = await svc.store.load()
    assert removed_seq not in db_after.items

    new_task = (await svc.create("task", "New")).item
    assert new_task.sequence_id > removed_seq


async def test_remove_refuses_on_incoming_refs_without_force(svc):
    task = (await svc.create("task", "Target")).item
    other = (await svc.create("task", "Referrer")).item
    await svc.add_ref(other.id, task.id)

    with pytest.raises(SquadsError, match=other.id):
        await svc.remove_work_item(task.id)
    assert (await svc.store.load()).get(task.id) is not None


async def test_remove_force_severs_every_incoming_ref(svc):
    target = (await svc.create("task", "T")).item
    a = (await svc.create("task", "A")).item
    b = (await svc.create("bug", "B")).item
    await svc.add_ref(a.id, target.id, kind="related")
    await svc.add_ref(b.id, target.id, kind="blocks")

    res = await svc.remove_work_item(target.id, force=True)

    assert sorted(res.severed_refs) == sorted([a.id, b.id])
    assert (await svc.get(a.id)).refs == []
    assert (await svc.get(b.id)).refs == []
    issues = await svc.check()
    assert not any("dangling" in i.message.lower() for i in issues)


async def test_remove_refuses_when_children_exist_even_with_force(svc):
    feat = (await svc.create("feature", "Parent")).item
    task = (await svc.create("task", "Child")).item
    await svc.link(task.id, feat.id)

    with pytest.raises(SquadsError, match=task.id):
        await svc.remove_work_item(feat.id, force=True)
    assert (await svc.store.load()).get(feat.id) is not None


async def test_remove_width_tolerant_ref_severing(svc):
    """A ref stored at a narrower (pre-repad) width is still found and severed."""
    from squads._index._resolver import item_file
    from squads._itemfile import update_frontmatter
    from squads._models._item import make_ref

    target = (await svc.create("bug", "Bug")).item
    referrer = (await svc.create("task", "Task")).item
    old_width_id = f"BUG-{target.sequence_id:04d}"  # narrower than the current default (6)

    async with svc.store.transaction() as db:
        r_item = db.get(referrer.id)
        assert r_item is not None
        r_item.refs = [make_ref(old_width_id, "related")]
        await update_frontmatter(item_file(svc.paths, r_item), r_item)

    res = await svc.remove_work_item(target.id, force=True)
    assert referrer.id in res.severed_refs
    assert (await svc.get(referrer.id)).refs == []
