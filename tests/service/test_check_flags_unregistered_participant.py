"""``sq check`` warns when an item's stored ``author`` no longer names a registered
participant — e.g. the role that authored it was later removed from the roster.
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_check_flags_an_author_whose_role_was_later_removed(svc):
    task = (await svc.create("task", "t", author="manager")).item
    await svc.remove_item((await svc.get("ROLE-000001")).id)  # drop the manager role

    issues = await svc.check()
    assert any(i.item == task.id and "author" in i.message for i in issues)
