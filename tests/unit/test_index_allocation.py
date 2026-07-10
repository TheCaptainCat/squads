"""IndexStore allocation math: a single monotonic counter, atomic-write round-tripping, and
clean failure on corruption or exhaustion.

Uses a bare ``IndexStore`` against ``tmp_path`` directly (no ``project``/``svc`` fixture) — the
store's own file/lock plumbing is exactly what's under test here.
"""

import json

import pytest

from squads._errors import SquadsError
from squads._index._store import IndexStore
from squads._models._index import SquadsDB

pytestmark = pytest.mark.anyio


async def test_counter_is_single_and_monotonic_across_every_type(tmp_path):
    """One global counter serves every type — no per-type numbering."""
    store = IndexStore(tmp_path / ".squads.json", tmp_path / ".squads.json.lock")
    store.create_empty("0.1.0")
    async with store.transaction() as db:
        ids = [
            db.allocate_id("epic", prefix="EPIC"),
            db.allocate_id("feature", prefix="FEAT"),
            db.allocate_id("task", prefix="TASK"),
        ]
    assert ids == ["EPIC-000001", "FEAT-000002", "TASK-000003"]
    numbers = [int(i.rsplit("-", 1)[-1]) for i in ids]
    assert len(set(numbers)) == 3


async def test_atomic_write_roundtrips_valid_json_and_leaves_no_temp_file(tmp_path):
    path = tmp_path / ".squads.json"
    store = IndexStore(path, tmp_path / ".squads.json.lock")
    store.create_empty("0.1.0")
    async with store.transaction() as db:
        db.allocate_id("bug")

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["counter"] == 1
    SquadsDB.model_validate_json(path.read_text(encoding="utf-8"))  # validates cleanly
    assert list(tmp_path.glob("*.tmp")) == []


async def test_load_wraps_a_corrupt_index_in_squads_error(tmp_path):
    """A structurally-invalid index (e.g. a negative counter) raises SquadsError, not a raw
    pydantic/JSON exception."""
    path = tmp_path / ".squads.json"
    store = IndexStore(path, tmp_path / ".squads.json.lock")
    store.create_empty("0.1.0")
    path.write_text('{"counter": -1}', encoding="utf-8")  # violates ge=0

    with pytest.raises(SquadsError, match="corrupt index"):
        await store.load()


async def test_allocate_id_raises_a_named_recovery_hint_at_capacity(tmp_path):
    """Exhausting the current padding's id space fails closed and names `sq migrate repad`
    rather than silently wrapping or corrupting the counter."""
    store = IndexStore(tmp_path / ".squads.json", tmp_path / ".squads.json.lock")
    store.create_empty("0.1.0")
    async with store.transaction() as db:
        db.counter = 10**6 - 1  # the last valid id at padding=6

    async with store.transaction() as db:
        with pytest.raises(SquadsError, match="sq migrate repad"):
            db.allocate_id("task")

    assert (await store.load()).counter == 10**6 - 1  # never advanced


def test_format_id_degrades_to_the_unresolved_sentinel_without_a_prefix():
    """With no prefix available, id formatting fails loud-but-graceful — an UNRESOLVED
    sentinel, never a plausible-but-wrong guess (e.g. "decision" -> "DECISION" instead of
    the real "ADR")."""
    from squads._models._item import UNRESOLVED_PREFIX

    db = SquadsDB(padding=6)
    assert db.format_id("decision", 7) == f"{UNRESOLVED_PREFIX}-000007"
