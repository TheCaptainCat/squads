"""The durable on-disk schema version this code reads and writes: the single source of truth,
dependency-free so the models and the migration registry import it without a cycle, bumped in
lock-step with adding a runner to `squads._migrations._registry`. While squads is alpha it is a
dotted string naming the alpha release that introduced it, not an opaque counter.
"""

SCHEMA_VERSION = "0.19"


def schema_tuple(version: str) -> tuple[int, ...]:
    """Parse a dotted schema version (e.g. ``"1.2"``) into ints for ordered comparison."""
    return tuple(int(part) for part in version.split("."))
