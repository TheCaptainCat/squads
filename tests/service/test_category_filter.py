"""``Service.list_items(category=...)`` — the roster/work/records filter axis, composed (AND)
with the existing type/status/badge dimensions.
"""

import pytest

from _helpers import create_item

pytestmark = pytest.mark.anyio


async def test_category_filter_narrows_to_the_matching_types(svc):
    task = (await create_item(svc, "task", "T1")).item
    decision = (await create_item(svc, "decision", "D1")).item

    work_ids = {i.id for i in await svc.list_items(category="work")}
    records_ids = {i.id for i in await svc.list_items(category="records")}

    assert task.id in work_ids and decision.id not in work_ids
    assert decision.id in records_ids and task.id not in records_ids


async def test_category_filter_ands_with_other_dimensions(svc):
    hi = (await create_item(svc, "task", "Hi", priority="high")).item
    lo = (await create_item(svc, "task", "Lo", priority="low")).item
    await create_item(svc, "decision", "D1")

    ids = {i.id for i in await svc.list_items(category="work", badges={"priority": "high"})}
    assert ids == {hi.id}
    assert lo.id not in ids
