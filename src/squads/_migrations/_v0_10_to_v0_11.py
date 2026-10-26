"""Schema 0.10 → 0.11 runner: a schema-stamp-only no-op, existing to gate the new ``scopes`` ref
kind (custom-skill role scoping). No frontmatter shape changed: system versus custom skill is
derived from the slug against the active spec and never stamped, and the ``scopes`` edge reuses the
``ID:kind`` ref shape supported since schema 0.2. The hazard is forward compatibility: a pre-0.11
client reading a 0.11 repo would warn "unknown ref kind 'scopes'" and silently ignore the scoping,
so bumping ``SCHEMA_VERSION`` makes the root CLI callback hard-stop it with "run `sq migrate up`".

It touches no file and returns 0; ``run_pending_migrations`` still runs ``repair()`` and stamps
0.11, which rebuilds a correct index from unmodified frontmatter, existing ``scopes`` edges and
authored custom-skill bodies included (repair never reads or rewrites body regions). It runs only
through ``sq migrate up`` via ``_migrations._registry``.
"""

from squads._paths import SquadPaths

MANUAL = ""


def migrate(paths: SquadPaths) -> int:
    """No-op — the 0.11 schema bump is a stamp-only gate, no file rewrite required."""
    _ = paths  # unused — kept for the ``Migration.run`` signature
    return 0
