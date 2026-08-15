"""Bulk retype (`rename_type`) and bulk status rename (`rename_status`): the affected set is
known up front, so both pre-flight the frontmatter-skew guard against the whole set and refuse
before their first write -- never mid-flight, which would leave the batch partially applied.
"""

import pytest

from _helpers import create_item
from squads._errors import SquadsError
from squads._index._store import IndexStore

pytestmark = pytest.mark.anyio


async def _drift_via_interrupted_index_commit(svc, monkeypatch, item_id: str) -> None:
    real_atomic_write = IndexStore._atomic_write

    async def _boom(self, db):
        raise OSError("simulated crash during the index commit")

    monkeypatch.setattr(IndexStore, "_atomic_write", _boom)
    with pytest.raises(OSError):
        await svc.update(item_id, description="interrupted description")
    monkeypatch.setattr(IndexStore, "_atomic_write", real_atomic_write)


async def test_bulk_retype_refuses_before_its_first_write_when_one_target_has_drifted(
    svc, monkeypatch
):
    drifted = (await create_item(svc, "task", "Drifted retype target")).item
    healthy = (await create_item(svc, "task", "Healthy retype target")).item
    await _drift_via_interrupted_index_commit(svc, monkeypatch, drifted.id)

    with pytest.raises(SquadsError, match="repair"):
        await svc.rename_type("task", "bug")

    # Every file untouched -- including the healthy one that would have renamed cleanly.
    reloaded_drifted = await svc.get(drifted.id)
    reloaded_healthy = await svc.get(healthy.id)
    assert reloaded_drifted.type == "task"
    assert reloaded_healthy.type == "task"


async def test_bulk_retype_of_a_clean_set_is_unaffected(svc):
    a = (await create_item(svc, "task", "Clean retype A")).item
    b = (await create_item(svc, "task", "Clean retype B")).item

    result = await svc.rename_type("task", "bug")

    assert result.renamed == 2
    reloaded_a = await svc.get(a.id)
    reloaded_b = await svc.get(b.id)
    assert reloaded_a.type == "bug"
    assert reloaded_b.type == "bug"


async def test_bulk_rename_status_refuses_before_its_first_write_when_one_target_has_drifted(
    svc, monkeypatch
):
    drifted = (await create_item(svc, "task", "Drifted rename-status target")).item
    healthy = (await create_item(svc, "task", "Healthy rename-status target")).item
    await _drift_via_interrupted_index_commit(svc, monkeypatch, drifted.id)

    with pytest.raises(SquadsError, match="repair"):
        await svc.rename_status("task", "Draft", "Ready")

    reloaded_drifted = await svc.get(drifted.id)
    reloaded_healthy = await svc.get(healthy.id)
    assert reloaded_drifted.status == "Draft"
    assert reloaded_healthy.status == "Draft"


async def test_bulk_rename_status_of_a_clean_set_is_unaffected(svc):
    a = (await create_item(svc, "task", "Clean rename-status A")).item
    b = (await create_item(svc, "task", "Clean rename-status B")).item

    result = await svc.rename_status("task", "Draft", "Ready")

    assert result.renamed == 2
    reloaded_a = await svc.get(a.id)
    reloaded_b = await svc.get(b.id)
    assert reloaded_a.status == "Ready"
    assert reloaded_b.status == "Ready"
