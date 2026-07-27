"""The service-level mutation call sites that write an item `.md` -- the shared section-edit
core (comments), the sub-entity block writer, and the rename/retype comment appends -- all go
through the item-file layer's atomic writers, never the bare truncate-in-place `_aio.write_text`
directly.

`test_item_file_writes_route_through_the_atomic_primitive.py` already pins this one level down,
for `_itemfile.py`'s own functions in isolation. This file pins it one level up: that these
service methods actually reach that layer rather than some other path, so a future edit that
imports `_aio.write_text` straight into `_base.py`/`_subentities.py`/`_rename.py`/`_retype.py`
(bypassing the item-file layer) fails a test instead of silently reintroducing a truncating
write on any of these routes.
"""

import pytest

from squads import _aio

pytestmark = pytest.mark.anyio


async def _fail_if_reached(path, text):
    raise AssertionError(f"non-atomic _aio.write_text was called for {path}")


async def test_commenting_never_reaches_the_plain_write(svc, monkeypatch):
    task = (await svc.create("task", "Comment target")).item
    monkeypatch.setattr(_aio, "write_text", _fail_if_reached)

    await svc.comment(task.id, ["a note on the record"], as_slug="manager")

    comments = await svc.comments(task.id)
    assert any("a note on the record" in c.body for c in comments)


async def test_adding_a_sub_entity_block_never_reaches_the_plain_write(svc, monkeypatch):
    review = (await svc.create("review", "Review target")).item
    monkeypatch.setattr(_aio, "write_text", _fail_if_reached)

    result = await svc.add_finding(review.id, "A finding")

    assert result.local_id
    item = await svc.get(review.id)
    assert any(s.local_id == result.local_id for s in item.subentities)


async def test_retyping_an_item_never_reaches_the_plain_write(svc, monkeypatch):
    task = (await svc.create("task", "Retype target")).item
    monkeypatch.setattr(_aio, "write_text", _fail_if_reached)

    result = await svc.retype(task.id, "bug")

    assert result.item.type == "bug"
    item = await svc.get(result.item.id)
    assert item.type == "bug"


async def test_bulk_renaming_a_status_never_reaches_the_plain_write(svc, monkeypatch):
    task = (await svc.create("task", "Rename-status target")).item
    monkeypatch.setattr(_aio, "write_text", _fail_if_reached)

    result = await svc.rename_status("task", "Draft", "Ready")

    assert result.renamed == 1
    item = await svc.get(task.id)
    assert item.status == "Ready"
