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


def atomic_replace_sync(path: Path, text: str) -> None:
    """Sync core of the atomic replace: write a temp file in *path*'s own directory, flush,
    ``os.fsync``, then ``os.replace`` onto *path*, with no gap between the fsync and the replace.

    Exposed (not underscored) because a handful of call sites are sync end to end — e.g. the
    override stamp writers, which touch adopter-authored files from a sync CLI command chain,
    and ``IndexStore._atomic_write_sync``, the no-event-loop bootstrap path — and must not have
    to go async just to reach this shape. :func:`atomic_write_text` is this same core, run on a
    worker thread for the async mutation path; both the index and every item ``.md`` write
    funnel through one of these two, so there is exactly one place the temp+fsync+replace shape
    is written down.
    """
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        tmp.replace(path)
    except BaseException:
        # An exception escaping the write (disk full, permission denied, an injected fault)
        # is in-model per the crash model — clean up the temp sibling before re-raising so a
        # failed write doesn't leave a permanent `*.tmp` behind. Process death proper can't
        # run this handler either way; this only helps the cases that *can* run Python.
        tmp.unlink(missing_ok=True)
        raise


async def atomic_write_text(path: Path, text: str) -> None:
    """Atomically replace *path* with *text* — the async wrapper over :func:`atomic_replace_sync`,
    run inside ONE thread hop so no coroutine can interleave between the durability barrier and
    the rename. ``IndexStore._atomic_write`` delegates to this for the index commit; every item
    ``.md`` write goes through it too (via ``_itemfile.py``) — one primitive, not two.

    Contract: after this returns, *path* holds either the complete new text or its complete
    previous bytes — **never** a prefix of either. Does not create parent directories (callers
    needing a new one call :func:`mkdir` first — this primitive has exactly one job) and does
    not collide with a concurrent writer of the same target: the temp name carries the pid and
    thread id.
    """
    await to_thread(lambda: atomic_replace_sync(path, text))


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
