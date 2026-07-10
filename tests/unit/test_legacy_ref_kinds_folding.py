"""A pre-0.2 on-disk shape stored ref kinds in a parallel ``extra.ref_kinds`` map instead of
inline on the ref string itself (``"ID:kind"``). ``Item.from_frontmatter`` folds that legacy
map onto the matching refs transparently (and drops the stale extra key) so an unmigrated file
still reads correctly. The migration-runner half of this same shape (which rewrites the file
on disk) lives in tests/integration/test_migrations.py.
"""

from datetime import UTC, datetime

from squads._models._item import Item

# A real datetime object (not its .isoformat() string) — Item.from_frontmatter accepts either
# shape for created_at/updated_at (_parse_dt's isinstance(datetime) vs isinstance(str) branches);
# this file deliberately uses the object form so both branches get exercised somewhere in the
# new suite (the sibling legacy-severity file uses the string form).
_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_from_frontmatter_folds_a_legacy_ref_kinds_map_onto_the_matching_bare_refs():
    data = {
        "id": "TASK-000001",
        "sequence_id": 1,
        "type": "task",
        "title": "t",
        "status": "Draft",
        "refs": ["GUIDE-000002", "BUG-000003"],
        "extra": {"ref_kinds": {"BUG-000003": "fixes"}, "tech": "py"},
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    it = Item.from_frontmatter(data, path="tasks/t.md")
    assert it.refs == ["GUIDE-000002", "BUG-000003:fixes"]  # folded inline; default stays bare
    assert "ref_kinds" not in it.extra  # legacy key dropped
    assert it.extra == {"tech": "py"}  # other extras preserved
