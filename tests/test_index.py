import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest

from squads._errors import SquadsError
from squads._index._store import IndexStore
from squads._models._enums import ItemType, Status
from squads._models._index import SquadsDB
from squads._models._item import Item


def test_index_keys_items_by_sequence_number():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    it = Item(
        sequence_id=7,
        type=ItemType.TASK,
        title="t",
        slug="t",
        status=Status.DRAFT,
        path="tasks/x.md",
        created_at=now,
        updated_at=now,
    )
    assert it.id == "TASK-000007"  # derived from type + sequence_id
    db = SquadsDB(counter=7)
    db.add(it)
    assert set(db.items) == {7}  # keyed by the int sequence, not the formatted id
    assert db.get("TASK-000007") is it  # lookup by formatted id …
    assert db.get("7") is it  # … or by bare number
    # JSON keys the items by the (stringified) int, and carries sequence_id + the formatted id
    data = json.loads(db.to_json())
    assert set(data["items"]) == {"7"}
    assert data["items"]["7"]["id"] == "TASK-000007"
    assert data["items"]["7"]["sequence_id"] == 7
    # round-trips, and a legacy full-id-keyed index still loads (tolerant validator)
    assert SquadsDB.model_validate_json(db.to_json()).get("TASK-000007") is not None
    legacy = json.dumps({"counter": 7, "items": {"TASK-000007": data["items"]["7"]}})
    assert set(SquadsDB.model_validate_json(legacy).items) == {7}


def test_global_counter_unique_across_types(tmp_path):
    store = IndexStore(tmp_path / ".squads.json", tmp_path / ".squads.json.lock")
    store.create_empty("0.1.0")
    ids = []
    with store.transaction() as db:
        ids.append(db.allocate_id(ItemType.EPIC))
        ids.append(db.allocate_id(ItemType.FEATURE))
        ids.append(db.allocate_id(ItemType.TASK))
    assert ids == ["EPIC-000001", "FEAT-000002", "TASK-000003"]
    numbers = [int(i.rsplit("-", 1)[-1]) for i in ids]
    assert len(set(numbers)) == 3  # no number shared across types


def test_atomic_write_roundtrips_valid_json(tmp_path):
    path = tmp_path / ".squads.json"
    store = IndexStore(path, tmp_path / ".squads.json.lock")
    store.create_empty("0.1.0")
    with store.transaction() as db:
        db.allocate_id(ItemType.BUG)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["counter"] == 1
    SquadsDB.model_validate_json(path.read_text(encoding="utf-8"))  # validates


def test_atomic_write_leaves_no_temp_file(tmp_path):
    # guards the write path: the index commits and the per-pid .tmp is consumed by the rename
    path = tmp_path / ".squads.json"
    store = IndexStore(path, tmp_path / ".squads.json.lock")
    store.create_empty("0.1.0")
    with store.transaction() as db:
        db.allocate_id(ItemType.TASK)
    assert path.is_file()
    assert list(tmp_path.glob("*.tmp")) == []


def test_concurrent_allocation_distinct_ids(tmp_path):
    store = IndexStore(tmp_path / ".squads.json", tmp_path / ".squads.json.lock")
    store.create_empty("0.1.0")

    def alloc(_):
        with store.transaction() as db:
            return db.allocate_id(ItemType.TASK)

    with ThreadPoolExecutor(max_workers=8) as ex:
        ids = list(ex.map(alloc, range(50)))
    assert len(set(ids)) == 50  # lock prevents collisions
    assert store.load().counter == 50


def test_load_wraps_corruption_in_squads_error(tmp_path):
    path = tmp_path / ".squads.json"
    store = IndexStore(path, tmp_path / ".squads.json.lock")
    store.create_empty("0.1.0")
    path.write_text('{"counter": -1}', encoding="utf-8")  # violates ge=0
    with pytest.raises(SquadsError, match="corrupt index"):
        store.load()


def test_backrefs_computed_not_stored(tmp_path):
    store = IndexStore(tmp_path / ".squads.json", tmp_path / ".squads.json.lock")
    db = store.create_empty("0.1.0")
    from datetime import datetime

    from squads._models._item import Item

    now = datetime(2026, 1, 1, tzinfo=UTC)
    a = Item(
        sequence_id=1,
        type=ItemType.TASK,
        title="a",
        slug="a",
        status=Status.DRAFT,
        refs=["GUIDE-000002"],
        path="tasks/a.md",
        created_at=now,
        updated_at=now,
    )
    db.add(a)
    assert db.backrefs("GUIDE-000002") == ["TASK-000001"]
    # nothing backref-shaped persisted
    assert "backrefs" not in db.to_json()
