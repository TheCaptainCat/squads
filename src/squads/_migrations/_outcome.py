"""What one migration runner's ``run`` awaitable resolves to.

A leaf module (no dependency on ``_registry``/``_services``) so both the registry's wiring and
a runner that needs to report more than a count can import it without a cycle.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MigrationOutcome:
    """``count`` is the changed-body count every runner returns, carried in a field rather than as
    the awaitable's bare value. ``skipped`` is the item ids a runner left untouched rather than
    raise on, empty for every runner that never skips
    (:func:`_wrap_sync`/:func:`~squads._migrations._registry._wrap_async` produce this shape from a
    plain-``int`` runner); ``sq migrate up`` prints them by id, and ``sq check`` is the backstop for
    what the list under-reports. ``report`` is printable lines a completed step adds under its own
    line, empty for a runner with nothing to add.
    """

    count: int
    skipped: tuple[str, ...] = ()
    report: tuple[str, ...] = ()
