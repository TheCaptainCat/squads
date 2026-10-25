"""A write that waits on the index lock says so on stderr, and one that never gets the lock ends
in a clean error with nothing written.

The lock is held from a separate process, because the file lock is what excludes processes.
"""

import pytest

from _helpers import hold_lock
from squads._errors import IndexLockTimeoutError
from squads._index._store import IndexStore
from squads._workflow import bundled_spec

pytestmark = pytest.mark.anyio


def make_store(tmp_path, *, lock_timeout: float) -> IndexStore:
    store = IndexStore(
        tmp_path / ".squads.json",
        tmp_path / ".squads.json.lock",
        lock_timeout=lock_timeout,
        spec=bundled_spec(),
    )
    store.create_empty()
    return store


async def test_a_free_lock_is_taken_without_a_notice(tmp_path, capsys):
    store = make_store(tmp_path, lock_timeout=3)
    async with store.transaction() as db:
        db.allocate_id("task", prefix="TASK")
    assert "waiting for the index lock" not in capsys.readouterr().err


async def test_a_lock_released_during_the_wait_is_announced_then_taken(tmp_path, capsys):
    store = make_store(tmp_path, lock_timeout=8)
    holder = hold_lock(store.lock_path, 2.5)
    try:
        async with store.transaction() as db:
            db.allocate_id("task", prefix="TASK")
    finally:
        holder.wait()
    assert f"waiting for the index lock {store.lock_path}" in capsys.readouterr().err
    assert (await store.load()).counter == 1


async def test_a_lock_held_past_the_timeout_fails_cleanly_and_leaves_the_store_usable(
    tmp_path, capsys
):
    store = make_store(tmp_path, lock_timeout=2)
    holder = hold_lock(store.lock_path, 4)
    try:
        with pytest.raises(IndexLockTimeoutError) as raised:
            async with store.transaction() as db:
                db.allocate_id("task", prefix="TASK")
    finally:
        holder.wait()
    message = str(raised.value)
    assert str(store.lock_path) in message
    assert "nothing was written" in message
    assert "retry" in message
    assert (await store.load()).counter == 0
    assert "waiting for the index lock" in capsys.readouterr().err

    # The in-process locks were released: the next write goes through.
    async with store.transaction() as db:
        db.allocate_id("task", prefix="TASK")
    assert (await store.load()).counter == 1
