"""Concurrent id allocation is exclusion-safe across both real OS threads and coroutines
sharing one event loop — needs a real filelock + tmp dir, so it lives at the service layer
rather than unit.
"""

import anyio
import anyio.lowlevel
import anyio.to_thread
import pytest

from squads._index._store import IndexStore

pytestmark = pytest.mark.anyio


async def test_concurrent_threads_allocate_distinct_ids(tmp_path):
    """Each thread runs its own event loop; thread-level parallelism + file-lock exclusion
    must still never hand out a duplicate id."""
    from concurrent.futures import ThreadPoolExecutor

    store = IndexStore(tmp_path / ".squads.json", tmp_path / ".squads.json.lock")
    store.create_empty("0.1.0")

    def alloc(_: int) -> str:
        async def _do() -> str:
            async with store.transaction() as db:
                return db.allocate_id("task")

        return anyio.run(_do)

    with ThreadPoolExecutor(max_workers=8) as ex:
        ids = list(ex.map(alloc, range(50)))
    assert len(set(ids)) == 50
    assert (await store.load()).counter == 50


async def test_concurrent_coroutines_on_one_loop_allocate_distinct_ids(tmp_path):
    """Forcing the thread limiter to a single token makes a single-layer (file-lock-only)
    implementation fail deterministically — every coroutine's acquire would land on the one
    reused worker thread and see the file lock as a reentrant no-op."""
    store = IndexStore(tmp_path / ".squads.json", tmp_path / ".squads.json.lock")
    store.create_empty("0.1.0")

    n = 8
    ids: list[str] = []

    limiter = anyio.to_thread.current_default_thread_limiter()
    original_tokens = limiter.total_tokens
    limiter.total_tokens = 1
    try:

        async def allocate() -> None:
            async with store.transaction() as db:
                ids.append(db.allocate_id("task"))
                await anyio.lowlevel.checkpoint()

        async with anyio.create_task_group() as tg:
            for _ in range(n):
                tg.start_soon(allocate)
    finally:
        limiter.total_tokens = original_tokens

    assert len(set(ids)) == n, f"duplicate ids allocated: {ids}"
    assert (await store.load()).counter == n
