"""What one migration runner's ``run`` awaitable resolves to.

A leaf module (no dependency on ``_registry``/``_services``) so both the registry's wiring and
a runner that needs to report more than a count can import it without a cycle.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MigrationOutcome:
    """``count`` is the changed-body count every runner has always returned — unchanged
    semantics, now carried in a field rather than as the awaitable's own bare value.

    ``skipped`` is the item ids a runner chose to leave untouched rather than raise on —
    empty for every runner that never skips (every existing runner: :func:`_wrap_sync`/
    :func:`~squads._migrations._registry._wrap_async` produce this shape from one that still
    speaks the plain ``int`` contract, so none of them had to widen their own return type to
    report it). ``sq migrate up`` prints these by id alongside the count; ``sq check``'s own
    advisories are the standing backstop for whatever this list under-reports.
    """

    count: int
    skipped: tuple[str, ...] = ()
