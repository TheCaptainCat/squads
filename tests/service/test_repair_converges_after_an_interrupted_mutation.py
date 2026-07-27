"""The markdown-ahead skew a killed process must always leave, in each direction of change:
raising from inside a transaction body strictly after the markdown write (but before the
index `os.replace`) reproduces the crash window without killing a process. In every direction
the file is left ahead of the index, never behind, and `sq repair` converges on the file's
state.
"""

import pytest

from squads._index._resolver import item_file
from squads._index._store import IndexStore
from squads._itemfile import read_frontmatter

pytestmark = pytest.mark.anyio


def _crash_the_commit(mp: pytest.MonkeyPatch) -> None:
    """Makes the NEXT index commit raise -- every markdown write inside the transaction body
    already ran (and is durable) by the time this fires.

    Takes a scoped `MonkeyPatch` instance (never the test's shared `monkeypatch` fixture) so
    the patch is gone the moment the `with` block exits, with no risk of an early `.undo()`
    also rolling back something unrelated a shared instance owns (e.g. `project`'s `chdir`).
    """

    def _raise(self, db):
        raise OSError("simulated crash during the index commit")

    mp.setattr(IndexStore, "_atomic_write", _raise)


async def test_create_survives_a_crash_between_the_file_write_and_the_index_commit(svc):
    with pytest.MonkeyPatch.context() as mp:
        _crash_the_commit(mp)
        with pytest.raises(OSError, match="simulated crash"):
            await svc.create("task", "Interrupted create")

    # The file was written (create's own write_new runs inside the transaction body) but the
    # index commit never happened.
    on_disk = list((svc.paths.squad_dir / "tasks").glob("TASK-*.md"))
    assert len(on_disk) == 1
    fid = read_frontmatter(path=on_disk[0]).get("id")
    assert fid is not None
    assert (await svc.store.load()).get(fid) is None  # not indexed yet

    repaired = await svc.repair()
    assert repaired.db.get(fid) is not None
    item = await svc.get(fid)
    assert item.title == "Interrupted create"


async def test_a_status_update_survives_a_crash_between_the_file_write_and_the_index_commit(svc):
    task = (await svc.create("task", "Interrupted update")).item
    await svc.set_status(task.id, "Ready")

    with pytest.MonkeyPatch.context() as mp:
        _crash_the_commit(mp)
        with pytest.raises(OSError, match="simulated crash"):
            await svc.set_status(task.id, "InProgress")

    path = item_file(svc.paths, task)
    assert read_frontmatter(path=path)["status"] == "InProgress"  # file: ahead
    assert (await svc.store.load()).items[task.sequence_id].status == "Ready"  # index: behind

    repaired = await svc.repair()
    assert repaired.db.items[task.sequence_id].status == "InProgress"  # adopts the file's value
    item = await svc.get(task.id)
    assert item.status == "InProgress"


async def test_removal_survives_a_crash_between_the_unlink_and_the_index_commit(svc):
    task = (await svc.create("task", "Interrupted remove")).item
    path = item_file(svc.paths, task)

    with pytest.MonkeyPatch.context() as mp:
        _crash_the_commit(mp)
        with pytest.raises(OSError, match="simulated crash"):
            await svc.remove_work_item(task.id)

    assert not path.exists()  # file: gone
    assert task.sequence_id in (await svc.store.load()).items  # index: still has the orphan

    repaired = await svc.repair()
    assert task.sequence_id not in repaired.db.items
    assert task.id in repaired.missing_ids


async def test_purging_a_roster_item_survives_a_crash_between_the_unlink_and_the_index_commit(svc):
    """Pins the ordering fix: `remove_item(purge=True)` used to unlink the .md AFTER the
    transaction committed -- the lossy direction, where a crash leaves the index gone but the
    file surviving, and `sq repair` would resurrect the removed item. It now unlinks inside the
    transaction body, same direction as remove_work_item above."""
    op = await svc.add_operator("Temp Operator")
    path = item_file(svc.paths, op)

    with pytest.MonkeyPatch.context() as mp:
        _crash_the_commit(mp)
        with pytest.raises(OSError, match="simulated crash"):
            await svc.remove_item(op.id, purge=True)

    assert not path.exists()  # file: gone (unlinked inside the transaction body)
    assert op.sequence_id in (await svc.store.load()).items  # index: still has the orphan

    repaired = await svc.repair()
    assert op.sequence_id not in repaired.db.items  # repair drops the orphan, never resurrects


async def test_retype_survives_a_crash_between_the_file_move_and_the_index_commit(svc):
    task = (await svc.create("task", "Interrupted retype")).item
    old_id, old_path = task.id, item_file(svc.paths, task)

    with pytest.MonkeyPatch.context() as mp:
        _crash_the_commit(mp)
        with pytest.raises(OSError, match="simulated crash"):
            await svc.retype(task.id, "bug")

    # The file already moved to its new (bug) path/id inside the transaction body.
    assert not old_path.exists()
    on_disk = list((svc.paths.squad_dir / "bugs").glob("BUG-*.md"))
    assert len(on_disk) == 1
    new_fid = read_frontmatter(path=on_disk[0]).get("id")
    assert new_fid is not None

    # The index never committed: still has the old entry at the old id/type.
    stale = (await svc.store.load()).items[task.sequence_id]
    assert stale.id == old_id
    assert stale.type == "task"

    repaired = await svc.repair()
    reindexed = repaired.db.items[task.sequence_id]
    assert reindexed.id == new_fid
    assert reindexed.type == "bug"
