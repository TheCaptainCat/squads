"""Regression pin for the latent misattribution risk: several `store.transaction()` calls
fired concurrently on one `IndexStore` (one event loop, real filelock + tmp dir, hence the
service-layer home alongside ``test_index_concurrency.py``) must never let one transaction's
reflog entry land in another's buffer.
"""

import anyio
import anyio.lowlevel
import pytest

from squads._index._reflog import read_lines, reflog_path
from squads._index._store import IndexStore

pytestmark = pytest.mark.anyio


async def test_concurrent_transactions_on_one_store_never_cross_attribute_reflog_entries(
    tmp_path,
):
    store = IndexStore(tmp_path / ".squads.json", tmp_path / ".squads.json.lock")
    store.create_empty("0.1.0")

    n = 8

    async def mutate(i: int) -> None:
        async with store.transaction() as db:
            _ = db
            # Yield control before AND after logging, so sibling tasks get a chance to run
            # (and, under the old shared-instance-attribute design, to clobber the active
            # context) while this task still holds the lock and has an op buffered.
            await anyio.lowlevel.checkpoint()
            store._log(  # pyright: ignore[reportPrivateUsage]
                "update", f"TASK-{i:06d}", {"i": i}
            )
            await anyio.lowlevel.checkpoint()

    async with anyio.create_task_group() as tg:
        for i in range(n):
            tg.start_soon(mutate, i)

    lines = await read_lines(reflog_path(tmp_path))
    assert len(lines) == n
    by_target = {ln.target: ln for ln in lines}
    assert set(by_target) == {f"TASK-{i:06d}" for i in range(n)}
    for i in range(n):
        assert by_target[f"TASK-{i:06d}"].delta == {"i": i}
