import json
from datetime import UTC, datetime

import anyio
import anyio.lowlevel
import anyio.to_thread
import pytest
from filelock import FileLock, Timeout

from squads._errors import SquadsError
from squads._index._store import IndexStore
from squads._models._enums import ItemType, Status
from squads._models._index import SquadsDB
from squads._models._item import DEFAULT_ID_PADDING, Item, format_item_id

pytestmark = pytest.mark.anyio


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


async def test_global_counter_unique_across_types(tmp_path):
    store = IndexStore(tmp_path / ".squads.json", tmp_path / ".squads.json.lock")
    store.create_empty("0.1.0")
    ids = []
    async with store.transaction() as db:
        ids.append(db.allocate_id(ItemType.EPIC))
        ids.append(db.allocate_id(ItemType.FEATURE))
        ids.append(db.allocate_id(ItemType.TASK))
    assert ids == ["EPIC-000001", "FEAT-000002", "TASK-000003"]
    numbers = [int(i.rsplit("-", 1)[-1]) for i in ids]
    assert len(set(numbers)) == 3  # no number shared across types


async def test_atomic_write_roundtrips_valid_json(tmp_path):
    path = tmp_path / ".squads.json"
    store = IndexStore(path, tmp_path / ".squads.json.lock")
    store.create_empty("0.1.0")
    async with store.transaction() as db:
        db.allocate_id(ItemType.BUG)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["counter"] == 1
    SquadsDB.model_validate_json(path.read_text(encoding="utf-8"))  # validates


async def test_atomic_write_leaves_no_temp_file(tmp_path):
    # guards the write path: index commits and the .pid.tid.tmp is consumed by the rename
    path = tmp_path / ".squads.json"
    store = IndexStore(path, tmp_path / ".squads.json.lock")
    store.create_empty("0.1.0")
    async with store.transaction() as db:
        db.allocate_id(ItemType.TASK)
    assert path.is_file()
    assert list(tmp_path.glob("*.tmp")) == []


async def test_concurrent_allocation_distinct_ids(tmp_path):
    """Concurrent allocations from separate threads use distinct IDs.

    Each thread runs its own anyio event loop: thread-level parallelism + file-lock exclusion.
    """
    from concurrent.futures import ThreadPoolExecutor

    store = IndexStore(tmp_path / ".squads.json", tmp_path / ".squads.json.lock")
    store.create_empty("0.1.0")

    def alloc(_: int) -> str:
        async def _do() -> str:
            async with store.transaction() as db:
                return db.allocate_id(ItemType.TASK)

        return anyio.run(_do)

    with ThreadPoolExecutor(max_workers=8) as ex:
        ids = list(ex.map(alloc, range(50)))
    assert len(set(ids)) == 50  # lock prevents collisions
    assert (await store.load()).counter == 50


async def test_load_wraps_corruption_in_squads_error(tmp_path):
    path = tmp_path / ".squads.json"
    store = IndexStore(path, tmp_path / ".squads.json.lock")
    store.create_empty("0.1.0")
    path.write_text('{"counter": -1}', encoding="utf-8")  # violates ge=0
    with pytest.raises(SquadsError, match="corrupt index"):
        await store.load()


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


# --------------------------------------------------------------------------- padding / FEAT-000027


def test_padding_defaults_to_six_and_is_persisted(tmp_path):
    """SquadsDB.padding defaults to DEFAULT_ID_PADDING (6) and round-trips through JSON."""
    assert DEFAULT_ID_PADDING == 6
    store = IndexStore(tmp_path / ".squads.json", tmp_path / ".squads.json.lock")
    db = store.create_empty("0.1.0")
    assert db.padding == DEFAULT_ID_PADDING
    data = json.loads(db.to_json())
    assert data["padding"] == DEFAULT_ID_PADDING
    assert SquadsDB.model_validate_json(db.to_json()).padding == DEFAULT_ID_PADDING


def test_format_item_id_uses_requested_width():
    """format_item_id() produces the correct zero-padded ID at any width."""
    assert format_item_id("TASK", 7) == "TASK-000007"  # default width 6
    assert format_item_id("TASK", 7, 6) == "TASK-000007"
    assert format_item_id("TASK", 7, 7) == "TASK-0000007"
    assert format_item_id("FEAT", 1, 4) == "FEAT-0001"


def test_db_format_id_uses_stored_padding():
    """SquadsDB.format_id() routes through the stored padding."""
    db6 = SquadsDB(padding=6)
    assert db6.format_id(ItemType.TASK, 7) == "TASK-000007"
    db7 = SquadsDB(padding=7)
    assert db7.format_id(ItemType.TASK, 7) == "TASK-0000007"


async def test_allocate_id_uses_stored_padding(tmp_path):
    """allocate_id() honours the stored padding when formatting the returned ID."""
    store = IndexStore(tmp_path / ".squads.json", tmp_path / ".squads.json.lock")
    store.create_empty("0.1.0")
    async with store.transaction() as db:
        db.padding = 7
        item_id = db.allocate_id(ItemType.TASK)
    assert item_id == "TASK-0000001"
    assert (await store.load()).counter == 1


async def test_allocate_id_raises_index_full_at_capacity(tmp_path):
    """allocate_id() raises SquadsError naming sq migrate repad when the counter hits capacity."""
    store = IndexStore(tmp_path / ".squads.json", tmp_path / ".squads.json.lock")
    store.create_empty("0.1.0")
    # Set the counter to the max value for padding=6 (999_999 IDs used up).
    async with store.transaction() as db:
        db.counter = 10**6 - 1  # 999_999 — the last valid ID
    # One more allocation must fail.
    async with store.transaction() as db:
        with pytest.raises(SquadsError, match="sq migrate repad"):
            db.allocate_id(ItemType.TASK)
    # Counter must not have advanced.
    assert (await store.load()).counter == 10**6 - 1


def test_item_id_field_not_persisted_in_json():
    """id_padding is excluded from Item JSON/frontmatter serialisation."""
    now = datetime(2026, 1, 1, tzinfo=UTC)
    item = Item(
        sequence_id=1,
        type=ItemType.TASK,
        title="t",
        slug="t",
        status=Status.DRAFT,
        path="tasks/x.md",
        created_at=now,
        updated_at=now,
        id_padding=7,
    )
    assert item.id == "TASK-0000001"  # uses the threaded padding
    dumped = json.loads(item.model_dump_json())
    assert "id_padding" not in dumped  # never persisted
    fm = item.to_frontmatter_dict()
    assert "id_padding" not in fm  # never in frontmatter
    assert fm["id"] == "TASK-0000001"


# --------------------------------------------------------------------------- width-tolerant IDs


def _make_item(seq: int, item_type: ItemType, refs: list[str] | None = None) -> Item:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    return Item(
        sequence_id=seq,
        type=item_type,
        title=f"item {seq}",
        slug=f"item-{seq}",
        status=Status.DRAFT,
        refs=refs or [],
        path=f"{item_type.folder}/{item_type.prefix}-{seq:06d}-item-{seq}.md",
        created_at=now,
        updated_at=now,
    )


def test_propagate_padding_sets_id_padding_on_all_items():
    """SquadsDB._propagate_padding runs after load and sets id_padding on all items."""
    # Build a db at width-7 with an item that would default to id_padding=6.
    db = SquadsDB(padding=7)
    item = _make_item(1, ItemType.TASK)
    assert item.id_padding == 6  # Item default
    db.add(item)
    # After round-tripping through JSON (which excludes id_padding), _propagate_padding fires.
    reloaded = SquadsDB.model_validate_json(db.to_json())
    assert reloaded.padding == 7
    assert reloaded.items[1].id_padding == 7
    assert reloaded.items[1].id == "TASK-0000001"  # display uses current width


def test_backrefs_width_tolerant():
    """backrefs() matches old-width ref strings against current-width item IDs.

    Simulates a squad repadded to width-7: the stored ref "FEAT-000002" (old width) must
    match backrefs("FEAT-0000002") (new width).  The DB is round-tripped through JSON to
    trigger _propagate_padding — the same path used by store.load().
    """
    # item 1 (TASK) refs item 2 (FEAT) using the old width-6 string.
    task = _make_item(1, ItemType.TASK, refs=["FEAT-000002"])
    feat = _make_item(2, ItemType.FEATURE)
    db = SquadsDB(padding=7, counter=2)  # squad repadded to width-7
    db.add(task)
    db.add(feat)
    # Round-trip through JSON to simulate store.load(); _propagate_padding fires and sets
    # id_padding=7 on all items.
    db = SquadsDB.model_validate_json(db.to_json())
    assert db.items[2].id == "FEAT-0000002"
    # backrefs("FEAT-0000002") must find the TASK whose ref holds "FEAT-000002" (old width).
    result = db.backrefs("FEAT-0000002")
    assert result == ["TASK-0000001"]


def test_backrefs_no_cross_type_false_positive():
    """backrefs() does not cross-match when two items share a sequence number (collision)."""
    # Two items both at seq=3 but different types — a collision state before renumber.
    bug = _make_item(3, ItemType.BUG)
    task = _make_item(1, ItemType.TASK, refs=["BUG-000003"])
    db = SquadsDB(padding=6, counter=3)
    # In a collision, the index can only hold one item at seq=3 (BUG wins here).
    db.add(bug)
    db.add(task)
    # backrefs on the FEAT at seq=3 must NOT match the "BUG-000003" ref in task.
    assert db.backrefs("FEAT-000003") == []
    # backrefs on the BUG at seq=3 DOES match.
    assert db.backrefs("BUG-000003") == ["TASK-000001"]


def test_db_get_width_tolerant():
    """SquadsDB.get() resolves any zero-pad width to the correct item."""
    item = _make_item(7, ItemType.TASK)
    db = SquadsDB(padding=7, counter=7)
    db.add(item)
    # Both old and new width resolve to the same item.
    assert db.get("TASK-000007") is db.items[7]
    assert db.get("TASK-0000007") is db.items[7]
    assert db.get("TASK-00000007") is db.items[7]


# --------------------------------------------------------------------------- locking


async def test_locking_timeout_propagates(tmp_path):
    """A competing FileLock forces filelock.Timeout through the async transaction (F6,
    REV-000154)."""
    store = IndexStore(tmp_path / ".squads.json", tmp_path / ".squads.json.lock")
    store.create_empty("0.1.0")

    # Hold the lock with a separate FileLock instance (simulates another process).
    competing = FileLock(str(tmp_path / ".squads.json.lock"), timeout=0)
    competing.acquire()
    try:
        # The async transaction uses a very short timeout so it fires quickly.
        fast_store = IndexStore(
            tmp_path / ".squads.json", tmp_path / ".squads.json.lock", lock_timeout=0.1
        )
        with pytest.raises(Timeout):
            async with fast_store.transaction() as db:
                _ = db  # pragma: no cover — acquire must fail before yielding
    finally:
        competing.release()


async def test_concurrent_coroutines_allocate_distinct_ids(tmp_path):
    """Concurrent coroutines on one event loop must allocate distinct IDs (F1, REV-000154).

    Exercises Layer 1 (per-loop ``anyio.Lock``, ADR-000153 Decision 2). Forcing the thread
    limiter to 1 token makes a single-layer implementation fail deterministically: every
    coroutine's ``acquire`` lands on the one reused worker thread, sees the file lock as a
    reentrant no-op, and enters the critical section simultaneously.
    """
    store = IndexStore(tmp_path / ".squads.json", tmp_path / ".squads.json.lock")
    store.create_empty("0.1.0")

    N = 8
    ids: list[str] = []

    # Force thread limiter to 1 token so all threaded acquire/release calls share ONE worker
    # thread — this is the exact condition that exposes the single-layer race.
    limiter = anyio.to_thread.current_default_thread_limiter()
    original_tokens = limiter.total_tokens
    limiter.total_tokens = 1
    try:

        async def allocate() -> None:
            async with store.transaction() as db:
                ids.append(db.allocate_id(ItemType.TASK))
                # Yield inside the held lock so the event loop can schedule another coroutine —
                # this is what forces thread-reuse and triggers the race in a single-layer model.
                await anyio.lowlevel.checkpoint()

        async with anyio.create_task_group() as tg:
            for _ in range(N):
                tg.start_soon(allocate)
    finally:
        limiter.total_tokens = original_tokens

    assert len(set(ids)) == N, f"duplicate IDs allocated: {ids}"
    assert (await store.load()).counter == N
