"""Both bulk-rename verbs (`rename_type`/`rename_status`) snapshot every item on the board
before writing anything, so a mid-flight failure can restore the filesystem. That snapshot read
must report a stale indexed path cleanly -- even when the stale item isn't part of the verb's
own affected set -- rather than crash the whole verb on a raw `FileNotFoundError`.
"""

import pytest

from squads._errors import SquadsError
from squads._index._store import IndexStore

pytestmark = pytest.mark.anyio


async def _interrupt_a_title_changing_update(svc, monkeypatch, item_id: str) -> None:
    """Crash the index commit right after the physical rename + frontmatter rewrite land --
    the file is at its new path; the index still names the old one."""
    real_atomic_write = IndexStore._atomic_write

    async def _boom(self, db):
        raise OSError("simulated crash during the index commit")

    monkeypatch.setattr(IndexStore, "_atomic_write", _boom)
    try:
        with pytest.raises(OSError):
            await svc.update(item_id, title="renamed mid crash")
    finally:
        monkeypatch.setattr(IndexStore, "_atomic_write", real_atomic_write)


async def test_rename_status_fails_cleanly_when_an_unrelated_item_has_a_stale_path(
    svc, monkeypatch
):
    stale = (await svc.create("bug", "Original title")).item
    await _interrupt_a_title_changing_update(svc, monkeypatch, stale.id)

    target = (await svc.create("task", "Rename-status target")).item

    with pytest.raises(SquadsError, match=rf"{stale.id}.*repair"):
        await svc.rename_status("task", "Draft", "Ready")

    reloaded_target = await svc.get(target.id)
    assert reloaded_target.status == "Draft"  # nothing was written


async def test_rename_type_fails_cleanly_when_an_unrelated_item_has_a_stale_path(svc, monkeypatch):
    stale = (await svc.create("bug", "Original title")).item
    await _interrupt_a_title_changing_update(svc, monkeypatch, stale.id)

    target = (await svc.create("task", "Rename-type target")).item

    with pytest.raises(SquadsError, match=rf"{stale.id}.*repair"):
        await svc.rename_type("task", "bug")

    reloaded_target = await svc.get(target.id)
    assert reloaded_target.type == "task"  # nothing was written


async def test_both_verbs_work_again_after_repair(svc, monkeypatch):
    stale = (await svc.create("bug", "Original title")).item
    await _interrupt_a_title_changing_update(svc, monkeypatch, stale.id)

    await svc.repair()

    target = (await svc.create("task", "Rename target after repair")).item
    status_result = await svc.rename_status("task", "Draft", "Ready")
    assert status_result.renamed == 1
    reloaded = await svc.get(target.id)
    assert reloaded.status == "Ready"

    type_result = await svc.rename_type("task", "bug")
    assert type_result.renamed == 1
