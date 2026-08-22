"""The active-transaction handle is a task-local, store-scoped binding: absent outside a
transaction, present only while the owning store holds its locks, restored (not merely
cleared) on every exit path, invisible to a different store instance, and built from a
single in-lock load.
"""

import anyio
import pytest

from squads._index._reflog import read_lines, reflog_path
from squads._index._store import (
    IndexStore,
    _transaction_ctx_for,
)

pytestmark = pytest.mark.anyio


def _make_store(tmp_path, name: str = "squad") -> IndexStore:
    squad_dir = tmp_path / name
    squad_dir.mkdir()
    store = IndexStore(squad_dir / ".squads.json", squad_dir / ".squads.json.lock")
    store.create_empty("0.1.0")
    return store


async def test_binding_is_absent_before_and_after_a_transaction(tmp_path):
    store = _make_store(tmp_path)
    assert _transaction_ctx_for(store) is None

    async with store.transaction() as db:
        _ = db

    assert _transaction_ctx_for(store) is None


async def test_binding_is_present_only_while_the_transaction_is_open(tmp_path):
    store = _make_store(tmp_path)

    async with store.transaction() as db:
        _ = db
        assert _transaction_ctx_for(store) is not None


async def test_binding_is_restored_when_an_exception_escapes_the_body(tmp_path):
    store = _make_store(tmp_path)

    with pytest.raises(RuntimeError):
        async with store.transaction() as db:
            _ = db
            raise RuntimeError("boom")

    assert _transaction_ctx_for(store) is None


async def test_binding_is_restored_when_the_transaction_is_cancelled(tmp_path):
    store = _make_store(tmp_path)
    entered = anyio.Event()

    async def _hold_transaction() -> None:
        async with store.transaction() as db:
            _ = db
            entered.set()
            await anyio.sleep_forever()

    with anyio.move_on_after(10) as scope:
        async with anyio.create_task_group() as tg:
            tg.start_soon(_hold_transaction)
            await entered.wait()
            scope.cancel()

    assert _transaction_ctx_for(store) is None


async def test_a_nested_transaction_on_a_different_store_restores_the_outer_binding(tmp_path):
    """Only one ambient slot exists per task, so while a different store's transaction is
    nested inside, it is the currently-bound one; the outer store's own ``log`` calls
    correctly see "no transaction of mine is active right now" (safe no-op, never routed
    into the inner store's buffer — the same guard ``_transaction_ctx_for`` applies to any
    foreign-store call). Once the inner transaction unwinds, the outer binding is
    *restored* to the very same context object, not cleared to ``None``.
    """
    outer_store = _make_store(tmp_path, "outer")
    inner_store = _make_store(tmp_path, "inner")

    async with outer_store.transaction() as outer_db:
        _ = outer_db
        outer_ctx = _transaction_ctx_for(outer_store)
        assert outer_ctx is not None

        async with inner_store.transaction() as inner_db:
            _ = inner_db
            assert _transaction_ctx_for(inner_store) is not None
            # the inner binding is now the ambient one; the outer store safely no-ops
            # rather than misattributing into the inner store's buffer.
            assert _transaction_ctx_for(outer_store) is None

        assert _transaction_ctx_for(inner_store) is None
        # restored, not cleared: the outer binding is exactly the same context again.
        assert _transaction_ctx_for(outer_store) is outer_ctx


async def test_log_call_with_no_open_transaction_is_a_silent_noop(tmp_path):
    store = _make_store(tmp_path)

    store.log("update", "TASK-000001", {"title": ["Old", "New"]})  # no exception

    lines = await read_lines(reflog_path(store.index_path.parent))
    assert lines == []


async def test_log_call_on_a_different_store_instance_does_not_leak_into_the_open_transaction(
    tmp_path,
):
    store_a = _make_store(tmp_path, "squad-a")
    store_b = _make_store(tmp_path, "squad-b")

    async with store_a.transaction() as db:
        _ = db
        store_b.log("update", "TASK-000002", {"title": ["Old", "New"]})
        ctx_a = _transaction_ctx_for(store_a)
        assert ctx_a is not None
        assert ctx_a.reflog_ops == []  # not routed into A's buffer

    lines_a = await read_lines(reflog_path(store_a.index_path.parent))
    lines_b = await read_lines(reflog_path(store_b.index_path.parent))
    assert lines_a == []
    assert lines_b == []  # store B never had an open transaction of its own


async def test_a_log_call_on_the_owning_store_still_buffers_and_flushes(tmp_path):
    store = _make_store(tmp_path)

    async with store.transaction() as db:
        _ = db
        store.log("update", "TASK-000003", {"title": ["Old", "New"]})

    lines = await read_lines(reflog_path(store.index_path.parent))
    matching = [ln for ln in lines if ln.op == "update" and ln.target == "TASK-000003"]
    assert len(matching) == 1


async def test_transaction_loads_the_index_exactly_once(tmp_path, monkeypatch):
    """``transaction()``'s in-lock load goes through ``_read_from_disk`` directly, never
    ``load()`` — the load-bearing line that keeps a request-scoped read snapshot from ever
    reaching a commit (see ``squads._index._store.read_scope``)."""
    store = _make_store(tmp_path)
    calls = 0
    original_read = IndexStore._read_from_disk

    async def _counting_read(self, *, validate_vocab):
        nonlocal calls
        calls += 1
        return await original_read(self, validate_vocab=validate_vocab)

    monkeypatch.setattr(IndexStore, "_read_from_disk", _counting_read)

    async with store.transaction() as db:
        _ = db

    assert calls == 1
