"""``sq check`` catches structural corruption that bypasses the normal service API: an index
entry pointing at a parent that no longer exists, and a body whose marker pair was broken by a
direct file edit.
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_check_detects_a_dangling_parent(svc):
    task = (await svc.create("task", "t")).item
    async with svc.store.transaction() as db:
        db.items[task.sequence_id].parent = "FEAT-999999"
    issues = await svc.check()
    assert any("dangling parent" in i.message and i.item == task.id for i in issues)


async def test_check_detects_a_broken_marker(svc):
    task = (await svc.create("task", "t")).item
    path = svc.paths.abspath(task.path)
    text = path.read_text(encoding="utf-8").replace("<!-- sq:body:end -->", "")
    path.write_text(text, encoding="utf-8")
    issues = await svc.check()
    assert any("sq:body" in i.message for i in issues)
