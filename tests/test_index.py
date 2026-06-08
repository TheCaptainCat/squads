import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC

from squads.index import IndexStore
from squads.models import ItemType, SquadsDB


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
    data = json.loads(path.read_text())
    assert data["counter"] == 1
    SquadsDB.model_validate_json(path.read_text())  # validates


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


def test_backrefs_computed_not_stored(tmp_path):
    store = IndexStore(tmp_path / ".squads.json", tmp_path / ".squads.json.lock")
    db = store.create_empty("0.1.0")
    from datetime import datetime

    from squads.models import Item

    now = datetime(2026, 1, 1, tzinfo=UTC)
    a = Item(
        id="TASK-000001",
        type=ItemType.TASK,
        title="a",
        slug="a",
        status="Draft",
        refs=["GUIDE-000002"],
        path="tasks/a.md",
        created_at=now,
        updated_at=now,
    )
    db.add(a)
    assert db.backrefs("GUIDE-000002") == ["TASK-000001"]
    # nothing backref-shaped persisted
    assert "backrefs" not in db.to_json()
