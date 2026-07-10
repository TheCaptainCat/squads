"""A pre-badge-collections / legacy-shaped bug's severity lived under `extra`;
`Item.from_frontmatter` backfills it onto the top-level field in memory (and drops the stale
extra copy) so an unmigrated file still reads correctly. The load-boundary integration proof
(via a real index load) lives in tests/integration/test_load_boundary_vocab.py.
"""

from datetime import UTC, datetime

from squads._models._item import Item

_NOW = datetime(2026, 1, 1, tzinfo=UTC).isoformat()


def test_from_frontmatter_backfills_legacy_extra_severity_onto_the_top_level_field():
    data = {
        "id": "BUG-000001",
        "sequence_id": 1,
        "type": "bug",
        "title": "b",
        "status": "Open",
        "extra": {"severity": "critical"},
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    it = Item.from_frontmatter(data, path="bugs/b.md")
    assert it.severity == "critical"
    assert "severity" not in it.extra


def test_a_top_level_severity_wins_over_the_legacy_extra_copy():
    data = {
        "id": "BUG-000001",
        "sequence_id": 1,
        "type": "bug",
        "title": "b",
        "status": "Open",
        "severity": "low",
        "extra": {"severity": "critical"},
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    it = Item.from_frontmatter(data, path="bugs/b.md")
    assert it.severity == "low"
