"""Thin async IO helpers — ``to_thread``-wrapped awaitables over blocking file operations,
the *only* awaitables that touch the filesystem below the CLI edge.

Call sites pass zero-arg lambdas or ``functools.partial`` so the return type ``T`` stays pinned
under pyright strict (positional forms widen ``T`` to ``Any``).

**Not ``anyio.Path``**: its methods widen results to ``Any`` under pyright strict, and
``_store._atomic_write`` needs ``os.fsync`` + ``os.replace`` on one thread hop (no ``await``
between them), which ``anyio.Path`` cannot express.
"""

from collections.abc import Callable
from pathlib import Path

import anyio.to_thread


async def to_thread[T](fn: Callable[[], T]) -> T:
    """Run a zero-arg blocking callable on a worker thread; pin the return type.

    Pass a zero-arg lambda or ``functools.partial`` — positional forms widen ``T`` to ``Any``
    under pyright strict (ADR-000153 §pyright notes).
    """
    return await anyio.to_thread.run_sync(fn)


async def read_text(path: Path) -> str:
    """Read *path* as UTF-8 text on a worker thread."""
    return await to_thread(lambda: path.read_text(encoding="utf-8"))


async def write_text(path: Path, text: str) -> None:
    """Write *text* to *path* as UTF-8 on a worker thread."""
    await to_thread(lambda: path.write_text(text, encoding="utf-8"))


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
