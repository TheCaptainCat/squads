"""Filename padding: default width, persistence, and the id-formatting math it drives.

The filesystem side of a real repad (renaming files, byte-identical bodies, ``sq check``
staying clean) needs a live squad and lives in tests/integration/test_repad.py.
"""

from squads._index._store import IndexStore
from squads._models._index import SquadsDB
from squads._models._item import DEFAULT_ID_PADDING, format_item_id


def test_padding_defaults_to_six_and_round_trips_through_json(tmp_path):
    assert DEFAULT_ID_PADDING == 6
    store = IndexStore(tmp_path / ".squads.json", tmp_path / ".squads.json.lock")
    db = store.create_empty("0.1.0")
    assert db.padding == DEFAULT_ID_PADDING
    data = SquadsDB.model_validate_json(db.to_json())
    assert data.padding == DEFAULT_ID_PADDING


def test_format_item_id_uses_the_requested_width():
    assert format_item_id("TASK", 7) == "TASK-000007"  # default width 6
    assert format_item_id("TASK", 7, 6) == "TASK-000007"
    assert format_item_id("TASK", 7, 7) == "TASK-0000007"
    assert format_item_id("FEAT", 1, 4) == "FEAT-0001"


def test_db_format_id_routes_through_the_stored_padding():
    db6 = SquadsDB(padding=6)
    assert db6.format_id("task", 7, prefix="TASK") == "TASK-000007"
    db7 = SquadsDB(padding=7)
    assert db7.format_id("task", 7, prefix="TASK") == "TASK-0000007"


def test_item_id_always_renders_unpadded_regardless_of_stored_padding():
    """Display padding is a fixed constant — SquadsDB.padding only ever governs filenames."""
    from datetime import UTC, datetime

    from squads._models._item import Item

    now = datetime(2026, 1, 1, tzinfo=UTC)
    item = Item(
        sequence_id=1,
        type="task",
        prefix="TASK",
        title="t",
        slug="t",
        status="Draft",
        path="tasks/x.md",
        created_at=now,
        updated_at=now,
    )
    assert item.id == "TASK-1"
    fm = item.to_frontmatter_dict()
    assert "id_padding" not in fm
    assert fm["id"] == "TASK-1"

    db = SquadsDB(padding=7)
    db.add(item)
    reloaded = SquadsDB.model_validate_json(db.to_json())
    assert reloaded.padding == 7
    assert reloaded.items[1].id == "TASK-1"  # still unpadded
