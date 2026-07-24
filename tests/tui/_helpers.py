"""Shared TUI test-only helpers with no production analogue.

Kept separate from a `conftest.py` (fixtures/autouse hooks) since this is a plain importable
function, not a pytest fixture — mirrors the `tests/_helpers.py` convention one level up.
"""

import time
from collections.abc import Callable

from textual.pilot import Pilot


async def wait_until(
    pilot: Pilot[None], predicate: Callable[[], bool], *, max_wait: float = 5.0
) -> None:
    """Poll *predicate* via repeated `pilot.pause()`s until it holds, instead of trusting a
    single pause.

    Two independent bits of app behaviour hand work off the current pilot-visible "settled"
    point: `Markdown.update()` offloads its parse to a thread-pool executor, and
    `SearchScreen._run_search` (a `@work`-decorated, fire-and-forget worker) populates its
    `ListView` on its own schedule. A lone `pilot.pause()` only waits until the process *looks*
    CPU-idle, which under parallel/contended test load can fire before either of those has
    actually finished — so the widget's content (or the scroll container's derived size, or a
    populated results list) isn't settled yet. Polling the real postcondition makes the wait
    deterministic regardless of scheduling.
    """
    deadline = time.monotonic() + max_wait
    while not predicate():
        if time.monotonic() >= deadline:
            raise AssertionError(f"condition not met within {max_wait}s: {predicate!r}")
        await pilot.pause()
