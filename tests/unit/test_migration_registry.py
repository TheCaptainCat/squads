"""The schema-migration registry never carries a vocabulary-rename entry.

Bulk rename (``sq migrate rename-type`` / ``rename-status``) is an on-demand vocabulary tool,
distinct from the SCHEMA_VERSION-gated up-chain — it must never bump SCHEMA_VERSION or appear
in the registry that ``sq migrate up`` walks. This is the registry-shape half of that guarantee;
the "running a rename leaves the on-disk schema_version untouched" half needs a live squad and
lives in tests/integration/test_rename.py.
"""

from squads._migrations._registry import MIGRATIONS
from squads._models._schema import SCHEMA_VERSION, schema_tuple


def test_no_migration_summary_mentions_rename():
    assert not any("rename" in m.summary.lower() for m in MIGRATIONS)


def test_no_registered_migration_targets_past_the_current_schema_version():
    highest = max(schema_tuple(m.to_schema) for m in MIGRATIONS)
    assert highest == schema_tuple(SCHEMA_VERSION)
