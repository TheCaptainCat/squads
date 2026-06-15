"""Locked, atomic read-modify-write access to ``<squad-dir>/.squads.json``.

The single global counter and all item metadata live here. Every mutation goes through a
``transaction()`` guarded by a cross-process file lock and committed with an atomic
``os.replace`` so two concurrent ``sq`` invocations never corrupt the file or collide on IDs.
"""

import contextlib
import os
import sys
from collections.abc import Generator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from filelock import FileLock
from pydantic import ValidationError

from squads._errors import SquadsError
from squads._models._index import SquadsDB


@dataclass
class _ReflogOp:
    """A reflog entry buffered during a transaction, flushed after the commit."""

    op: str
    target: str
    delta: dict[str, Any]


@dataclass
class _TransactionCtx:
    """Context object yielded by :meth:`IndexStore.transaction`.

    The service layer writes :attr:`reflog_ops` entries to be appended to the reflog
    *after* the index ``os.replace`` commits, while the file lock is still held.
    Reading from :meth:`IndexStore.transaction` gives back the :class:`SquadsDB`; the
    context object is available as ``ctx.db`` for callers that also need the ops channel.
    """

    db: SquadsDB
    reflog_ops: list[_ReflogOp] = field(default_factory=list[_ReflogOp])

    def log(self, op: str, target: str, delta: dict[str, Any]) -> None:
        """Buffer one reflog entry for post-commit append."""
        self.reflog_ops.append(_ReflogOp(op=op, target=target, delta=delta))


class IndexStore:
    def __init__(self, index_path: Path, lock_path: Path, *, lock_timeout: float = 10.0):
        self.index_path = index_path
        self.lock_path = lock_path
        self._lock = FileLock(str(lock_path), timeout=lock_timeout)

    # ------------------------------------------------------------------ create / read
    def create_empty(self, squads_version: str) -> SquadsDB:
        """Write a fresh empty index (used by ``sq init``)."""
        db = SquadsDB(squads_version=squads_version, counter=0)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write(db)
        return db

    def exists(self) -> bool:
        return self.index_path.is_file()

    def load(self) -> SquadsDB:
        """Read without locking — for queries (list/show).

        If the stored counter is below the maximum item sequence number (e.g. due to a hand-edit),
        the counter is silently raised **in memory** so the next allocation cannot reuse a sequence
        number.  The file is left untouched; the corrected value reaches disk only when the next
        ``transaction()`` saves — or when ``sq repair`` is run explicitly.  Allocation still
        happens only inside ``IndexStore.transaction()`` (invariant 2).
        """
        try:
            db = SquadsDB.model_validate_json(self.index_path.read_text(encoding="utf-8"))
        except ValidationError as exc:
            raise SquadsError(
                f"corrupt index {self.index_path.name} ({exc.error_count()} problem(s)); "
                "run `sq repair` to rebuild it from the markdown files"
            ) from exc
        # Guard against a hand-edited or externally-regressed counter (in memory only).
        max_seq = max((item.sequence_id for item in db.items.values()), default=0)
        if db.counter < max_seq:
            db.counter = max_seq
        return db

    # ------------------------------------------------------------------ transaction
    @contextlib.contextmanager
    def transaction(self) -> Generator[SquadsDB]:
        """Load under the lock, yield the DB to mutate, then atomically write it back.

        After the index ``os.replace`` commits, any reflog ops buffered on the transaction
        context are appended to the reflog file (ADR-000117 §1 — append strictly after commit,
        while still holding the lock).  A failed reflog append warns to stderr and never
        rolls back the already-committed mutation.

        If the body raises, nothing is written (neither the index nor the reflog).

        .. note::
            This generator yields the :class:`SquadsDB` directly (not the
            :class:`_TransactionCtx`) so existing callers are unaffected.  Call sites that
            want to buffer reflog ops access the store's ``_current_ctx`` attribute, set on
            ``self`` for the duration of the ``with`` block.
        """
        from squads import _actor as actor
        from squads import _clock as clock
        from squads._index._reflog import append_line, reflog_path

        ctx = _TransactionCtx(db=self.load())
        self._current_ctx: _TransactionCtx | None = ctx  # type: ignore[attr-defined]
        try:
            with self._lock:
                ctx.db = self.load()
                yield ctx.db
                self._atomic_write(ctx.db)

                # --- reflog append: strictly after os.replace, inside the lock ---
                # The index is already committed; per ADR-000117 §1 nothing here may
                # propagate past that commit. append_line swallows its own failures, and
                # this loop is additionally guarded so any unforeseen error degrades to a
                # warning rather than surfacing from an operation the index already applied.
                if ctx.reflog_ops:
                    try:
                        rpath = reflog_path(self.index_path.parent)
                        ts = clock.iso(clock.now())
                        act = actor.current_actor()
                        for entry in ctx.reflog_ops:
                            append_line(
                                rpath,
                                ts=ts,
                                actor=act,
                                op=entry.op,
                                target=entry.target,
                                delta=entry.delta,
                            )
                    except Exception as exc:  # never fail a committed mutation
                        print(
                            f"[squads reflog] warning: reflog append failed after commit: {exc}",
                            file=sys.stderr,
                        )
        finally:
            self._current_ctx = None  # type: ignore[attr-defined]

    def _log(self, op: str, target: str, delta: dict[str, Any]) -> None:
        """Buffer a reflog entry on the active transaction context (no-op outside a transaction).

        Call sites inside ``with self.store.transaction() as db:`` use this so the op is
        captured at the place that knows what changed, and emitted after the commit.
        """
        ctx: _TransactionCtx | None = getattr(self, "_current_ctx", None)
        if ctx is not None:
            ctx.log(op, target, delta)

    def overwrite(self, db: SquadsDB) -> None:
        """Replace the whole index under lock (used by ``sq repair``)."""
        with self._lock:
            self._atomic_write(db)

    # ------------------------------------------------------------------ internals
    def _atomic_write(self, db: SquadsDB) -> None:
        tmp = self.index_path.with_suffix(f".json.{os.getpid()}.tmp")
        # fsync the same (write) handle that wrote the bytes — fsync needs write access on Windows
        # (a read-only handle raises OSError [Errno 9] there).
        with tmp.open("w", encoding="utf-8") as fh:
            fh.write(db.to_json() + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        tmp.replace(self.index_path)
