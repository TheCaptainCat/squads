"""Wall-clock spans of one invocation, written to stderr when ``SQUADS_SPANS`` is non-empty.

A value of the form ``t=<float>`` is a launcher's ``time.perf_counter()`` reading, and ``mark``
times are reported from it; any other value times them from the module's import.
"""

import os
import sys
import time
from collections.abc import Generator
from contextlib import AbstractContextManager, contextmanager, nullcontext

_SWITCH = os.environ.get("SQUADS_SPANS", "")
ENABLED = bool(_SWITCH)


def _origin() -> float:
    if _SWITCH.startswith("t="):
        try:
            return float(_SWITCH[2:])
        except ValueError:
            pass
    return time.perf_counter()


_ORIGIN = _origin()


@contextmanager
def _timed(name: str) -> Generator[None]:
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = (time.perf_counter() - start) * 1000
        print(f"SQUADS_SPAN {name} {elapsed:.2f}", file=sys.stderr)


def span(name: str) -> AbstractContextManager[None]:
    """A context manager that reports how long its body took under *name*; free when off."""
    return _timed(name) if ENABLED else nullcontext()


def mark(name: str) -> None:
    """Report the time since the launcher's reading, or the module's import, under *name*."""
    if not ENABLED:
        return
    print(f"SQUADS_SPAN {name} {(time.perf_counter() - _ORIGIN) * 1000:.2f}", file=sys.stderr)
