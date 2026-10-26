"""Thin async IO helpers: ``to_thread``-wrapped awaitables over blocking file operations.

They are the only awaitables that touch the filesystem below the CLI edge. Call sites pass
zero-arg lambdas or ``functools.partial`` so the return type ``T`` stays pinned under pyright
strict (positional forms widen it to ``Any``). ``anyio.Path`` is not used: its methods widen
results to ``Any``, and ``_store._atomic_write`` needs ``os.fsync`` and ``os.replace`` on one
thread hop with no ``await`` between them.

There are two write shapes on purpose. :func:`write_text` is a bare truncate-in-place, legal
only for regenerable artifacts (backend pointers, managed-region files, the squad
``.gitignore``, override stamps) that ``sq sync`` reproduces. Every write to squad data (item
``.md`` files, board notices, memory entries, ``.squads.toml``) goes through
:func:`atomic_write_text`, so a killed process never truncates what ``sq repair`` cannot
rebuild.
"""

import os
import threading
from collections.abc import Callable
from pathlib import Path

import anyio.to_thread

from squads._errors import UndecodableFileError, UnreadableFileError


async def to_thread[T](fn: Callable[[], T]) -> T:
    """Run a zero-arg blocking callable on a worker thread; pin the return type.

    Pass a zero-arg lambda or ``functools.partial`` — positional forms widen ``T`` to ``Any``
    under pyright strict.
    """
    return await anyio.to_thread.run_sync(fn)


async def read_text(path: Path, *, verbatim: bool = False) -> str:
    """Read *path* as UTF-8 text on a worker thread, with every line ending read as LF.

    A writer that must restore untouched lines byte for byte passes ``verbatim=True`` to get the
    file's own endings (the item-file write seam compares its new text with them).

    Raises :class:`~squads._errors.UndecodableFileError` (naming *path* and the failing byte
    offset) on invalid UTF-8, and :class:`~squads._errors.UnreadableFileError` (naming the OS
    error) when the file exists but the read is refused. Nearly every reader in the product (item
    files, board notices, memory entries, override templates, the reflog, migration runners) goes
    through here, so one guard covers them.

    It does not catch ``FileNotFoundError``: ``_services/_check.py``'s confirm round and
    ``_services/_import.py``'s pre-pass read a missing file as a signal and rely on it
    propagating. Callers wanting a clean not-found error convert it at their own seam.
    """
    try:
        return await to_thread(
            lambda: path.read_text(encoding="utf-8", newline="" if verbatim else None)
        )
    except UnicodeDecodeError as exc:
        bad_byte = exc.object[exc.start]
        raise UndecodableFileError(
            f"{path} is not valid UTF-8: byte {bad_byte:#04x} at offset {exc.start} — {exc.reason}"
        ) from exc
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise UnreadableFileError(f"{path} could not be read: {exc.strerror or exc}") from exc


async def read_bytes(path: Path) -> bytes:
    """Read *path* as raw bytes on a worker thread."""
    return await to_thread(path.read_bytes)


async def write_text(path: Path, text: str) -> None:
    """Write *text* to *path* as UTF-8 on a worker thread — truncate-in-place, NOT atomic.

    Legal only for regenerable artifacts (see the module docstring). Squad data must use
    :func:`atomic_write_text`.
    """
    await to_thread(lambda: path.write_text(text, encoding="utf-8", newline=""))


def atomic_replace_sync(path: Path, text: str) -> None:
    """Sync core of the atomic replace: temp file beside *path*, flush, fsync, ``os.replace``.

    There is no gap between the fsync and the replace. It is public because some call sites are
    sync end to end (the override stamp writers, ``IndexStore._atomic_write_sync`` on the
    no-event-loop bootstrap path). :func:`atomic_write_text` runs this same core on a worker thread,
    so the index and every item ``.md`` write share this one temp+fsync+replace shape.
    """
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        with tmp.open("w", encoding="utf-8", newline="") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        tmp.replace(path)
    except BaseException:
        # A failure that can still run Python (disk full, permission denied, an injected fault)
        # must not leave a permanent `*.tmp` behind; process death never reaches this handler.
        tmp.unlink(missing_ok=True)
        raise


async def atomic_write_text(path: Path, text: str) -> None:
    """Atomically replace *path* with *text*, in one thread hop over :func:`atomic_replace_sync`.

    No coroutine can interleave between the durability barrier and the rename.
    ``IndexStore._atomic_write`` and every item ``.md`` write (via ``_itemfile.py``) use it. After
    it returns, *path* holds either the complete new text or its complete previous bytes, never a
    prefix. It does not create parent directories (call :func:`mkdir` first) and does not collide
    with a concurrent writer of the same target, since the temp name carries the pid and thread id.
    """
    await to_thread(lambda: atomic_replace_sync(path, text))


async def path_exists(path: Path) -> bool:
    """Return ``True`` if *path* exists (checked on a worker thread)."""
    return await to_thread(lambda: path.exists())


async def path_is_symlink(path: Path) -> bool:
    """Whether *path* is itself a symlink dirent, not whether its target exists.

    ``Path.is_symlink()`` uses ``lstat``, so it is ``True`` for a broken symlink, unlike
    :func:`path_exists`, which follows the link. A caller uses it after ``read_text`` raises
    ``FileNotFoundError`` on a dirent its own glob just saw: a broken symlink is a present file
    (the read failed on its target), while a dirent that vanished between glob and read is not.
    See ``_services/_maintenance.py``, ``_board/_store.py`` and ``_memory/_store.py``.
    """
    return await to_thread(lambda: path.is_symlink())


async def path_rename(src: Path, dst: Path) -> None:
    """Rename *src* to *dst* on a worker thread (zero-arg lambda keeps ``T`` pinned)."""
    await to_thread(lambda: src.rename(dst))


async def path_unlink(path: Path, *, missing_ok: bool = False) -> None:
    """Delete *path* on a worker thread."""
    await to_thread(lambda: path.unlink(missing_ok=missing_ok))


async def mkdir(path: Path, *, parents: bool = False, exist_ok: bool = False) -> None:
    """Create directory *path* on a worker thread."""
    await to_thread(lambda: path.mkdir(parents=parents, exist_ok=exist_ok))
