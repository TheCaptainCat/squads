"""The schema-migration registry never carries a vocabulary-rename entry: bulk rename is an
on-demand tool distinct from the SCHEMA_VERSION-gated up-chain."""

from squads._migrations._registry import MIGRATIONS
from squads._models._schema import SCHEMA_VERSION, schema_tuple


def test_no_migration_summary_mentions_rename():
    assert not any("rename" in m.summary.lower() for m in MIGRATIONS)


def test_no_registered_migration_targets_past_the_current_schema_version():
    highest = max(schema_tuple(m.to_schema) for m in MIGRATIONS)
    assert highest == schema_tuple(SCHEMA_VERSION)


def test_the_0_15_summary_names_every_body_kind_the_step_actually_reclaims():
    """The migration entry's summary names every body kind the reclaim step touches."""
    entry = next(m for m in MIGRATIONS if m.to_schema == "0.15")
    assert "sq-<type>" in entry.summary
    assert "sq-<type>" in entry.manual


def test_the_0_15_manual_agrees_with_the_docs_on_an_out_of_region_tag():
    """The manual runbook agrees with the docs on an out-of-region tag's real remedy."""
    entry = next(m for m in MIGRATIONS if m.to_schema == "0.15")
    assert "do not run" not in entry.manual.lower()
    assert "nothing to fix here" not in entry.manual.lower()
    assert "delete the out-of-region line" in entry.manual
    assert "sq milestone <n> view add milestone_rollup" in entry.manual
