"""A competing file lock on the index propagates as a clean, catchable timeout."""

import pytest
from filelock import FileLock, Timeout

from squads._index._store import IndexStore

pytestmark = pytest.mark.anyio


async def test_a_held_lock_forces_timeout_through_the_async_transaction(tmp_path):
    store = IndexStore(tmp_path / ".squads.json", tmp_path / ".squads.json.lock")
    store.create_empty("0.1.0")

    competing = FileLock(str(tmp_path / ".squads.json.lock"), timeout=0)
    competing.acquire()
    try:
        fast_store = IndexStore(
            tmp_path / ".squads.json", tmp_path / ".squads.json.lock", lock_timeout=0.1
        )
        with pytest.raises(Timeout):
            async with fast_store.transaction() as db:
                _ = db  # pragma: no cover — acquire must fail before yielding
    finally:
        competing.release()
