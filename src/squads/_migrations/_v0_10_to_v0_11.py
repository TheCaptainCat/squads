"""Schema 0.10 → 0.11 runner: a schema-stamp-only no-op.

This migration exists purely to gate the new ``scopes`` ref kind (custom-skill role scoping):
no frontmatter **shape** changed. The classification of a skill as system vs. custom is derived
from its slug against the active spec, never stamped, so there is nothing to backfill; the
``scopes`` edge reuses the existing ``ID:kind`` ref shape supported since schema 0.2.

The one forward-compatibility hazard is the new ``scopes`` kind itself: a pre-0.11 client
reading a 0.11 repo would ``sq check``-warn "unknown ref kind 'scopes'" and silently ignore the
scoping. Bumping ``SCHEMA_VERSION`` makes the root CLI callback hard-stop that old client with
"run `sq migrate up`" instead of letting it mishandle the edge.

**No existing file needs to be modified** — this runner touches no files and returns 0.
``run_pending_migrations`` (``_services/_maintenance.py``) still runs ``repair()`` and stamps
0.11 as usual; that alone reconstructs a correct index from unmodified frontmatter, including any
pre-existing ``scopes`` edges and authored custom-skill bodies (repair never reads or rewrites
body regions).

Invoked by ``sq migrate up`` via ``_migrations._registry`` — never run directly (this module is
private).
"""

from squads._paths import SquadPaths

MANUAL = ""


def migrate(paths: SquadPaths) -> int:
    """No-op — the 0.11 schema bump is a stamp-only gate, no file rewrite required."""
    _ = paths  # unused — kept for the ``Migration.run`` signature
    return 0
