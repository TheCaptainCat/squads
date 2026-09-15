"""The durable on-disk schema version this code reads and writes.

Single source of truth, kept dependency-free so both the models (`_config`, `_index`) and the
migration registry can import it without an import cycle. Bump it in lock-step with adding a runner
to `squads._migrations._registry`.

While squads is alpha, the schema version tracks the **alpha release that introduced it** (e.g.
``"0.1"`` for the initial shape, ``"0.2"`` for inline ref kinds) rather than an opaque counter.
"""

SCHEMA_VERSION = "0.15"


def schema_tuple(version: str) -> tuple[int, ...]:
    """Parse a dotted schema version (e.g. ``"0.2"``) into ints for ordered comparison."""
    return tuple(int(part) for part in version.split("."))


def version_drifted(current: str, recorded: str) -> bool:
    """Whether *current* (typically the running ``squads.__version__``) is newer than
    *recorded* (typically a squad's stamped ``squads_version``) — the single "is a version-
    drift-gated action due" predicate every caller that gates one shares, so it can be
    reimplemented at most once.

    Compares with :func:`schema_tuple`'s strict, per-segment integer parse, on a **fail-safe**
    direction when that parse fails: either string can carry a pre-release/dev/local suffix
    (``"0.15.0rc1"``) ``schema_tuple`` has no model for and raises ``ValueError`` on, and in
    that case this returns ``True`` rather than refusing to answer. The tolerant alternative —
    stripping non-digits per segment and concatenating the survivors, the shape
    :func:`~squads._util.version_tuple` still uses for the CLI's purely cosmetic drift notice —
    orders a prerelease *above* its own release and *equal to* the next patch, so a squad
    stamped by a prerelease build would read as never-drifted against it. Under-triggering a
    real convergence step that way is worse than the extra, idempotent no-op work
    over-triggering costs, which is why this function (not that one) is what any *gating*
    caller — not merely a cosmetic notice — must use.
    """
    try:
        return schema_tuple(current) > schema_tuple(recorded)
    except ValueError:
        return True
