"""Service integration for session lineage: ``create`` records the seeded session on both the
reflog line and the item's frontmatter (``created_session``); ``set_status`` updates
``modified_session`` while leaving ``created_session`` alone; ``read_reflog`` surfaces the
session fields on ``ReflogEntry``; a legacy item with no session fields loads fine; and
``repair`` on a legacy (no-session) item preserves invariant 1 (frontmatter stays the source
of truth) rather than crashing on the missing fields.
"""

import pytest

from squads import _actor as actor
from squads import _aio
from squads import _sections as sections
from squads._index._reflog import read_lines, reflog_path
from squads._index._resolver import item_file
from squads._services._results import ReflogEntry

pytestmark = pytest.mark.anyio

# The session pair is reset before/after every test by the root conftest's autouse
# `_reset_session_seed` — no local leak-guard needed here.


async def test_create_records_the_session_on_the_reflog_line_and_the_item_frontmatter(svc):
    actor.seed_session("sid-create", "sid-parent")
    item = (await svc.create("task", "Session task")).item

    lines = await read_lines(reflog_path(svc.paths.squad_dir))
    create_line = next(ln for ln in lines if ln.op == "create" and ln.target == item.id)
    assert create_line.session_id == "sid-create"
    assert create_line.parent_session_id == "sid-parent"

    loaded = await svc.get(item.id)
    assert loaded.created_session == "sid-create"
    assert loaded.modified_session == "sid-create"


async def test_with_no_session_seeded_the_frontmatter_fields_stay_none(svc):
    item = (await svc.create("task", "No-session task")).item
    loaded = await svc.get(item.id)
    assert loaded.created_session is None
    assert loaded.modified_session is None


async def test_set_status_updates_modified_session_leaving_created_session_alone(svc):
    actor.seed_session("sid-create", None)
    item = (await svc.create("task", "Session update test")).item
    actor.seed_session("sid-modify", None)
    await svc.set_status(item.id, "InProgress")

    loaded = await svc.get(item.id)
    assert loaded.created_session == "sid-create"
    assert loaded.modified_session == "sid-modify"


async def test_read_reflog_surfaces_the_session_fields_on_reflog_entry(svc):
    actor.seed_session("sid-svc", "sid-par")
    item = (await svc.create("task", "Reflog entry session")).item

    entries = await svc.read_reflog(item=item.id, op_filter="create")
    (entry,) = entries
    assert isinstance(entry, ReflogEntry)
    assert entry.session_id == "sid-svc"
    assert entry.parent_session_id == "sid-par"


async def test_a_legacy_item_with_no_session_fields_loads_cleanly(svc):
    item = (await svc.create("task", "Legacy item")).item
    path = item_file(svc.paths, item)
    text = await _aio.read_text(path)
    fm, body = sections.split_frontmatter(text)
    fm.pop("created_session", None)
    fm.pop("modified_session", None)
    await _aio.write_text(path, sections.join_frontmatter(fm, body))

    loaded = await svc.get(item.id)
    assert loaded.created_session is None
    assert loaded.modified_session is None


async def test_repair_on_a_legacy_no_session_item_preserves_invariant_1(svc):
    item = (await svc.create("task", "Repair legacy")).item
    path = item_file(svc.paths, item)
    text = await _aio.read_text(path)
    fm, body = sections.split_frontmatter(text)
    fm.pop("created_session", None)
    fm.pop("modified_session", None)
    await _aio.write_text(path, sections.join_frontmatter(fm, body))

    result = await svc.repair()
    assert len(result.db.items) >= 1
    errors = [i for i in await svc.check() if i.level == "error"]
    assert not errors
