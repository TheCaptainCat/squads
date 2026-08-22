"""The request-scoped read cache (``squads._index._store.read_scope``): opt-in and
absent-by-default, keyed on store instance identity like ``_active_transaction``, and never
consulted by the one path invariant 8 forbids it from ever reaching — ``transaction()``'s own
in-lock load.

Uses bare ``IndexStore`` instances against ``tmp_path`` directly, exactly like
``tests/unit/test_index_allocation.py`` and ``tests/unit/test_transaction_context_scoping.py`` —
the store's own read/cache plumbing is what is under test here, not a whole squad.
"""

import pytest

from squads._index._store import IndexStore, _read_scope, read_scope

pytestmark = pytest.mark.anyio


def _make_store(tmp_path, name: str = "squad") -> IndexStore:
    squad_dir = tmp_path / name
    squad_dir.mkdir()
    store = IndexStore(squad_dir / ".squads.json", squad_dir / ".squads.json.lock")
    store.create_empty("0.1.0")
    return store


async def test_load_without_a_scope_always_rereads_disk(tmp_path):
    """Absent a scope, ``load()`` behaves exactly as it always has: no cache, so a load after
    a commit always observes the commit."""
    store = _make_store(tmp_path)
    async with store.transaction() as db:
        db.counter = 1
    assert (await store.load()).counter == 1

    async with store.transaction() as db:
        db.counter = 2
    assert (await store.load()).counter == 2


async def test_load_within_a_scope_serves_one_snapshot_to_every_caller(tmp_path):
    """Two ``load()`` calls inside one open scope, with nothing invalidating it between them,
    get back the very same object — one disk read shared by the whole invocation."""
    store = _make_store(tmp_path)

    with read_scope():
        first = await store.load()
        second = await store.load()
        assert first is second


async def test_transaction_never_serves_a_stale_snapshot_over_a_newer_index(tmp_path):
    """Invariant 8, exercised directly. Two ``IndexStore``s legitimately address one squad
    directory (the same configuration the module docstring already allows for ``sq repair``
    and tests): one holds a read scope with a now-stale snapshot; the other commits a change
    on disk that the first store's own scope entry is never told about. A ``transaction()``
    opened on the first store afterwards must still see the second store's committed change —
    if it instead served the stale scoped snapshot, committing on top of it would silently
    revert the second store's change, the one skew direction the durability model forbids.

    This is the falsification the design owes: if ``transaction()`` read through the scope
    instead of always calling ``_read_from_disk`` directly, this test goes red.
    """
    squad_dir = tmp_path / "squad"
    squad_dir.mkdir()
    index_path = squad_dir / ".squads.json"
    lock_path = squad_dir / ".squads.json.lock"
    store_a = IndexStore(index_path, lock_path)
    store_a.create_empty("0.1.0")
    store_b = IndexStore(index_path, lock_path)

    with read_scope():
        primed = await store_a.load()
        assert primed.counter == 0

        # store_b's commit is invisible to store_a's own scope entry — a different store
        # instance, exactly the identity-keyed boundary ``_ReadScope`` draws.
        async with store_b.transaction() as db:
            db.counter = 7

        async with store_a.transaction() as db:
            assert db.counter == 7, "transaction() must read disk, not the stale scope snapshot"
            db.counter = 8

    on_disk = await store_a.load()
    assert on_disk.counter == 8, "store_b's commit must survive, not be reverted"


async def test_scope_is_invalidated_after_a_commit_so_a_later_read_sees_the_mutation(tmp_path):
    """Break the invalidation and this goes red: a read after a committed mutation in the
    same invocation must never report pre-mutation state."""
    store = _make_store(tmp_path)

    with read_scope():
        first = await store.load()
        assert first.counter == 0

        async with store.transaction() as db:
            db.counter = 1

        second = await store.load()
        assert second.counter == 1


async def test_overwrite_also_invalidates_the_scope(tmp_path):
    """``overwrite()`` (``sq repair``'s whole-index replacement) invalidates the same way as
    ``transaction()`` — a read afterwards in the same invocation must see the replacement."""
    store = _make_store(tmp_path)

    with read_scope():
        first = await store.load()
        assert first.counter == 0

        replacement = first.model_copy(deep=True)
        replacement.counter = 9
        await store.overwrite(replacement)

        second = await store.load()
        assert second.counter == 9


async def test_load_fresh_bypasses_the_scope_in_both_directions(tmp_path):
    """``fresh=True`` neither consults nor fills the scope — required for the caller whose
    contract is "re-read the index right now" (``_confirm_cross_source``'s ``sq check``
    false-positive suppression). Remove the bypass and this goes red: the confirm round would
    serve a stale pre-scan snapshot instead of observing a concurrent commit.
    """
    squad_dir = tmp_path / "squad"
    squad_dir.mkdir()
    index_path = squad_dir / ".squads.json"
    lock_path = squad_dir / ".squads.json.lock"
    store_a = IndexStore(index_path, lock_path)
    store_a.create_empty("0.1.0")
    store_b = IndexStore(index_path, lock_path)

    with read_scope():
        cached = await store_a.load()
        assert cached.counter == 0

        # A concurrent process's commit through a different store instance — store_a's own
        # scope entry is untouched by it, exactly as in the transaction test above.
        async with store_b.transaction() as db:
            db.counter = 5

        fresh = await store_a.load(fresh=True)
        assert fresh.counter == 5, "fresh=True must bypass the stale cached entry"

        still_cached = await store_a.load()
        assert still_cached.counter == 0, "fresh=True must not have filed its answer either"


async def test_validate_vocab_false_neither_consults_nor_fills_the_scope(tmp_path):
    """The recovery read (``sq repair``'s pre-rebuild load) never touches the scope in either
    direction — filing an unvalidated db in a shared slot would let a later validating caller
    in the same invocation skip a fail-closed check."""
    store = _make_store(tmp_path)

    with read_scope():
        unvalidated = await store.load(validate_vocab=False)
        assert unvalidated.counter == 0

        async with store.transaction() as db:
            db.counter = 3

        # A validating load fills its own slot fresh from disk — never served the
        # unvalidated read that came before it.
        validated = await store.load()
        assert validated.counter == 3

        # And the unvalidated path itself always reads disk directly, cache or not.
        still_unvalidated = await store.load(validate_vocab=False)
        assert still_unvalidated.counter == 3


async def test_scope_survives_a_raising_transaction_so_a_later_read_sees_a_concurrent_commit(
    tmp_path,
):
    """The raise half of "commit or raise, no second clause": a transaction body that raises
    before ``_atomic_write`` is ever reached must still drop this store's scoped snapshot, so a
    read afterwards in the same invocation observes a concurrent committer's write rather than
    the stale pre-raise snapshot — and not the value the raising transaction attempted to
    write, since that mutation was never persisted.

    Break the invalidation so it only runs on the success path (e.g. move the
    ``scope.snapshots.pop`` after ``_atomic_write``, or wrap only the happy path in the
    ``finally``) and this goes red.
    """
    squad_dir = tmp_path / "squad"
    squad_dir.mkdir()
    index_path = squad_dir / ".squads.json"
    lock_path = squad_dir / ".squads.json.lock"
    store_a = IndexStore(index_path, lock_path)
    store_a.create_empty("0.1.0")
    store_b = IndexStore(index_path, lock_path)

    with read_scope():
        primed = await store_a.load()
        assert primed.counter == 0

        with pytest.raises(RuntimeError, match="boom"):
            async with store_a.transaction() as db:
                db.counter = 42
                raise RuntimeError("boom")

        # An unrelated commit through a second store instance on the same directory — visible
        # to store_a's own scope entry only if the raise above dropped it.
        async with store_b.transaction() as db:
            db.counter = 99

        after = await store_a.load()
        assert after.counter != primed.counter, "must not be the stale pre-transaction snapshot"
        assert after.counter != 42, "must not be the raising transaction's attempted write"
        assert after.counter == 99, "must be store_b's committed value"


async def test_scope_context_closes_after_every_invocation_success_or_error(tmp_path):
    """The scope's own binding, not just its contents: bound while a ``read_scope()`` block is
    open, and unbound again the moment it closes — on both a normal exit and an exception
    exit — so a later invocation in the same process never inherits a snapshot left behind by
    the one before it.

    This guarantee currently rests on Click's ``call_on_close`` contract in the real CLI (see
    ``enter_read_scope``'s docstring), not on anything this module enforces by itself; pinned
    here anyway because a regression in it would otherwise be silent.
    """
    store = _make_store(tmp_path)

    assert _read_scope.get() is None, "no scope bound before any invocation has opened one"

    with read_scope():
        assert _read_scope.get() is not None
        await store.load()

    assert _read_scope.get() is None, "scope must not survive a normal exit"

    with pytest.raises(RuntimeError, match="boom"), read_scope():
        assert _read_scope.get() is not None
        raise RuntimeError("boom")

    assert _read_scope.get() is None, "scope must not survive an error exit"

    # A later "invocation" opens a fresh, empty scope — no snapshot inherited from the one
    # above, even though it loaded the very same store.
    with read_scope():
        scope = _read_scope.get()
        assert scope is not None
        assert store not in scope.snapshots
