"""Observation of item-file writes per unit of work, for the autouse write-once guard.

A *unit* is one ``IndexStore.transaction()`` or one repair rebuild. Within a committed unit
every item file is written at most once, and every item-file write precedes the index commit.
An item file is a ``.md`` file under a directory that holds a ``.squads.json``, outside any
dot-directory; the index and regenerable backend output are not item files.

The ledger is per test, carried by the fixture that installs it: it patches the write funnel
(``_aio.atomic_replace_sync`` and ``_aio.write_text``), the rename primitive and the unit
openers, and keeps the current unit on a stack it owns, so a write made on a worker thread is
attributed to the unit its awaiting coroutine opened.
"""

import contextlib
import sys
from collections import Counter
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from squads import _aio
from squads._index._store import IndexStore
from squads._services._maintenance import MaintenanceMixin

#: Service methods whose unit still writes one item file more than once, each with the reason.
#: A method leaves this table when its fix lands; ``test_*_still_double_writes`` pins the rest.
ALLOWED_DOUBLE_WRITERS: dict[str, str] = {
    "rename_type": "per-item rewrite, id remap and comment are separate writes",
    "_apply_import": "every event writes its own file",
    "rename_status": "frontmatter and comment are separate writes",
}

INDEX_NAME = ".squads.json"


def squad_dir_of(path: Path) -> Path | None:
    """The nearest ancestor of *path* holding an index, or ``None``."""
    return next((p for p in path.parents if (p / INDEX_NAME).exists()), None)


def squad_key(squad_dir: Path) -> Path:
    """The key a squad's unit stack is filed under."""
    return squad_dir.resolve()


def is_item_file(path: Path) -> bool:
    """True when *path* is a ``.md`` file under a squad directory, outside any dot-directory."""
    squad_dir = squad_dir_of(path)
    if path.suffix != ".md" or squad_dir is None:
        return False
    return not any(part.startswith(".") for part in path.relative_to(squad_dir).parts)


@dataclass
class Unit:
    method: str
    counts: Counter[Path] = field(default_factory=Counter)
    index_written: bool = False
    late_item_writes: list[Path] = field(default_factory=list)
    committed: bool = False


class WriteLedger:
    def __init__(self) -> None:
        self.stacks: dict[Path, list[Unit]] = {}
        self.violations: list[str] = []
        #: ``(method, path, count)`` for every committed-unit double write, allowlisted or not.
        self.double_writes: list[tuple[str, Path, int]] = []
        self.seen: Counter[Path] = Counter()
        #: Every committed unit, in the order they finished.
        self.finished: list[Unit] = []

    def _current(self, path: Path) -> Unit | None:
        squad_dir = squad_dir_of(path)
        stack = self.stacks.get(squad_key(squad_dir)) if squad_dir is not None else None
        return stack[-1] if stack else None

    def note_write(self, path: Path) -> None:
        resolved = path.resolve()
        unit = self._current(resolved)
        if resolved.name == INDEX_NAME:
            if unit is not None:
                unit.index_written = True
            return
        if not is_item_file(resolved):
            return
        self.seen[resolved] += 1
        if unit is None:
            return
        if unit.index_written:
            unit.late_item_writes.append(resolved)
        unit.counts[resolved] += 1

    def note_rename(self, old: Path, new: Path) -> None:
        old, new = old.resolve(), new.resolve()
        unit = self._current(new)
        if unit is None:
            return
        counts = unit.counts
        if old in counts:
            counts[new] += counts.pop(old)

    def finish(self, unit: Unit) -> None:
        if not unit.committed:
            return
        self.finished.append(unit)
        for path, n in unit.counts.items():
            if n > 1:
                self.double_writes.append((unit.method, path, n))
                if unit.method not in ALLOWED_DOUBLE_WRITERS:
                    self.violations.append(
                        f"{unit.method}: {path.name} written {n} times in one transaction"
                    )
        for path in unit.late_item_writes:
            self.violations.append(f"{unit.method}: {path.name} written after the index commit")

    def take_violations(self) -> list[str]:
        taken, self.violations = self.violations, []
        return taken

    @contextlib.asynccontextmanager
    async def unit(self, squad_dir: Path, method: str, inner: Any) -> AsyncGenerator[Any]:
        unit = Unit(method)
        stack = self.stacks.setdefault(squad_key(squad_dir), [])
        stack.append(unit)
        try:
            async with inner as value:
                yield value
            unit.committed = True
        finally:
            stack.remove(unit)
            self.finish(unit)


def install(monkeypatch: pytest.MonkeyPatch) -> WriteLedger:
    """Patch the write funnel and the unit openers for the current test; return the ledger."""
    ledger = WriteLedger()

    real_replace: Callable[[Path, str], None] = _aio.atomic_replace_sync
    real_write = _aio.write_text
    real_rename = _aio.path_rename
    real_transaction = IndexStore.transaction
    real_rebuild = MaintenanceMixin._rebuild_index_from_disk  # pyright: ignore[reportPrivateUsage]

    def replace(path: Path, text: str) -> None:
        real_replace(path, text)
        ledger.note_write(path)

    async def write_text(path: Path, text: str) -> None:
        await real_write(path, text)
        ledger.note_write(path)

    async def path_rename(old: Path, new: Path) -> None:
        await real_rename(old, new)
        ledger.note_rename(old, new)

    def transaction(self: IndexStore) -> Any:
        method = sys._getframe(1).f_code.co_name
        return ledger.unit(self.index_path.parent, method, real_transaction(self))

    async def rebuild(self: MaintenanceMixin, *args: Any, **kwargs: Any) -> Any:
        async with ledger.unit(
            self.paths.squad_dir,
            "_rebuild_index_from_disk",
            _Awaited(real_rebuild(self, *args, **kwargs)),
        ) as built:
            return built

    monkeypatch.setattr(_aio, "atomic_replace_sync", replace)
    monkeypatch.setattr(_aio, "write_text", write_text)
    monkeypatch.setattr(_aio, "path_rename", path_rename)
    monkeypatch.setattr(IndexStore, "transaction", transaction)
    monkeypatch.setattr(MaintenanceMixin, "_rebuild_index_from_disk", rebuild)
    return ledger


class _Awaited:
    """Adapts an awaitable to the ``async with`` shape :meth:`WriteLedger.unit` wraps."""

    def __init__(self, awaitable: Any) -> None:
        self._awaitable = awaitable

    async def __aenter__(self) -> Any:
        return await self._awaitable

    async def __aexit__(self, *exc: object) -> None:
        return None
