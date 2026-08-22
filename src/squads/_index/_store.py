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

**Skew direction: markdown is always ahead of or equal to the index, never behind.** Within a
transaction, every write to an item's markdown — create, frontmatter update, marker-section
edit, rename/move, unlink — happens inside the transaction body, before it returns. This
module's ``os.replace`` (:meth:`IndexStore._atomic_write`) is always the transaction's *last*
write to squad data; nothing that mutates an item ``.md`` may run after it commits. A process
killed mid-transaction can therefore only ever leave the markdown newer than the index, in
every direction of change:

| interrupted op | surviving state | ``sq repair`` outcome |
|---|---|---|
| create | file exists, not indexed | indexes it; the high-water mark keeps the number unique |
| update | file has the new value, index has the old one | adopts the file's value |
| remove | file gone, index still has the entry | drops the orphan entry, reporting it as missing |
| retype/rename | file at the new path/id, index at the old | re-indexes from the new path |

Each of those heals losslessly, because repair derives the index *from* the markdown — a
markdown-ahead skew is simply its input, not a special case it has to detect. The inverse skew
is forbidden rather than merely discouraged: an index ahead of the markdown would let repair
**silently revert** a committed mutation or resurrect a removed item, and a loud, repairable
inconsistency beats a quiet rollback every time.

Exempt from this ordering, because neither has a mirrored value in the index for the two sides
to disagree about: regenerable artifacts (backend pointer files, managed regions in
``CLAUDE.md``/``AGENTS.md``, ``.claude/`` output) may be written after the commit, since
``sq sync`` reproduces them from nothing; and the reflog, deliberately appended after
``os.replace`` under a never-raise contract (see :meth:`IndexStore.transaction`) because it is
an append-only log, not source of truth. Compliance is the ordering itself, not any particular
syntax for reaching it: a board-wide reshaping pass that owns every file and finishes by
rebuilding the index outright (``repad``, ``renumber``) complies by ending in that rebuild
rather than by nesting hundreds of renames inside one transaction. That is a separate question
from whether an index-derived frontmatter *rewrite* may overwrite a value still only on disk —
the guard for that lives at the item-file write seam (see
:func:`squads._itemfile.ensure_no_skew`) and does not reach either of them, since neither
sources a value from the index in the first place.

**Request-scoped reads never enter this ordering.** :meth:`IndexStore.load` optionally serves a
snapshot filed by an ambient :class:`_ReadScope` (see :func:`read_scope`, entered once per CLI
invocation at the sync-to-async bridge) instead of re-reading disk — but :meth:`transaction`
never consults that scope: its in-lock load always calls :meth:`_read_from_disk` directly, so
the only db that ever reaches :meth:`IndexStore._atomic_write` is one read from disk under this
module's file lock a moment before. Serving a transaction a stale snapshot would write an older
index over a newer one — the one skew direction forbidden above — so this is not a rule the
scope has to remember to honour; the scope is simply never wired to the commit path at all.

**Failure model.** In model: process death — ``SIGKILL``/``SIGTERM``, a harness timeout or
background-stop, an OOM kill, a container stop, or an exception escaping a transaction body,
all treated as one event class. Writes already accepted by the kernel survive it, so program
order alone is enough to order durability events. Out of model: a host crash or power loss,
where ordering would additionally need an ``fsync`` of every file *and* its parent directory at
each step, and even then the skew could only be bounded, not removed, without a journal.
``sq repair`` remains the recovery path there too; it makes no promise about which side is
ahead.
"""

import asyncio
import contextlib
import sys
import threading
from collections.abc import AsyncGenerator, Generator
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import anyio
from filelock import FileLock
from pydantic import ValidationError

from squads import _aio
from squads._errors import SquadsError, UndecodableFileError
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

    Reads through ``badge_value`` — the generic accessor ``Item`` and ``SubEntity`` both carry
    — so **every** declared field code is checked, not only the two (``priority``/``severity``)
    that happen to have a same-named model attribute. A dynamic attribute read keyed on the
    field's own code silently skipped every adopter-declared field, whose value lives in the
    generic ``extra`` store (``tests/meta`` now forbids that shape outright): the
    same operation (shrinking a collection out from under a live corpus) failed closed on
    ``priority`` and passed clean on a declared ``impact``, indefinitely. The accessor is the
    same one ``_workflow._loader._badge_field_mismatches`` already reads through, so the load
    boundary and the live-index cross-check now see the same set of stored values.

    This is the load-boundary backstop, not the primary enforcement: a workflow override that
    shrinks or replaces a badge collection out from under a live corpus is caught earlier, at
    load, by the workflow loader's own live-index cross-check
    (``_workflow._loader.validate_against_index``/``sq workflow lint``) — that check knows an
    override is involved (it only ever runs when one is present) and names the offending items
    with a remedy scoped to that cause: add the code back to the collection, revert the
    override, or update the affected items. This check exists for what that one cannot see —
    it runs on *every* load, override or not — so it has no way to tell "this code was valid
    until an override shrank the collection" apart from "this code was never valid at all" (a
    hand-edited or otherwise corrupted frontmatter value). Its own message must therefore stay
    true in **both** cases: it names the fact (the active spec's collection does not declare
    this code) and the one remedy that is always correct regardless of cause — fix the stored
    value — plus ``sq repair`` scoped correctly to the narrower case where it actually helps
    (the index merely stale relative to a still-valid frontmatter value).
    """
    for f in fields:
        code = obj.badge_value(f.code)
        if code is None:
            continue
        coll = spec.collections.get(f.collection)
        if coll is None or code not in coll.badge_codes:
            raise SquadsError(
                f"{label} field {f.code!r} has code {code!r}, which the active workflow spec's "
                f"{f.collection!r} collection does not declare; fix the frontmatter value to a "
                "currently valid code, or run `sq repair` if the index itself is merely stale"
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
    """A reflog entry buffered during a transaction, flushed after the commit.

    ``ts``/``actor``/``session_id``/``parent_session_id`` are captured from the ambient
    context at the moment :meth:`IndexStore.log` is called (buffer time), NOT re-read at
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
    the same task, the old per-instance attribute let ``A.log()`` still find A's own context
    and buffer correctly, while this task-local slot lets B's binding shadow A's, so
    ``A.log()`` sees a foreign owner and returns ``None`` — A's entries are silently
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

    async def _read_from_disk(self, *, validate_vocab: bool) -> SquadsDB:
        """Read and validate the index straight from disk — the one implementation both
        :meth:`load` (the scope-aware wrapper over this) and :meth:`transaction` (which must
        never consult or fill the read scope — see the module docstring's skew-direction rule)
        delegate to.

        If the stored counter trails the max item sequence (e.g. a hand-edit), it is raised
        *in memory* so the next allocation can't reuse a number; the corrected value only
        reaches disk on the next ``transaction()`` save (or ``sq repair``). Allocation still
        happens only inside ``transaction()`` (invariant 2).

        ``validate_vocab`` gates only the *semantic* checks (:func:`_validate_item_vocab`,
        :func:`_validate_badge_codes`) — every ordinary caller wants those fail-closed, so
        callers default to ``True``. The one exception is ``sq repair``'s own pre-rebuild read:
        its whole point is to recover from exactly this drift (e.g. a type/status/badge-code
        dropped via an override), so it reads with ``validate_vocab=False`` to get the prior
        counter/padding/corpus back even when a stored item's vocab no longer resolves. A
        structurally unreadable index (missing file, bad JSON, schema violation) still raises
        either way — that is genuine corruption, not vocab drift, and has no prior state to
        recover.
        """
        try:
            raw = await _aio.read_text(self.index_path)
            db = SquadsDB.model_validate_json(raw)
        except FileNotFoundError as exc:
            # No index on disk at all — a different operator story from a corrupt one
            # (fresh clone of a gitignored index, wrong --dir, half-finished adopt), but
            # the same cause (an unusable index) and the same remedy, so the wording is
            # this message's sibling rather than a distinct case.
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
        _backfill_severity(db)
        if validate_vocab:
            _validate_item_vocab(db, self._spec)
            _validate_badge_codes(db, self._spec)
        return db

    async def load(self, *, validate_vocab: bool = True, fresh: bool = False) -> SquadsDB:
        """Read without locking, on a worker thread — for queries (list/show); writes use
        :meth:`transaction`.

        Consults the ambient :class:`_ReadScope` (see :func:`read_scope`) first: if one is
        bound and already holds a snapshot this store filed, that snapshot is returned as-is
        with no disk read at all. Otherwise (or with no scope bound) this reads via
        :meth:`_read_from_disk` and, when a scope is bound, files the result for the rest of
        the invocation to reuse. Absent a scope, this behaves exactly as it always has —
        opt-in, and its absence is only ever slow, never wrong.

        Two bypasses, both of which neither consult nor fill the scope:

        - ``validate_vocab=False`` — filing an unvalidated db in a shared slot would let a
          later validating caller in the same invocation skip a fail-closed check, the wrong
          direction to fail. See :meth:`_read_from_disk` for why this one exists at all.
        - ``fresh=True`` — for the caller whose contract is "re-read the index right now"
          (``_confirm_cross_source`` in ``_services/_maintenance.py``, ``sq check``'s
          false-positive suppression round): serving *or filing* a scope-cached answer here
          would defeat the one re-read its own docstring depends on.
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
        """Load under the lock, yield the DB to mutate, then atomically write it back.

        Three-layer lock taken Layer 1 → 2 → 3; Layers 2/3 via ``_aio.to_thread``.
        ``filelock.Timeout`` from the Layer 3 acquire propagates unchanged with no lock
        leak (inner ``finally`` no-ops, outer releases the proc-mutex, the ``async with``
        releases the per-loop lock).

        The active-transaction context (read by ``log``) is bound to the
        ``_active_transaction`` ``ContextVar`` only once Layer 3 is held and the in-lock
        load below has produced it — never before any lock is taken — and is
        always unbound (restoring whatever was bound before, if anything) in the same
        ``finally`` that releases Layer 3, including when an exception escapes the body or
        the transaction is cancelled.

        The in-lock load always calls :meth:`_read_from_disk` directly — never :meth:`load`,
        and so never the ambient read scope. This is the load-bearing line of the whole
        read-scope design: the only db that ever reaches :meth:`_atomic_write` is one read
        from disk under this lock a moment before, so a stale cached snapshot can never be
        the one written back — see the module docstring's skew-direction rule. Any read
        scope this store filed before the transaction opened is unconditionally invalidated
        in the same ``finally`` that unbinds ``_active_transaction``, commit or raise, so a
        read after this transaction (in the same invocation) never serves pre-mutation state.

        After the ``os.replace`` commits, buffered reflog ops are appended while still
        holding all locks, strictly after commit. A failed append only warns; it never
        rolls back the committed mutation.

        If the body raises, nothing is written *to the index* — the raise propagates before
        ``_atomic_write`` is ever reached. Markdown writes the body already made stand; that is
        not a partial rollback failing to finish its job, it is the module docstring's
        skew-direction rule doing exactly what it is for: the crash leaves markdown ahead of
        the index, the one direction ``sq repair`` heals losslessly.
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
                    # publishes, so there is no separate pre-lock load to discard. Always
                    # the disk, never the read scope — see the docstring above.
                    ctx = _TransactionCtx(db=await self._read_from_disk(validate_vocab=True))
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
                    # Unconditional, commit or raise: drop any snapshot this store filed
                    # before a read after this transaction (in the same invocation) can ever
                    # observe pre-mutation state. On the raise path the index was never
                    # written, so the snapshot would still be accurate — dropped anyway, in
                    # exchange for a rule with no second clause.
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
        """Buffer a reflog entry on the active transaction context, so the op is captured where
        the change is known and emitted after the commit.

        Snapshots the ambient actor/clock/session **now** (buffer time) rather than leaving
        that to the post-commit flush — see ``_ReflogOp`` for why a single transaction can't
        share one snapshot across every buffered op (bulk import rebinds actor/clock per event
        while the whole apply stays inside one transaction).

        A deliberate silent no-op when this store has no open transaction — including when the
        ambient context belongs to a *different* ``IndexStore`` instance (see
        ``_transaction_ctx_for``). Raising here would turn a benign two-stores-in-one-process
        situation into a crash, and because most callers write markdown before they log, it
        would also abort a transaction after a durable markdown write and before the index
        commit, manufacturing the exact skew the durability model forbids. The reflog
        assertions over the mutation cores are the safety net for a call site that forgets to
        log, not an exception from this method.

        **Provisional.** This is the ambient-context shape of the logging entry point, not a
        commitment to ``store.log()`` as the permanent surface: when the transaction API is
        next revised for fan-out/batch mutation or the server, the active-transaction handle
        becomes an explicit parameter and this becomes ``txn.log(...)``. Kept minimal for that
        migration — no overloads, no return value, no extra keyword arguments.
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
        same Layer-1-first ordering as :meth:`transaction`.

        Invalidates any read scope this store filed the same way :meth:`transaction` does —
        unconditionally, in the same ``finally`` that releases Layer 3 — so a read after this
        in the same invocation never serves the pre-rebuild snapshot.
        """
        async with self._loop_lock():
            await _aio.to_thread(self._proc_mutex.acquire)
            try:
                await _aio.to_thread(self._lock.acquire)
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
    """One command invocation's read-side index cache: at most one :class:`SquadsDB` snapshot
    per :class:`IndexStore` instance, keyed on store identity for the same reason
    ``_active_transaction`` is (two stores can legitimately address one squad directory in one
    process, e.g. ``sq repair``, tests).

    ``load()`` is the only consumer — it consults and fills this on the ambient scope's behalf
    (see :func:`read_scope`); :meth:`IndexStore.transaction` never does either. Held inside this
    one object, not as a bare module-level dict, so the whole cache is a single value bound (and
    unbound) by one ``ContextVar``.
    """

    snapshots: dict[IndexStore, SquadsDB] = field(default_factory=dict[IndexStore, SquadsDB])


# Task-local read-scope handle, absent by default. Mirrors ``_active_transaction`` above: one
# module-level ContextVar for one engine-internal, task-local concern. Unlike that one, this is
# opt-in on the *read* side — ``load()`` behaves exactly as it always has when no scope is bound
# (opt-in, and its absence is only ever slow, never wrong), and nothing here changes what
# ``transaction()`` does or reads.
_read_scope: ContextVar[_ReadScope | None] = ContextVar("_read_scope", default=None)


def enter_read_scope() -> Token[_ReadScope | None]:
    """Bind a fresh, empty :class:`_ReadScope` and return the token to undo it with
    (:func:`exit_read_scope`).

    Paired primitives for the one caller that cannot use the :func:`read_scope` context
    manager below: ``_cli/_common.py``'s ``command`` bridge, because Typer's own
    group-resolving callback (e.g. ``@item.callback()``, which resolves ``sq <type> <n>``
    before the verb runs) is *itself* wrapped by ``command`` and crosses the sync/async
    bridge in a separate call from the leaf verb's — two calls, sequential, not nested, so a
    plain ``with`` block opened in the first call cannot still be open in the second. Both
    calls share one Click root ``Context`` for the one real CLI invocation they're both part
    of, so ``command`` opens the scope on the *first* such call and closes it via
    ``ctx.call_on_close`` when that root context finishes — see ``command`` for the full
    mechanism. Prefer plain :func:`read_scope` for anything confined to one call frame
    (tests included).
    """
    return _read_scope.set(_ReadScope())


def exit_read_scope(token: Token[_ReadScope | None]) -> None:
    """Undo a binding made by :func:`enter_read_scope`."""
    _read_scope.reset(token)


@contextlib.contextmanager
def read_scope() -> Generator[None]:
    """Bind a fresh, empty :class:`_ReadScope` for the duration of the block.

    For any use confined to one call frame (every test in this suite that wants one). The
    real CLI's per-invocation scope is opened by ``_cli/_common.py::command`` instead, via
    :func:`enter_read_scope`/:func:`exit_read_scope`, because one CLI invocation can cross this
    module's sync/async bridge more than once (see that pair's docstring) — this simple form
    would tear down and reopen on each crossing, defeating the point.

    Whichever way it's opened, ``load()`` consults the very same ambient scope, and ``sq ui``
    is a sync command that never passes through either — it opts out for free and keeps
    today's per-call-always-fresh behaviour.
    """
    token = enter_read_scope()
    try:
        yield
    finally:
        exit_read_scope(token)
