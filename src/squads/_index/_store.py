"""Locked, atomic read-modify-write access to ``<squad-dir>/.squads.json``, which holds the single
global counter and all item metadata. Every mutation goes through a ``transaction()`` guarded by
three locks taken in this order and released in reverse, each acquire in ``try/finally`` so nothing
leaks on exception, cancellation or lock timeout:

- Layer 1: a per-loop ``anyio.Lock`` serialising coroutines on one event loop (it binds to the
  loop it is first used on, so locks are cached per running-loop id under a ``threading.Lock``);
- Layer 2: ``_proc_mutex`` (``threading.Lock``), so one OS thread per process is in the file-lock
  section;
- Layer 3: ``filelock.FileLock(thread_local=False)`` for cross-process exclusion, safe because
  Layer 2 guarantees single-threaded entry.

Commits are atomic ``os.replace``, so concurrent ``sq`` invocations never corrupt the file or
collide on IDs.

**Skew direction: markdown is always ahead of or equal to the index, never behind.** Within a
transaction every write to an item's markdown (create, frontmatter update, marker-section edit,
rename/move, unlink) happens in the transaction body, before it returns; this module's
``os.replace`` (:meth:`IndexStore._atomic_write`) is always the transaction's last write to squad
data, and nothing that mutates an item ``.md`` may run after it. A process killed mid-transaction
can therefore only leave the markdown newer than the index:

| interrupted op | surviving state | healing rebuild outcome |
|---|---|---|
| create | file exists, not indexed | indexes it; the high-water mark keeps the number unique |
| update | file has the new value, index has the old one | adopts the file's value |
| remove | file gone, index still has the entry | drops the orphan entry, reporting it as missing |
| retype/rename | file at the new path/id, index at the old | re-indexes from the new path |

Each heals losslessly under ``sq repair`` at the current schema, and under ``sq migrate up``'s own
rebuild while the schema is behind, because the rebuild derives the index from the markdown. The
inverse skew is forbidden: an index ahead of the markdown would let repair silently revert a
committed mutation or resurrect a removed item, and a loud, repairable inconsistency beats a quiet
rollback.

Exempt, because neither has a mirrored index value to disagree about: regenerable artifacts (backend
pointers, managed regions in ``CLAUDE.md``/``AGENTS.md``, ``.claude/`` output), which ``sq sync``
reproduces from nothing and may be written after the commit; and the reflog, appended after
``os.replace`` under a never-raise contract (see :meth:`IndexStore.transaction`) as an append-only
log, not source of truth. Compliance is the ordering, not the syntax: a pass that owns every file
and ends by rebuilding the index (``repad``, ``renumber``) complies without nesting its renames in
one transaction. Whether an index-derived frontmatter rewrite may overwrite a value still only on
disk is a separate guard at the item-file write seam (:func:`squads._itemfile.ensure_no_skew`).

**Request-scoped reads never enter this ordering.** :meth:`IndexStore.load` may serve a snapshot
filed by the ambient :class:`_ReadScope` (:func:`read_scope`, entered once per CLI invocation), but
:meth:`transaction` never consults it: its in-lock load always calls :meth:`_read_from_disk`, so the
only db that reaches :meth:`IndexStore._atomic_write` was read from disk under the file lock a
moment before. A stale snapshot written back would put an older index over a newer one, the
forbidden direction, so the scope is simply never wired to the commit path.

**Failure model.** In model: process death (``SIGKILL``/``SIGTERM``, a harness timeout, an OOM kill,
a container stop, or an exception escaping a transaction body), where writes the kernel accepted
survive, so program order alone orders durability. Out of model: a host crash or power loss, which
would need an ``fsync`` of every file and its parent directory at each step and could still only
bound the skew without a journal. The rebuild remains the recovery path there but promises nothing
about which side is ahead.
"""

import asyncio
import contextlib
import sys
import threading
from collections.abc import AsyncGenerator, Generator
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import Any

import anyio
from filelock import FileLock, Timeout
from pydantic import ValidationError

from squads import _aio
from squads._errors import IndexLockTimeoutError, SquadsError, UndecodableFileError
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._models._subentity import SubEntity
from squads._workflow._models import Field, WorkflowSpec

# Seconds a lock acquire waits before it tells the user it is waiting.
_LOCK_NOTICE_AFTER = 1.0


def _check_field_codes(
    label: str, obj: Item | SubEntity, fields: list[Field], spec: WorkflowSpec
) -> None:
    """Raise if any of *obj*'s stored badge codes is not in its field's bound collection, read
    through ``badge_value`` (shared by ``Item``, ``SubEntity`` and
    ``_workflow._loader._badge_field_mismatches``) so every declared field is checked. It is the
    every-load backstop for what the loader's override-only cross-check cannot see, so it cannot
    tell a code an override shrank away from one never valid: its message names the undeclared code
    and the always-correct remedy (fix the stored value), with ``sq repair`` only for a stale index.
    """
    for f in fields:
        code = obj.badge_value(f.code)
        if code is None:
            continue
        coll = spec.collections.get(f.collection)
        if coll is None or not coll.declares(code):
            raise SquadsError(
                f"{label} field {f.code!r} has code {code!r}, which the active workflow spec's "
                f"{f.collection!r} collection does not declare; fix the frontmatter value to a "
                "currently valid code, or run `sq repair` if the index itself is merely stale"
            )


def badge_code_problems(db: SquadsDB, spec: WorkflowSpec) -> list[str]:
    """One line per stored badge code, on an item or a sub-entity, that its bound collection
    does not declare: the values the load check refuses, without its recovery clause."""
    problems: list[str] = []
    for item in db.items.values():
        scopes: list[tuple[str, Item | SubEntity, list[Field]]] = [
            (item.id, item, spec.fields_for(item.type))
        ]
        kind = spec.item_subentity_kind(item.type)
        if kind is not None:
            sub_fields = spec.fields_for(kind)
            scopes.extend(
                (f"{item.id} sub-entity {s.local_id}", s, sub_fields) for s in item.subentities
            )
        for label, obj, fields in scopes:
            for f in fields:
                code = obj.badge_value(f.code)
                coll = spec.collections.get(f.collection)
                if code is not None and (coll is None or not coll.declares(code)):
                    problems.append(
                        f"{label} field {f.code!r} has code {code!r}, which the "
                        f"{f.collection!r} collection does not declare (in {item.path})"
                    )
    return problems


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
    """Validate every item's ``type``, ``status`` and sub-entity statuses against the
    ``WorkflowSpec`` the ``IndexStore`` was constructed with (called from :meth:`IndexStore.load`;
    there is no global singleton). A corrupt or hand-edited entry raises a clean
    :class:`SquadsError` instead of a raw ``KeyError`` downstream.
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
        # Sub-entity statuses share the same vocabulary as the item's own — validate each one too.
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
    """A reflog entry buffered during a transaction and flushed after the commit. ``ts``, ``actor``,
    ``session_id`` and ``parent_session_id`` are snapshotted when :meth:`IndexStore.log` is called,
    not at flush, since one transaction may buffer ops under different ambient bindings (bulk import
    rebinds per event).
    """

    op: str
    target: str
    delta: dict[str, Any]
    ts: str
    actor: str
    session_id: str | None
    parent_session_id: str | None


@dataclass
class HeldItemFiles:
    """Item-file texts and file moves a transaction holds in memory, in first-touch order.

    The service layer fills it while a hold is open and applies it once, before the index
    commit: each moved file is renamed, then written. ``moves`` maps the path a file has on
    disk to the path it is to have; ``texts`` is keyed by final path.
    """

    texts: dict[Path, str] = field(default_factory=dict[Path, str])
    moves: dict[Path, Path] = field(default_factory=dict[Path, Path])

    def disk_path(self, path: Path) -> Path:
        """Where the file that is to be at *path* sits on disk now."""
        return next((origin for origin, final in self.moves.items() if final == path), path)


@dataclass
class _TransactionCtx:
    """Transaction context: the :class:`SquadsDB` plus :attr:`reflog_ops` buffered for
    post-commit append (flushed after ``os.replace``, while the file lock is held), and the
    :class:`HeldItemFiles` of an open hold, if any."""

    db: SquadsDB
    reflog_ops: list[_ReflogOp] = field(default_factory=list[_ReflogOp])
    held: HeldItemFiles | None = None

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


# Task-local active-transaction handle. A ContextVar is task-local but not store-local, so store A's
# binding is visible to store B on one task; ``_transaction_ctx_for`` checks ownership and is the
# only reader. It is separate from ``RequestContext`` because a transaction is shorter-lived and
# engine-internal.
_active_transaction: ContextVar[_ActiveTransaction | None] = ContextVar(
    "_active_transaction", default=None
)


def _transaction_ctx_for(store: IndexStore) -> _TransactionCtx | None:
    """Return *store*'s active transaction context, or ``None`` if it has none open, ignoring a
    binding owned by another ``IndexStore``. Identity is the store instance, not its index path, so
    a store with no open transaction stays a no-op rather than logging into an unrelated store's
    buffer. If store B's transaction nests inside A's on one task, B's binding shadows A's and
    ``A.log()`` drops its entries for that span (failing closed); no live path does this, and a
    second store in flight would call for an explicit parameter.
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
        spec: WorkflowSpec,
        lock_timeout: float = 10.0,
    ):
        """Construct an ``IndexStore``. ``spec`` is the :class:`WorkflowSpec` that validates item
        vocabulary at load time; pass ``Service.spec`` to validate against a squad-specific
        override.
        """
        self.index_path = index_path
        self.lock_path = lock_path
        self._spec = spec
        # Layer 3 — cross-process file lock. thread_local=False is safe because Layer 2
        # guarantees single-threaded entry, so its shared-state race is unreachable.
        self._lock = FileLock(str(lock_path), timeout=lock_timeout, thread_local=False)
        self._lock_timeout = lock_timeout
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

    async def _acquire_file_lock(self) -> None:
        """Take Layer 3: wait up to :data:`_LOCK_NOTICE_AFTER` quietly, say so on stderr, then
        wait out the rest of the timeout.

        Raises :class:`IndexLockTimeoutError` when the lock is still held at the end.
        """
        first = min(_LOCK_NOTICE_AFTER, self._lock_timeout)
        try:
            await _aio.to_thread(partial(self._lock.acquire, timeout=first))
        except Timeout:
            await self._acquire_after_notice(first)

    async def _acquire_after_notice(self, waited: float) -> None:
        """Say on stderr that the lock is being waited for, then wait out the timeout's rest."""
        print(f"waiting for the index lock {self.lock_path}…", file=sys.stderr)
        try:
            await _aio.to_thread(
                partial(self._lock.acquire, timeout=max(self._lock_timeout - waited, 0.0))
            )
        except Timeout:
            raise IndexLockTimeoutError(self.lock_path) from None

    # ------------------------------------------------------------------ create / read
    def create_empty(self) -> SquadsDB:
        """Write a fresh empty index (sync; used by tests and one-shot bootstrap paths).

        Prefer :meth:`create_empty_threaded` on the async service path (``init``/``adopt``).
        """
        db = SquadsDB(counter=0)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write_sync(db)
        return db

    async def create_empty_threaded(self) -> SquadsDB:
        """Write a fresh empty index on a worker thread (async; used by ``init``/``adopt``)."""
        db = SquadsDB(counter=0)
        await _aio.mkdir(self.index_path.parent, parents=True, exist_ok=True)
        await self._atomic_write(db)
        return db

    def exists(self) -> bool:
        return self.index_path.is_file()

    async def _read_from_disk(self, *, validate_vocab: bool) -> SquadsDB:
        """Read and validate the index straight from disk: the one implementation behind
        :meth:`load` (the scope-aware wrapper) and :meth:`transaction` (which must never consult or
        fill the read scope). A
        stored counter trailing the max item sequence is raised in memory so allocation cannot reuse
        a number (invariant 2 keeps allocation inside ``transaction()``). ``validate_vocab=False``
        skips only the semantic checks and is passed solely by ``sq repair``'s pre-rebuild read, to
        recover the prior counter and corpus after vocab drift; a structurally unreadable index
        raises either way.
        """
        try:
            raw = await _aio.read_text(self.index_path)
            db = SquadsDB.model_validate_json(raw)
        except FileNotFoundError as exc:
            # No index on disk is a different story from a corrupt one (fresh clone of a gitignored
            # index, wrong directory, half-finished adopt) but the same cause and remedy, so the
            # wording is a sibling of the corrupt-index message.
            raise SquadsError(
                f"missing index {self.index_path.name}; "
                "run `sq repair` to rebuild it from the markdown files"
            ) from exc
        except (ValidationError, UndecodableFileError) as exc:  # fmt: skip
            # An undecodable index is just as unreadable as a schema-invalid one — same
            # remedy, same wording; only ValidationError carries an error_count().
            reason = (
                f"{exc.error_count()} problem(s)" if isinstance(exc, ValidationError) else str(exc)
            )
            raise SquadsError(
                f"corrupt index {self.index_path.name} ({reason}); "
                "run `sq repair` to rebuild it from the markdown files"
            ) from exc
        max_seq = max((item.sequence_id for item in db.items.values()), default=0)
        if db.counter < max_seq:
            db.counter = max_seq
        if validate_vocab:
            _validate_item_vocab(db, self._spec)
            _validate_badge_codes(db, self._spec)
        return db

    async def load(self, *, validate_vocab: bool = True, fresh: bool = False) -> SquadsDB:
        """Read without locking, on a worker thread, for queries; writes use :meth:`transaction`. An
        ambient :class:`_ReadScope` that holds this store's snapshot is returned with no disk read,
        else the result of :meth:`_read_from_disk` is filed in the scope if one is bound; without a
        scope it is only slower, never wrong. ``validate_vocab=False`` and ``fresh=True`` bypass the
        scope in both directions: filing an unvalidated db would let a later caller skip a
        fail-closed check, and ``fresh`` callers (``_confirm_cross_source``) need a real re-read.
        """
        if not validate_vocab or fresh:
            return await self._read_from_disk(validate_vocab=validate_vocab)
        scope = _read_scope.get()
        if scope is None:
            return await self._read_from_disk(validate_vocab=True)
        cached = scope.snapshots.get(self)
        if cached is not None:
            return cached
        db = await self._read_from_disk(validate_vocab=True)
        scope.snapshots[self] = db
        return db

    # ------------------------------------------------------------------ transaction
    @contextlib.asynccontextmanager
    async def transaction(self) -> AsyncGenerator[SquadsDB]:
        """Load under the lock, yield the DB to mutate, then atomically write it back. Layers are
        taken 1, 2, 3 in that order (2 and 3 via ``_aio.to_thread``) and a Layer 3 timeout raises
        :class:`IndexLockTimeoutError` with nothing leaked. The active-transaction context that
        ``log`` reads is bound only once Layer 3 is held and unbound in the ``finally`` that
        releases it, even on an exception or cancellation, and any read scope this store filed is
        invalidated there too.

        The in-lock load is :meth:`_read_from_disk`, never :meth:`load`, so a stale snapshot can
        never be written back. After the commit, buffered reflog ops are appended under the locks
        and a failed append only warns. If the body raises, nothing is written to the index while
        its markdown writes stand, leaving markdown ahead, the direction the rebuild heals.
        """
        from squads._index._reflog import append_line, reflog_path

        # Layer 1 first — serialises concurrent coroutines on this event loop.
        async with self._loop_lock():
            # Layer 2 — acquire proc-mutex on a worker thread (off the event loop).
            await _aio.to_thread(self._proc_mutex.acquire)
            try:
                # Layer 3 — acquire file lock on a worker thread, inside the proc-mutex.
                # A timeout raises IndexLockTimeoutError here; the outer finally releases Layer 2.
                await self._acquire_file_lock()
                token = None
                try:
                    # The one and only load: this is also the context transaction()
                    # publishes, so there is no separate pre-lock load to discard. Always
                    # the disk, never the read scope — see the docstring above.
                    ctx = _TransactionCtx(db=await self._read_from_disk(validate_vocab=True))
                    token = _active_transaction.set(_ActiveTransaction(store=self, ctx=ctx))
                    yield ctx.db
                    await self._atomic_write(ctx.db)

                    # Reflog append: strictly after os.replace, inside all locks, never raising
                    # (an error degrades to a warning), each op replaying its own buffer-time
                    # ts/actor/session snapshot (see ``_ReflogOp``).
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
                    # Unconditional, commit or raise: drop any snapshot this store filed so a later
                    # read in the invocation cannot see pre-mutation state. On the raise path it
                    # would still be accurate, but dropping it keeps the rule to one clause.
                    scope = _read_scope.get()
                    if scope is not None:
                        scope.snapshots.pop(self, None)
                    # Restore (not clear) the ambient binding before releasing Layer 3, so
                    # a sibling/nested transaction's binding on this task is never clobbered.
                    if token is not None:
                        _active_transaction.reset(token)
                    await _aio.to_thread(self._lock.release)  # Layer 3 released first
            finally:
                await _aio.to_thread(self._proc_mutex.release)  # Layer 2; Layer 1 by async-with

    def log(self, op: str, target: str, delta: dict[str, Any]) -> None:
        """Buffer a reflog entry on the active transaction context so it is emitted after the
        commit, snapshotting the ambient actor, clock and session now (see ``_ReflogOp``). It is a
        silent no-op when this store has no open transaction, including when the context belongs to
        another store: raising would abort a transaction after a durable markdown write and before
        the index commit, manufacturing the skew the durability model forbids. This ambient form is
        provisional: with fan-out or a server the handle becomes an explicit parameter
        (``txn.log(...)``).
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

    def held_item_files(self) -> HeldItemFiles | None:
        """The open hold of this store's active transaction, or ``None`` when there is none."""
        ctx = _transaction_ctx_for(self)
        return ctx.held if ctx is not None else None

    def open_held_item_files(self) -> HeldItemFiles:
        """Open a hold on the active transaction. Raises when no transaction is open or a hold
        already is: a second hold would silently drop the first one's texts."""
        ctx = _transaction_ctx_for(self)
        if ctx is None:
            raise SquadsError("item files can be held only inside an open transaction")
        if ctx.held is not None:
            raise SquadsError("a hold on item files is already open in this transaction")
        ctx.held = HeldItemFiles()
        return ctx.held

    def close_held_item_files(self) -> None:
        """Drop the active transaction's hold, if any."""
        ctx = _transaction_ctx_for(self)
        if ctx is not None:
            ctx.held = None

    @contextlib.asynccontextmanager
    async def exclusive(self) -> AsyncGenerator[None]:
        """Hold the three-layer lock across a multi-step pass that reads files, rewrites them
        and commits the index itself with :meth:`overwrite`, so no writer interleaves. Inside
        the block :meth:`overwrite` does not take the lock again; :meth:`transaction` still
        would, so the body must not open one."""
        async with self._loop_lock():
            await _aio.to_thread(self._proc_mutex.acquire)
            try:
                await self._acquire_file_lock()
                token = _exclusive_holder.set(self)
                try:
                    yield
                finally:
                    _exclusive_holder.reset(token)
                    scope = _read_scope.get()
                    if scope is not None:
                        scope.snapshots.pop(self, None)
                    await _aio.to_thread(self._lock.release)
            finally:
                await _aio.to_thread(self._proc_mutex.release)

    async def overwrite(self, db: SquadsDB) -> None:
        """Replace the whole index under the three-layer lock (used by ``sq repair``), with the
        same Layer-1-first ordering as :meth:`transaction`.

        Invalidates any read scope this store filed the same way :meth:`transaction` does —
        unconditionally, in the same ``finally`` that releases Layer 3 — so a read after this
        in the same invocation never serves the pre-rebuild snapshot.
        """
        if _exclusive_holder.get() is self:
            await self._atomic_write(db)
            return
        async with self._loop_lock():
            await _aio.to_thread(self._proc_mutex.acquire)
            try:
                await self._acquire_file_lock()
                try:
                    await self._atomic_write(db)
                finally:
                    scope = _read_scope.get()
                    if scope is not None:
                        scope.snapshots.pop(self, None)
                    await _aio.to_thread(self._lock.release)
            finally:
                await _aio.to_thread(self._proc_mutex.release)

    # ------------------------------------------------------------------ internals
    def _atomic_write_sync(self, db: SquadsDB) -> None:
        """Sync atomic write — for ``create_empty`` (bootstrap, single-process path).

        Delegates to :func:`squads._aio.atomic_replace_sync`, the shared temp+fsync+
        ``os.replace`` primitive markdown writes use too — the index's own JSON serialization
        stays here; the primitive never learns about :class:`SquadsDB`.
        """
        _aio.atomic_replace_sync(self.index_path, db.to_json() + "\n")

    async def _atomic_write(self, db: SquadsDB) -> None:
        """Async atomic write: delegates to :func:`squads._aio.atomic_write_text`, which runs
        the whole tmp-open/write/fsync/replace sequence as one thread hop, with no ``await``
        between the fsync and the rename.
        """
        await _aio.atomic_write_text(self.index_path, db.to_json() + "\n")


@dataclass
class _ReadScope:
    """One command invocation's read-side index cache: at most one :class:`SquadsDB` snapshot per
    :class:`IndexStore` instance, keyed on store identity as ``_active_transaction`` is. ``load()``
    is its only consumer and :meth:`IndexStore.transaction` never touches it. It is one object, not
    a module-level dict, so a single ``ContextVar`` binds and unbinds the whole cache.
    """

    snapshots: dict[IndexStore, SquadsDB] = field(default_factory=dict[IndexStore, SquadsDB])


# The store whose :meth:`IndexStore.exclusive` block the current task is inside, if any.
_exclusive_holder: ContextVar[IndexStore | None] = ContextVar("_exclusive_holder", default=None)

# Task-local read-scope handle, absent by default and opt-in: without one ``load()`` is only
# slower, never wrong, and ``transaction()`` never reads or changes it.
_read_scope: ContextVar[_ReadScope | None] = ContextVar("_read_scope", default=None)


def enter_read_scope() -> Token[_ReadScope | None]:
    """Bind a fresh, empty :class:`_ReadScope` and return the token to undo it with
    (:func:`exit_read_scope`); :func:`read_scope` is the block form.
    """
    return _read_scope.set(_ReadScope())


def exit_read_scope(token: Token[_ReadScope | None]) -> None:
    """Undo a binding made by :func:`enter_read_scope`."""
    _read_scope.reset(token)


@contextlib.contextmanager
def read_scope() -> Generator[None]:
    """Bind a fresh, empty :class:`_ReadScope` for the block: each operation runs in one, so its
    reads of the index share one load.
    """
    token = enter_read_scope()
    try:
        yield
    finally:
        exit_read_scope(token)
