"""`init --force` over a squad that already holds items, roles and skills rebuilds the index from
disk: nothing drops out of it, nothing is created twice, and new ids continue past the highest."""

import functools

import pytest

from _helpers import create_item, hold_lock, make_service
from squads._errors import IndexLockTimeoutError
from squads._index._resolver import item_file
from squads._index._store import IndexStore
from squads._services import _service as service

pytestmark = pytest.mark.anyio


async def _init(root):
    return await service.init(root=root, force=True)


async def test_a_second_init_over_a_fresh_squad_changes_nothing(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    paths = (await _init(tmp_path)).paths
    first = sorted(p.relative_to(tmp_path).as_posix() for p in paths.squad_dir.rglob("*.md"))

    paths = (await _init(tmp_path)).paths

    svc = make_service(paths)
    db = await svc.store.load()
    assert db.counter == 20
    assert (
        sorted(p.relative_to(tmp_path).as_posix() for p in paths.squad_dir.rglob("*.md")) == first
    )
    assert [i for i in await svc.check() if i.level in ("error", "warn")] == []


async def test_init_over_a_squad_holding_a_task_keeps_it_and_continues_the_ids(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = (await _init(tmp_path)).paths
    task = (await create_item(make_service(paths), "task", "Kept")).item

    paths = (await _init(tmp_path)).paths

    svc = make_service(paths)
    assert (await svc.get(task.id)).title == "Kept"
    roles = await svc.list_items(item_type="role")
    assert len(roles) == len({r.slug for r in roles}) == 8
    later = (await create_item(svc, "task", "After")).item
    assert later.sequence_id == task.sequence_id + 1


async def test_init_with_the_lock_held_fails_cleanly_and_leaves_the_index_as_it_was(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = (await _init(tmp_path)).paths
    await create_item(make_service(paths), "task", "Kept")
    before = paths.index_path.read_bytes()
    short = functools.partial(IndexStore, lock_timeout=1)
    monkeypatch.setattr("squads._services._service.IndexStore", short)
    monkeypatch.setattr("squads._services._base.IndexStore", short)
    holder = hold_lock(paths.lock_path, 3)
    try:
        with pytest.raises(IndexLockTimeoutError):
            await _init(tmp_path)
    finally:
        holder.wait()

    assert paths.index_path.read_bytes() == before


async def test_init_carries_an_unparseable_item_forward_as_repair_does(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = (await _init(tmp_path)).paths
    svc = make_service(paths)
    broken = (await create_item(svc, "task", "Broken")).item
    item_file(paths, broken).write_text("---\n: not [valid\n---\n", encoding="utf-8")

    paths = (await _init(tmp_path)).paths

    assert broken.id in {i.id for i in (await make_service(paths).store.load()).items.values()}
