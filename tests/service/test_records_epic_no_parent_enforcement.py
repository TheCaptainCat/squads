"""The two deliberate new ``no_parent`` enforcements: ``records`` types
(``decision``/``guide``) reject a parent via the category default bundle, and ``epic`` rejects
one via its own ``validators`` addition — both fail-closed at create/link time, and both
flagged by ``sq check`` for a pre-existing violation.
"""

import pytest

from squads._errors import SquadsError

pytestmark = pytest.mark.anyio


async def test_decision_rejects_a_parent_at_create(svc):
    task = (await svc.create("task", "t")).item
    with pytest.raises(SquadsError, match="takes no parent"):
        await svc.create("decision", "d", parent=task.id)


async def test_decision_rejects_a_parent_at_link_time(svc):
    task = (await svc.create("task", "t")).item
    dec = (await svc.create("decision", "d")).item
    with pytest.raises(SquadsError, match="takes no parent"):
        await svc.link(dec.id, task.id)


async def test_guide_rejects_a_parent_at_create(svc):
    task = (await svc.create("task", "t")).item
    with pytest.raises(SquadsError, match="takes no parent"):
        await svc.create("guide", "g", parent=task.id)


async def test_decision_without_a_parent_still_succeeds(svc):
    dec = (await svc.create("decision", "d")).item
    assert dec.parent is None


async def test_guide_without_a_parent_still_succeeds(svc):
    guide = (await svc.create("guide", "g")).item
    assert guide.parent is None


async def test_epic_rejects_a_parent_at_create(svc):
    epic = (await svc.create("epic", "root")).item
    with pytest.raises(SquadsError, match="takes no parent"):
        await svc.create("epic", "sub", parent=epic.id)


async def test_epic_rejects_a_parent_at_link_time(svc):
    epic1 = (await svc.create("epic", "e1")).item
    epic2 = (await svc.create("epic", "e2")).item
    with pytest.raises(SquadsError, match="takes no parent"):
        await svc.link(epic2.id, epic1.id)


async def test_epic_without_a_parent_still_succeeds(svc):
    epic = (await svc.create("epic", "root")).item
    assert epic.parent is None


async def test_check_flags_a_decision_corrupted_to_hold_a_parent(svc):
    task = (await svc.create("task", "t")).item
    dec = (await svc.create("decision", "d")).item
    async with svc.store.transaction() as db:
        db.items[dec.sequence_id].parent = task.id
    issues = await svc.check()
    assert any(i.item == dec.id and "takes no parent" in i.message for i in issues)


async def test_check_flags_an_epic_corrupted_to_hold_a_parent(svc):
    epic1 = (await svc.create("epic", "e1")).item
    epic2 = (await svc.create("epic", "e2")).item
    async with svc.store.transaction() as db:
        db.items[epic2.sequence_id].parent = epic1.id
    issues = await svc.check()
    assert any(i.item == epic2.id and "takes no parent" in i.message for i in issues)
