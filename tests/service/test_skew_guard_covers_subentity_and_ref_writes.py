"""The skew guard's coverage on the two write paths not exercised by the metadata/status or
body/comment seams directly: sub-entity block writes (`_write_block_file`) and the ref-add/
remove seam (`_refs.py`) -- both reach the same shared guard, and both refuse a real skew.
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


async def test_adding_a_sub_entity_refuses_on_a_drifted_parent(svc, monkeypatch):
    review = (await create_item(svc, "review", "Drifted review")).item
    await _drift_via_interrupted_index_commit(svc, monkeypatch, review.id)

    with pytest.raises(SquadsError, match="repair"):
        await svc.add_finding(review.id, "a finding")

    await svc.repair()
    result = await svc.add_finding(review.id, "a finding after repair")
    assert result.local_id


async def test_a_sub_entity_status_change_refuses_on_a_drifted_parent(svc, monkeypatch):
    task = (await create_item(svc, "task", "Drifted subtask host")).item
    added = await svc.add_subtask(task.id, "a subtask")
    await _drift_via_interrupted_index_commit(svc, monkeypatch, task.id)

    with pytest.raises(SquadsError, match="repair"):
        await svc.set_subtask_status(task.id, added.local_id, "InProgress")

    await svc.repair()
    await svc.set_subtask_status(task.id, added.local_id, "InProgress")
    final = await svc.get(task.id)
    assert any(s.local_id == added.local_id and s.status == "InProgress" for s in final.subentities)


async def test_adding_a_ref_refuses_on_a_drifted_source_item(svc, monkeypatch):
    a = (await create_item(svc, "task", "Drifted ref source")).item
    b = (await create_item(svc, "task", "Ref target")).item
    await _drift_via_interrupted_index_commit(svc, monkeypatch, a.id)

    with pytest.raises(SquadsError, match="repair"):
        await svc.add_ref(a.id, b.id, kind="related")

    await svc.repair()
    await svc.add_ref(a.id, b.id, kind="related")
    reloaded = await svc.get(a.id)
    assert any(r.startswith(b.id) for r in reloaded.refs)


async def test_removing_a_ref_refuses_on_a_drifted_source_item(svc, monkeypatch):
    a = (await create_item(svc, "task", "Drifted ref remover")).item
    b = (await create_item(svc, "task", "Ref target for removal")).item
    await svc.add_ref(a.id, b.id, kind="related")
    await _drift_via_interrupted_index_commit(svc, monkeypatch, a.id)

    with pytest.raises(SquadsError, match="repair"):
        await svc.rm_ref(a.id, b.id)

    await svc.repair()
    await svc.rm_ref(a.id, b.id)
    reloaded = await svc.get(a.id)
    assert not any(r.startswith(b.id) for r in reloaded.refs)
