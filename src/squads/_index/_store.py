"""Locked, atomic read-modify-write access to ``<squad-dir>/.squads.json``.

The single global counter and all item metadata live here. Every mutation goes through a
``transaction()`` guarded by a three-layer lock:

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
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import anyio
from filelock import FileLock
from pydantic import ValidationError

from squads import _aio
from squads._errors import SquadsError
from squads._models._extras import ExtraKey as X
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._models._subentity import SubEntity
from squads._workflow._models import Field, WorkflowSpec


def _backfill_severity(db: SquadsDB) -> None:
    """Backfill top-level ``Item.severity`` from the legacy ``extra[X.SEVERITY]`` location
    for any item indexed before item-level severity became a top-level badge field.

    In-memory only, mirroring the old ``_propagate_prefix`` pattern: the corrected value
    reaches disk on the next write to that item (or ``sq repair``) — a dedicated one-way
    migration that walks every file to relocate it on disk is a separate, later step.
    """
    for item in db.items.values():
        if item.severity is None:
            legacy = item.extra.pop(X.SEVERITY, None)
            if legacy:
                item.severity = legacy


def _check_field_codes(
    label: str, obj: Item | SubEntity, fields: list[Field], spec: WorkflowSpec
) -> None:
    """Raise if any of *obj*'s stored badge codes aren't in its field's bound collection.

    Only field codes backed by a same-named model attribute (``priority``/``severity``
    today) are checked — ``getattr`` skips anything else (e.g. a future ``extra``-stored
    custom field), matching the storage this task actually implements.
    """
    for f in fields:
        code = getattr(obj, f.code, None)
        if code is None:
            continue
        coll = spec.collections.get(f.collection)
        if coll is None or code not in coll.badge_codes:
            raise SquadsError(
                f"{label} field {f.code!r} has unknown code {code!r}; "
                "run `sq repair` if the index is stale, or check the frontmatter"
            )


def _validate_badge_codes(db: SquadsDB, spec: WorkflowSpec) -> None:
    """Validate every item's/sub-entity's stored badge codes against their bound collections.

    The badge-vocabulary counterpart to :func:`_validate_item_vocab`'s type/status check —
    same seam, same fail-closed contract.
    """
    for item in db.items.values():
        _check_field_codes(item.id, item, spec.fields_for(item.type), spec)
        kind = spec.item_subentity_kind(item.type)
        if kind is None:
            continue
        sub_fields = spec.fields_for(kind)
        for sub in item.subentities:
            _check_field_codes(f"{item.id} sub-entity {sub.local_id}", sub, sub_fields, spec)


def _validate_item_vocab(db: SquadsDB, spec: WorkflowSpec) -> None:
    """Validate every item's ``type``, ``status``, and sub-entity statuses against the
    supplied ``WorkflowSpec``.

    Called from :meth:`IndexStore.load`. The spec is supplied explicitly by the
    ``IndexStore`` constructor; there is no lazy import of a process-global singleton.
    A corrupt or hand-edited index entry with an unknown type, status, or sub-entity
    status raises a clean :class:`SquadsError` rather than silently indexing and
    crashing downstream with a raw ``KeyError`` or ``ValueError``.
    """
    known_types: frozenset[str] = frozenset(spec.items)
    known_statuses: frozenset[str] = frozenset(spec.statuses)

    for item in db.items.values():
        if item.type not in known_types:
            raise SquadsError(
                f"item {item.id} has type {item.type!r}, which the active spec no longer "
                "declares; migrate or re-type this item before it can load again "
                "(or run `sq repair` if the index itself is merely stale)"
            )
        if item.status not in known_statuses:
            raise SquadsError(
                f"item {item.id} has status {item.status!r}, which the active spec no "
                "longer declares; migrate or re-type this item before it can load again "
                "(or run `sq repair` if the index itself is merely stale)"
            )
        # F5: sub-entity statuses share the same vocabulary — validate each one too.
        for sub in item.subentities:
            if sub.status not in known_statuses:
                raise SquadsError(
                    f"item {item.id} sub-entity {sub.local_id} has status {sub.status!r}, "
                    "which the active spec no longer declares; migrate or re-type this "
                    "sub-entity before it can load again (or run `sq repair` if the index "
                    "itself is merely stale)"
                )


@dataclass
class _ReflogOp:
    """A reflog entry buffered during a transaction, flushed after the commit.

    ``ts``/``actor``/``session_id``/``parent_session_id`` are captured from the ambient
    context at the moment :meth:`IndexStore._log` is called (buffer time), NOT re-read at
    flush time — a single transaction may buffer several ops under different ambient actor/
    clock bindings (bulk import rebinds per event while holding one open transaction), so
    each op must carry its own snapshot rather than sharing one taken after the last rebind.
    """

    op: str
    target: str
    delta: dict[str, Any]
    ts: str
    actor: str
    session_id: str | None
    parent_session_id: str | None


@dataclass
class _TransactionCtx:
    """Transaction context: the :class:`SquadsDB` plus :attr:`reflog_ops` buffered for
    post-commit append (flushed after ``os.replace``, while the file lock is held)."""

    db: SquadsDB
    reflog_ops: list[_ReflogOp] = field(default_factory=list[_ReflogOp])

    def log(
        self,
        op: str,
        target: str,
        delta: dict[str, Any],
        *,
        ts: str,
        actor: str,
        session_id: str | None,
        parent_session_id: str | None,
    ) -> None:
        """Buffer one reflog entry for post-commit append, with its own actor/clock snapshot."""
        self.reflog_ops.append(
            _ReflogOp(
                op=op,
                target=target,
                delta=delta,
                ts=ts,
                actor=actor,
                session_id=session_id,
                parent_session_id=parent_session_id,
            )
        )


@dataclass
class _ActiveTransaction:
    """The ambient binding for one in-flight ``transaction()`` call: which ``IndexStore``
    instance opened it, plus its buffered :class:`_TransactionCtx`.

    Bound in the module-level ``_active_transaction`` ``ContextVar`` below — never a
    ``self.foo`` instance attribute — so the binding is task-local, present only while
    *this* store holds all three locks.
    """

    store: IndexStore
    ctx: _TransactionCtx


# Task-local active-transaction handle. ContextVars are process-wide but task-local, so —
# unlike the instance attribute this replaces — a binding made by store A
# is visible to code running on the same task against store B (two squads in one process,
# e.g. a long-lived server). ``_transaction_ctx_for`` below closes that gap by checking
# ownership; nothing else reads this ContextVar directly. Follows the
# ``_rendering/_engine.py::_active_squad_dir`` precedent: one module-level ContextVar for
# one concern, not a field folded onto the general-purpose ``RequestContext`` — a
# transaction context is shorter-lived than a request and engine-internal, not an ambient
# request *input*.
_active_transaction: ContextVar[_ActiveTransaction | None] = ContextVar(
    "_active_transaction", default=None
)


def _transaction_ctx_for(store: IndexStore) -> _TransactionCtx | None:
    """Return *store*'s active transaction context, or ``None`` if it has none open.

    Ignores an ambient binding owned by a *different* ``IndexStore`` instance. Identity is
    the store instance, not its resolved index path: two ``IndexStore``s can legitimately
    point at the same squad directory in one process (``sq repair``, tests), and a store
    with no open transaction of its own stays the silent no-op it is today, rather than
    being routed into an unrelated store's buffer and committed there.

    For that no-open-transaction case, instance identity correctly mirrors the per-instance
    attribute this replaces. It is not a faithful translation in one other case, and must not
    be described as one: with store A's transaction open and store B's nested inside it on
    the same task, the old per-instance attribute let ``A._log()`` still find A's own context
    and buffer correctly, while this task-local slot lets B's binding shadow A's, so
    ``A._log()`` sees a foreign owner and returns ``None`` — A's entries are silently
    discarded for the inner transaction's duration, not misattributed into B's buffer (which
    path identity would do, and which is worse: it fails open by committing a wrong entry
    rather than closed by losing one). No live call path opens one store's transaction inside
    another's on one task, so this is unreachable today; what would make it reachable is a
    second store in flight on one task — fan-out, batch, or a server — the same trigger that
    already promotes this binding to an explicit parameter, and a per-store mapping is the
    answer on that day, not this one.
    """
    active = _active_transaction.get()
    if active is None or active.store is not store:
        return None
    return active.ctx


class IndexStore:
    def __init__(
        self,
        index_path: Path,
        lock_path: Path,
        *,
        spec: WorkflowSpec | None = None,
        lock_timeout: float = 10.0,
    ):
        """Construct an ``IndexStore``.

        ``spec`` is the :class:`WorkflowSpec` used to validate item vocabulary at
        load time.  When ``None``, the immutable bundled default is used, for code
        that constructs an ``IndexStore`` without an explicit spec (e.g. ``sq init``,
        ``sq adopt``, tests).  Pass ``Service.spec`` (or another resolved spec) to
        validate against a squad-specific override.
        """
        self.index_path = index_path
        self.lock_path = lock_path
        if spec is None:
            from squads._workflow import bundled_spec

            self._spec: WorkflowSpec = bundled_spec()
        else:
            self._spec = spec
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
        _backfill_severity(db)
        _validate_item_vocab(db, self._spec)
        _validate_badge_codes(db, self._spec)
        return db

    # ------------------------------------------------------------------ transaction
    @contextlib.asynccontextmanager
    async def transaction(self) -> AsyncGenerator[SquadsDB]:
        """Load under the lock, yield the DB to mutate, then atomically write it back.

        Three-layer lock taken Layer 1 → 2 → 3; Layers 2/3 via ``_aio.to_thread``.
        ``filelock.Timeout`` from the Layer 3 acquire propagates unchanged with no lock
        leak (inner ``finally`` no-ops, outer releases the proc-mutex, the ``async with``
        releases the per-loop lock).

        The active-transaction context (read by ``_log``) is bound to the
        ``_active_transaction`` ``ContextVar`` only once Layer 3 is held and the in-lock
        load below has produced it — never before any lock is taken — and is
        always unbound (restoring whatever was bound before, if anything) in the same
        ``finally`` that releases Layer 3, including when an exception escapes the body or
        the transaction is cancelled.

        After the ``os.replace`` commits, buffered reflog ops are appended while still
        holding all locks, strictly after commit. A failed append only warns; it never
        rolls back the committed mutation. If the body raises, nothing is written.
        """
        from squads._index._reflog import append_line, reflog_path

        # Layer 1 first — serialises concurrent coroutines on this event loop.
        async with self._loop_lock():
            # Layer 2 — acquire proc-mutex on a worker thread (off the event loop).
            await _aio.to_thread(self._proc_mutex.acquire)
            try:
                # Layer 3 — acquire file lock on a worker thread, inside the proc-mutex.
                # filelock.Timeout propagates here unchanged; inner finally is a no-op.
                await _aio.to_thread(self._lock.acquire)
                token = None
                try:
                    # The one and only load: this is also the context transaction()
                    # publishes, so there is no separate pre-lock load to discard.
                    ctx = _TransactionCtx(db=await self.load())
                    token = _active_transaction.set(_ActiveTransaction(store=self, ctx=ctx))
                    yield ctx.db
                    await self._atomic_write(ctx.db)

                    # Reflog append: strictly after os.replace, inside all locks. Guarded
                    # so any error degrades to a warning — never surfaces from an
                    # already-committed mutation (never-raise contract). Each entry replays
                    # its OWN buffer-time ts/actor/session snapshot (see ``_ReflogOp``) —
                    # not one snapshot shared across every buffered op.
                    if ctx.reflog_ops:
                        try:
                            rpath = reflog_path(self.index_path.parent)
                            for entry in ctx.reflog_ops:
                                await append_line(
                                    rpath,
                                    ts=entry.ts,
                                    actor=entry.actor,
                                    op=entry.op,
                                    target=entry.target,
                                    delta=entry.delta,
                                    session_id=entry.session_id,
                                    parent_session_id=entry.parent_session_id,
                                )
                        except Exception as exc:  # never fail a committed mutation
                            print(
                                f"[squads reflog] warning: reflog append failed: {exc}",
                                file=sys.stderr,
                            )
                finally:
                    # Restore (not clear) the ambient binding before releasing Layer 3, so
                    # a sibling/nested transaction's binding on this task is never clobbered.
                    if token is not None:
                        _active_transaction.reset(token)
                    await _aio.to_thread(self._lock.release)  # Layer 3 released first
            finally:
                await _aio.to_thread(self._proc_mutex.release)  # Layer 2; Layer 1 by async-with

    def _log(self, op: str, target: str, delta: dict[str, Any]) -> None:
        """Buffer a reflog entry on the active transaction context (no-op outside one), so the
        op is captured where the change is known and emitted after the commit.

        Snapshots the ambient actor/clock/session **now** (buffer time) rather than leaving
        that to the post-commit flush — see ``_ReflogOp`` for why a single transaction can't
        share one snapshot across every buffered op (bulk import rebinds actor/clock per event
        while the whole apply stays inside one transaction).
        """
        ctx = _transaction_ctx_for(self)
        if ctx is not None:
            from squads import _actor as actor
            from squads import _clock as clock

            sid, psid = actor.current_session()
            ctx.log(
                op,
                target,
                delta,
                ts=clock.iso(clock.now()),
                actor=actor.current_actor(),
                session_id=sid,
                parent_session_id=psid,
            )

    async def overwrite(self, db: SquadsDB) -> None:
        """Replace the whole index under the three-layer lock (used by ``sq repair``), with the
        same Layer-1-first ordering as :meth:`transaction`."""
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
        try:
            # fsync the write handle — Windows raises OSError [Errno 9] on a read-only handle.
            with tmp.open("w", encoding="utf-8") as fh:
                fh.write(db.to_json() + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            tmp.replace(self.index_path)
        except BaseException:
            # An exception escaping the write is in-model (process death is not, and can't
            # run this handler regardless) — clean up the temp sibling before re-raising.
            # Mirrors `_aio.atomic_replace_sync`'s shape; keep both identical.
            tmp.unlink(missing_ok=True)
            raise

    async def _atomic_write(self, db: SquadsDB) -> None:
        """Async atomic write: tmp-open/write/fsync/replace runs as ONE thread hop.

        No ``await`` between ``os.fsync`` and ``tmp.replace`` — they share one sync closure so
        no coroutine interleaves between the durability barrier and the rename.
        """
        index_path = self.index_path
        json_text = db.to_json() + "\n"

        def _write_and_replace() -> None:
            # thread id in the tmp name so concurrent callers never collide on the temp path.
            tmp = index_path.with_suffix(f".json.{os.getpid()}.{threading.get_ident()}.tmp")
            try:
                with tmp.open("w", encoding="utf-8") as fh:
                    fh.write(json_text)
                    fh.flush()
                    os.fsync(fh.fileno())
                tmp.replace(index_path)
            except BaseException:
                # Mirrors `_aio.atomic_replace_sync`'s cleanup shape; keep both identical.
                tmp.unlink(missing_ok=True)
                raise

        await _aio.to_thread(_write_and_replace)
