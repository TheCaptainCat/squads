"""Schema 0.16 → 0.17 runner: the release's one migration step, which rewrites nothing.

The 0.17 schema adds the Noted and Deferred finding states, which no 0.16 file can hold; the bump
exists so an older release stops at the schema gate with an upgrade message once a squad is
stamped 0.17. Invoked by ``sq migrate up`` via ``_migrations._registry`` — never run directly
(this module is private).
"""

from squads._migrations._context import MigrationContext
from squads._migrations._outcome import MigrationOutcome

MANUAL = ""
SUMMARY = "Stamps the schema; no item file changes."


async def migrate(ctx: MigrationContext) -> MigrationOutcome:
    """Report a zero-count step: ``sq migrate up`` repairs and stamps the schema itself."""
    del ctx
    return MigrationOutcome(count=0)
