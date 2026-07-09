"""The durable on-disk schema version this code reads and writes.

Single source of truth, kept dependency-free so both the models (`_config`, `_index`) and the
migration registry can import it without an import cycle. Bump it in lock-step with adding a runner
to `squads._migrations._registry`.

While squads is alpha, the schema version tracks the **alpha release that introduced it** (e.g.
``"0.1"`` for the initial shape, ``"0.2"`` for inline ref kinds) rather than an opaque counter.
"""

SCHEMA_VERSION = "0.8"


def schema_tuple(version: str) -> tuple[int, ...]:
    """Parse a dotted schema version (e.g. ``"0.2"``) into ints for ordered comparison."""
    return tuple(int(part) for part in version.split("."))
