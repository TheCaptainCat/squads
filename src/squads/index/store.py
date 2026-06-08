"""Locked, atomic read-modify-write access to ``<squad-dir>/.squads.json``.

The single global counter and all item metadata live here. Every mutation goes through a
``transaction()`` guarded by a cross-process file lock and committed with an atomic
``os.replace`` so two concurrent ``sq`` invocations never corrupt the file or collide on IDs.
"""

import contextlib
import os
from collections.abc import Generator
from pathlib import Path

from filelock import FileLock

from squads.models.index import SquadsDB


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
        """Read without locking — for queries (list/show)."""
        return SquadsDB.model_validate_json(self.index_path.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------ transaction
    @contextlib.contextmanager
    def transaction(self) -> Generator[SquadsDB]:
        """Load under the lock, yield the DB to mutate, then atomically write it back.

        If the body raises, nothing is written.
        """
        with self._lock:
            db = self.load()
            yield db
            self._atomic_write(db)

    def overwrite(self, db: SquadsDB) -> None:
        """Replace the whole index under lock (used by ``sq repair``)."""
        with self._lock:
            self._atomic_write(db)

    # ------------------------------------------------------------------ internals
    def _atomic_write(self, db: SquadsDB) -> None:
        tmp = self.index_path.with_suffix(f".json.{os.getpid()}.tmp")
        tmp.write_text(db.to_json() + "\n", encoding="utf-8")
        with open(tmp, "rb") as fh:
            os.fsync(fh.fileno())
        os.replace(tmp, self.index_path)
