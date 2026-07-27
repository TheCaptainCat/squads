"""Thin async IO helpers — ``to_thread``-wrapped awaitables over blocking file operations,
the *only* awaitables that touch the filesystem below the CLI edge.

Call sites pass zero-arg lambdas or ``functools.partial`` so the return type ``T`` stays pinned
under pyright strict (positional forms widen ``T`` to ``Any``).

**Not ``anyio.Path``**: its methods widen results to ``Any`` under pyright strict, and
``_store._atomic_write`` needs ``os.fsync`` + ``os.replace`` on one thread hop (no ``await``
between them), which ``anyio.Path`` cannot express.

**Two write shapes, on purpose.** :func:`write_text` is a bare truncate-in-place — legal only
for *regenerable* artifacts (backend pointer files, managed-region files, the squad
``.gitignore``, override stamps): things ``sq sync`` reproduces, where a killed process costs
at worst a re-sync. Every write to squad **data** — item ``.md`` files, board notices, memory
entries, ``.squads.toml`` — must go through :func:`atomic_write_text` instead, so a killed
process can never truncate the one artifact ``sq repair`` has no way to rebuild.
"""

import os
import threading
from collections.abc import Callable
from pathlib import Path

import anyio.to_thread


async def to_thread[T](fn: Callable[[], T]) -> T:
    """Run a zero-arg blocking callable on a worker thread; pin the return type.

    Pass a zero-arg lambda or ``functools.partial`` — positional forms widen ``T`` to ``Any``
    under pyright strict.
    """
    return await anyio.to_thread.run_sync(fn)


async def read_text(path: Path) -> str:
    """Read *path* as UTF-8 text on a worker thread."""
    return await to_thread(lambda: path.read_text(encoding="utf-8"))


async def write_text(path: Path, text: str) -> None:
    """Write *text* to *path* as UTF-8 on a worker thread — truncate-in-place, NOT atomic.

    Legal only for regenerable artifacts (see the module docstring). Squad data must use
    :func:`atomic_write_text`.
    """
    await to_thread(lambda: path.write_text(text, encoding="utf-8"))


async def atomic_write_text(path: Path, text: str) -> None:
    """Atomically replace *path* with *text*: write a temp file in *path*'s own directory,
    flush, ``os.fsync``, then ``os.replace`` onto *path* — all inside ONE thread hop, with no
    ``await`` between the fsync and the replace so no coroutine can interleave between the
    durability barrier and the rename. Mirrors the shape ``IndexStore._atomic_write`` already
    uses for the index.

    Contract: after this returns, *path* holds either the complete new text or its complete
    previous bytes — **never** a prefix of either. Does not create parent directories (callers
    needing a new one call :func:`mkdir` first — this primitive has exactly one job) and does
    not collide with a concurrent writer of the same target: the temp name carries the pid and
    thread id.
    """

    def _write_and_replace() -> None:
        tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        tmp.replace(path)

    await to_thread(_write_and_replace)


async def path_exists(path: Path) -> bool:
    """Return ``True`` if *path* exists (checked on a worker thread)."""
    return await to_thread(lambda: path.exists())


async def path_rename(src: Path, dst: Path) -> None:
    """Rename *src* to *dst* on a worker thread (zero-arg lambda keeps ``T`` pinned)."""
    await to_thread(lambda: src.rename(dst))


async def path_unlink(path: Path, *, missing_ok: bool = False) -> None:
    """Delete *path* on a worker thread."""
    await to_thread(lambda: path.unlink(missing_ok=missing_ok))


async def mkdir(path: Path, *, parents: bool = False, exist_ok: bool = False) -> None:
    """Create directory *path* on a worker thread."""
    await to_thread(lambda: path.mkdir(parents=parents, exist_ok=exist_ok))
