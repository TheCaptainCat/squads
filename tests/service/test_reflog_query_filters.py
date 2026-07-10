"""``svc.read_reflog``'s query surface: no reflog file returns empty (never an error), a
truncated trailing line is tolerated (good entries still returned), entries come back as typed
``ReflogEntry`` values, and ``--item``/``--actor``/``--op``/``--since``/``tail`` each filter
correctly — including two filters combined at once (AND semantics), which no prior test drove.
"""

import pytest

from squads import _actor as actor
from squads._index._reflog import reflog_path
from squads._services._results import ReflogEntry

pytestmark = pytest.mark.anyio


async def test_no_reflog_file_returns_empty_never_an_error(svc):
    rpath = reflog_path(svc.paths.squad_dir)
    if rpath.exists():
        rpath.unlink()
    assert await svc.read_reflog() == []


async def test_a_truncated_trailing_line_is_tolerated_and_good_entries_still_return(svc):
    await svc.create("task", "T")
    rpath = reflog_path(svc.paths.squad_dir)
    with rpath.open("a", encoding="utf-8") as fh:
        fh.write('{"v": "0.3", "ts": "t"')  # truncated, no closing brace/newline
    result = await svc.read_reflog()
    assert len(result) >= 1


async def test_entries_come_back_as_typed_reflog_entry_values(svc):
    item = (await svc.create("task", "Entry test")).item
    result = await svc.read_reflog()
    assert all(isinstance(r, ReflogEntry) for r in result)
    assert any(r.op == "create" and r.target == item.id for r in result)


async def test_item_filter_returns_only_entries_for_that_target(svc):
    a = (await svc.create("task", "A")).item
    b = (await svc.create("task", "B")).item
    result = await svc.read_reflog(item=a.id)
    assert all(r.target == a.id for r in result)
    assert not any(r.target == b.id for r in result)


async def test_actor_filter_returns_only_entries_for_that_actor_slug(svc):
    actor.set_actor("python-dev")
    await svc.create("task", "By python-dev")
    actor.set_actor("system")
    await svc.create("task", "By system")
    dev_entries = await svc.read_reflog(actor_filter="python-dev")
    assert dev_entries and all(r.actor == "python-dev" for r in dev_entries)


async def test_op_filter_returns_only_entries_with_that_operation_name(svc):
    item = (await svc.create("task", "T")).item
    await svc.set_status(item.id, "InProgress")
    status_entries = await svc.read_reflog(op_filter="status")
    assert status_entries and all(r.op == "status" for r in status_entries)


async def test_since_filter_excludes_entries_before_the_given_timestamp(svc):
    future = await svc.read_reflog(since="2099-01-01T00:00:00Z")
    assert future == []
    await svc.create("task", "T")
    past = await svc.read_reflog(since="2000-01-01T00:00:00Z")
    assert len(past) > 0


async def test_tail_returns_exactly_the_last_n_entries(svc):
    for i in range(5):
        await svc.create("task", f"Task {i}")
    result_all = await svc.read_reflog(tail=None)
    result_tail = await svc.read_reflog(tail=3)
    assert len(result_tail) == 3
    assert result_tail == result_all[-3:]


async def test_item_and_op_filters_combine_with_and_semantics(svc):
    """Neither filter alone would distinguish this — both must hold on the same entry."""
    a = (await svc.create("task", "A")).item
    b = (await svc.create("task", "B")).item
    await svc.set_status(a.id, "InProgress")
    await svc.set_status(b.id, "InProgress")

    combined = await svc.read_reflog(item=a.id, op_filter="status")
    assert combined and all(r.target == a.id and r.op == "status" for r in combined)
    # Sanity: item=a alone includes non-status entries too (create), so the op filter is doing
    # real narrowing work, not just being redundant with the item filter.
    item_only = await svc.read_reflog(item=a.id)
    assert len(item_only) > len(combined)
