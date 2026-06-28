"""Locked, atomic read-modify-write access to ``<squad-dir>/.squads.json``.

The single global counter and all item metadata live here. Every mutation goes through a
``transaction()`` guarded by a three-layer lock (ADR-000153 Decision 2):

- **Layer 1 — per-loop ``anyio.Lock``** (taken first): serialises coroutines on one event
  loop. ``anyio.Lock`` binds to the loop it is first used on, so locks are cached per
  running-loop id; the cache is guarded by a ``threading.Lock`` for cross-thread safety.
- **Layer 2 — ``_proc_mutex`` (``threading.Lock``)**: only one OS thread per process is ever
  in the file-lock section (covers multi-loop/multi-thread).
- **Layer 3 — ``filelock.FileLock(thread_local=False)``**: cross-process exclusion.
  ``thread_local=False`` is safe because Layer 2 guarantees single-threaded entry.

Lock order is always Layer 1 → 2 → 3; release reverse. Every acquire is in ``try/finally`` so
nothing leaks on exception/cancellation/``filelock.Timeout``. Commits are atomic ``os.replace``
so concurrent ``sq`` invocations never corrupt the file or collide on IDs.
"""

import asyncio
import contextlib
import os
import sys
import threading
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import anyio
from filelock import FileLock
from pydantic import ValidationError

from squads import _aio
from squads._errors import SquadsError
from squads._models._index import SquadsDB


def _validate_item_vocab(db: SquadsDB) -> None:
    """Validate every item's ``type``, ``status``, and sub-entity statuses against the
    loaded WorkflowSpec singleton.

    Called from :meth:`IndexStore.load` (ADR-000232 §1 / TASK-000235 F1/F5).  A corrupt or
    hand-edited index entry with an unknown type, status, or sub-entity status raises a
    clean :class:`SquadsError` rather than silently indexing and crashing downstream with a
    raw ``KeyError`` or ``ValueError``.

    Import is deferred (inside the function body) to avoid creating an import cycle:
    ``_index._store`` → ``_workflow`` → (no dependency on ``_index``).
    """
    # Lazy import: _workflow loads its singleton on first import; that is fine because
    # the CLI root callback always runs before any load().  Tests that construct an
    # IndexStore directly also import _workflow transitively before reaching this point.
    from squads._workflow import _DEFAULT_SPEC  # pyright: ignore[reportPrivateUsage]

    known_types: frozenset[str] = frozenset(_DEFAULT_SPEC.items)
    known_statuses: frozenset[str] = frozenset(_DEFAULT_SPEC.statuses)

    for item in db.items.values():
        if item.type not in known_types:
            raise SquadsError(
                f"item {item.id} has unknown type {item.type!r}; "
                f"run `sq repair` if the index is stale, or check the frontmatter"
            )
        if item.status not in known_statuses:
            raise SquadsError(
                f"item {item.id} has unknown status {item.status!r}; "
                f"run `sq repair` if the index is stale, or check the frontmatter"
            )
        # F5: sub-entity statuses share the same vocabulary — validate each one too.
        for sub in item.subentities:
            if sub.status not in known_statuses:
                raise SquadsError(
                    f"item {item.id} sub-entity {sub.local_id} has unknown status "
                    f"{sub.status!r}; run `sq repair` if the index is stale, or "
                    f"check the frontmatter"
                )


@dataclass
class _ReflogOp:
    """A reflog entry buffered during a transaction, flushed after the commit."""

    op: str
    target: str
    delta: dict[str, Any]


@dataclass
class _TransactionCtx:
    """Transaction context: the :class:`SquadsDB` plus :attr:`reflog_ops` buffered for
    post-commit append (flushed after ``os.replace``, while the file lock is held)."""

    db: SquadsDB
    reflog_ops: list[_ReflogOp] = field(default_factory=list[_ReflogOp])

    def log(self, op: str, target: str, delta: dict[str, Any]) -> None:
        """Buffer one reflog entry for post-commit append."""
        self.reflog_ops.append(_ReflogOp(op=op, target=target, delta=delta))


class IndexStore:
    def __init__(self, index_path: Path, lock_path: Path, *, lock_timeout: float = 10.0):
        self.index_path = index_path
        self.lock_path = lock_path
        self._lock_timeout = lock_timeout
        # Layer 3 — cross-process file lock. thread_local=False is safe because Layer 2
        # guarantees single-threaded entry, so its shared-state race is unreachable.
        self._lock = FileLock(str(lock_path), timeout=lock_timeout, thread_local=False)
        # Layer 2 — proc-mutex: one OS thread in the file-lock section at a time.
        self._proc_mutex: threading.Lock = threading.Lock()
        # Layer 1 — per-running-loop anyio.Lock cache (one instance shared across loops
        # deadlocks); _loop_locks_guard serialises cache updates.
        self._loop_locks: dict[int, anyio.Lock] = {}
        self._loop_locks_guard: threading.Lock = threading.Lock()

    def _loop_lock(self) -> anyio.Lock:
        """Return the ``anyio.Lock`` for the running event loop, creating it on first use."""
        loop = asyncio.get_running_loop()
        loop_id = id(loop)
        with self._loop_locks_guard:
            if loop_id not in self._loop_locks:
                self._loop_locks[loop_id] = anyio.Lock()
            return self._loop_locks[loop_id]

    # ------------------------------------------------------------------ create / read
    def create_empty(self, squads_version: str) -> SquadsDB:
        """Write a fresh empty index (sync; used by tests and one-shot bootstrap paths).

        Prefer :meth:`create_empty_threaded` on the async service path (``init``/``adopt``).
        """
        db = SquadsDB(squads_version=squads_version, counter=0)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write_sync(db)
        return db

    async def create_empty_threaded(self, squads_version: str) -> SquadsDB:
        """Write a fresh empty index on a worker thread (async; used by ``init``/``adopt``)."""
        db = SquadsDB(squads_version=squads_version, counter=0)
        await _aio.mkdir(self.index_path.parent, parents=True, exist_ok=True)
        await self._atomic_write(db)
        return db

    def exists(self) -> bool:
        return self.index_path.is_file()

    async def load(self) -> SquadsDB:
        """Read without locking, on a worker thread — for queries (list/show); writes use
        :meth:`transaction`.

        If the stored counter trails the max item sequence (e.g. a hand-edit), it is raised
        *in memory* so the next allocation can't reuse a number; the corrected value only
        reaches disk on the next ``transaction()`` save (or ``sq repair``). Allocation still
        happens only inside ``transaction()`` (invariant 2).
        """
        try:
            raw = await _aio.read_text(self.index_path)
            db = SquadsDB.model_validate_json(raw)
        except ValidationError as exc:
            raise SquadsError(
                f"corrupt index {self.index_path.name} ({exc.error_count()} problem(s)); "
                "run `sq repair` to rebuild it from the markdown files"
            ) from exc
        max_seq = max((item.sequence_id for item in db.items.values()), default=0)
        if db.counter < max_seq:
            db.counter = max_seq
        _validate_item_vocab(db)
        return db

    # ------------------------------------------------------------------ transaction
    @contextlib.asynccontextmanager
    async def transaction(self) -> AsyncGenerator[SquadsDB]:
        """Load under the lock, yield the DB to mutate, then atomically write it back.

        Three-layer lock taken Layer 1 → 2 → 3 (ADR-000153 Decision 2); Layers 2/3 via
        ``_aio.to_thread``. ``filelock.Timeout`` from the Layer 3 acquire propagates unchanged
        with no lock leak (inner ``finally`` no-ops, outer releases the proc-mutex, the
        ``async with`` releases the per-loop lock).

        After the ``os.replace`` commits, buffered reflog ops are appended while still holding
        all locks (ADR-000117 §1 — strictly after commit). A failed append only warns; it never
        rolls back the committed mutation. If the body raises, nothing is written.
        """
        from squads import _actor as actor
        from squads import _clock as clock
        from squads._index._reflog import append_line, reflog_path

        ctx = _TransactionCtx(db=await self.load())
        self._current_ctx: _TransactionCtx | None = ctx  # type: ignore[attr-defined]
        # Layer 1 first — serialises concurrent coroutines on this event loop.
        async with self._loop_lock():
            # Layer 2 — acquire proc-mutex on a worker thread (off the event loop).
            await _aio.to_thread(self._proc_mutex.acquire)
            try:
                # Layer 3 — acquire file lock on a worker thread, inside the proc-mutex.
                # filelock.Timeout propagates here unchanged; inner finally is a no-op.
                await _aio.to_thread(self._lock.acquire)
                try:
                    ctx.db = await self.load()
                    yield ctx.db
                    await self._atomic_write(ctx.db)

                    # Reflog append: strictly after os.replace, inside all locks (ADR-000117
                    # §1). Guarded so any error degrades to a warning — never surfaces from an
                    # already-committed mutation (ADR-000153 Decision 2, never-raise contract).
                    if ctx.reflog_ops:
                        try:
                            rpath = reflog_path(self.index_path.parent)
                            ts = clock.iso(clock.now())
                            act = actor.current_actor()
                            sid, psid = actor.current_session()
                            for entry in ctx.reflog_ops:
                                await append_line(
                                    rpath,
                                    ts=ts,
                                    actor=act,
                                    op=entry.op,
                                    target=entry.target,
                                    delta=entry.delta,
                                    session_id=sid,
                                    parent_session_id=psid,
                                )
                        except Exception as exc:  # never fail a committed mutation
                            print(
                                f"[squads reflog] warning: reflog append failed: {exc}",
                                file=sys.stderr,
                            )
                finally:
                    await _aio.to_thread(self._lock.release)  # Layer 3 released first
                    self._current_ctx = None  # type: ignore[attr-defined]
            finally:
                await _aio.to_thread(self._proc_mutex.release)  # Layer 2; Layer 1 by async-with

    def _log(self, op: str, target: str, delta: dict[str, Any]) -> None:
        """Buffer a reflog entry on the active transaction context (no-op outside one), so the
        op is captured where the change is known and emitted after the commit."""
        ctx: _TransactionCtx | None = getattr(self, "_current_ctx", None)
        if ctx is not None:
            ctx.log(op, target, delta)

    async def overwrite(self, db: SquadsDB) -> None:
        """Replace the whole index under the three-layer lock (used by ``sq repair``), with the
        same Layer-1-first ordering as :meth:`transaction` (ADR-000153 Decision 2)."""
        async with self._loop_lock():
            await _aio.to_thread(self._proc_mutex.acquire)
            try:
                await _aio.to_thread(self._lock.acquire)
                try:
                    await self._atomic_write(db)
                finally:
                    await _aio.to_thread(self._lock.release)
            finally:
                await _aio.to_thread(self._proc_mutex.release)

    # ------------------------------------------------------------------ internals
    def _atomic_write_sync(self, db: SquadsDB) -> None:
        """Sync atomic write — for ``create_empty`` (bootstrap, single-process path)."""
        tmp = self.index_path.with_suffix(f".json.{os.getpid()}.{threading.get_ident()}.tmp")
        # fsync the write handle — Windows raises OSError [Errno 9] on a read-only handle.
        with tmp.open("w", encoding="utf-8") as fh:
            fh.write(db.to_json() + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        tmp.replace(self.index_path)

    async def _atomic_write(self, db: SquadsDB) -> None:
        """Async atomic write: tmp-open/write/fsync/replace runs as ONE thread hop.

        No ``await`` between ``os.fsync`` and ``tmp.replace`` — they share one sync closure so
        no coroutine interleaves between the durability barrier and the rename (ADR-000153
        Decision 4).
        """
        index_path = self.index_path
        json_text = db.to_json() + "\n"

        def _write_and_replace() -> None:
            # thread id in the tmp name so concurrent callers never collide on the temp path.
            tmp = index_path.with_suffix(f".json.{os.getpid()}.{threading.get_ident()}.tmp")
            with tmp.open("w", encoding="utf-8") as fh:
                fh.write(json_text)
                fh.flush()
                os.fsync(fh.fileno())
            tmp.replace(index_path)

        await _aio.to_thread(_write_and_replace)
