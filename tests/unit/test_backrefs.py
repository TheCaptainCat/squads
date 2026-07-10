"""Backrefs are computed by inversion, never persisted, and resolve width/type-tolerantly.

The post-repad re-verification of the same width-tolerance claim is deliberately not repeated
here as a second test — it's the same invariant proven again at a higher layer for a different
trigger (see tests/integration/test_repad.py), not a distinct fact.
"""

from datetime import UTC, datetime

from _helpers import BUILTIN_FOLDER, BUILTIN_PREFIX
from squads._models._index import SquadsDB
from squads._models._item import Item

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _make_item(seq: int, item_type: str, refs: list[str] | None = None) -> Item:
    prefix = BUILTIN_PREFIX[item_type]
    return Item(
        sequence_id=seq,
        type=item_type,
        prefix=prefix,
        title=f"item {seq}",
        slug=f"item-{seq}",
        status="Draft",
        refs=refs or [],
        path=f"{BUILTIN_FOLDER[item_type]}/{prefix}-{seq:06d}-item-{seq}.md",
        created_at=_NOW,
        updated_at=_NOW,
    )


def test_backrefs_are_computed_by_inversion_and_never_persisted():
    db = SquadsDB(counter=2)
    db.add(_make_item(1, "task", refs=["FEAT-000002"]))
    db.add(_make_item(2, "feature"))
    assert db.backrefs("FEAT-000002") == ["TASK-1"]
    assert "backrefs" not in db.to_json()


def test_backrefs_resolve_a_query_at_any_width_including_the_unpadded_display_id():
    """A ref stored at one width must be found whether the query uses that width, a
    different width, or the unpadded display id — resolution is by (prefix, sequence_id),
    never the literal string."""
    task = _make_item(1, "task", refs=["FEAT-000002"])
    feat = _make_item(2, "feature")
    db = SquadsDB(padding=7, counter=2)
    db.add(task)
    db.add(feat)
    db = SquadsDB.model_validate_json(db.to_json())  # round-trip like a real store.load()

    for query in ("FEAT-0000002", "FEAT-000002", "FEAT-2"):
        assert db.backrefs(query) == ["TASK-1"], query


def test_backrefs_do_not_cross_match_a_different_type_at_the_same_sequence_number():
    """Two items sharing a sequence number (a pre-repair collision) must not cross-match."""
    bug = _make_item(3, "bug")
    task = _make_item(1, "task", refs=["BUG-000003"])
    db = SquadsDB(padding=6, counter=3)
    db.add(bug)
    db.add(task)

    assert db.backrefs("FEAT-000003") == []  # no FEAT at seq 3 — must not match the BUG ref
    assert db.backrefs("BUG-000003") == ["TASK-1"]
