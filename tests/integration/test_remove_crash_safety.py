"""`remove_work_item`'s crash-ordering guarantee: the .md unlink happens *inside* the
transaction, before the index commit — so a crash between the two can never resurrect a
removed item via a later `sq repair`. Contrast: unlinking *after* the commit would let a crash
leave the .md surviving while the index-entry is already gone, and repair would re-adopt it.
"""

import pytest

from squads._index._store import IndexStore

pytestmark = pytest.mark.anyio


async def test_the_file_is_gone_before_a_crashed_commit_so_repair_never_resurrects_it(
    svc, monkeypatch
):
    task = (await svc.create("task", "AtomicCheck")).item
    seq = task.sequence_id
    path = svc.paths.abspath(task.path)

    original_atomic_write = IndexStore._atomic_write  # pyright: ignore[reportPrivateUsage]

    def _crash_on_write(self, db):
        raise OSError("simulated crash during index commit")

    monkeypatch.setattr(IndexStore, "_atomic_write", _crash_on_write)

    with pytest.raises(OSError, match="simulated crash"):
        await svc.remove_work_item(task.id)

    # The .md is already gone -- unlink ran before the failed commit.
    assert not path.exists()
    # The on-disk index was never rewritten -- the commit raised.
    assert seq in (await svc.store.load()).items

    monkeypatch.setattr(IndexStore, "_atomic_write", original_atomic_write)

    await svc.repair()  # scans .md files: none for seq -> it is not resurrected
    assert seq not in (await svc.store.load()).items
