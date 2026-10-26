"""`repair`, `renumber` and `repad` read, rewrite and commit under the index lock: a writer
started during any step waits for the pass to end instead of interleaving."""

import anyio
import pytest

from _helpers import make_service
from squads import _aio
from squads._errors import SquadsError
from squads._index._store import read_scope

pytestmark = pytest.mark.anyio


async def _collide(svc):
    """A task and a bug numbered alike, plus a third task that refers to the task."""
    first = await svc.create("task", "alpha", author="manager")
    twin = first.path.parent.parent / "bugs" / first.path.name.replace("TASK", "BUG")
    text = (await _aio.read_text(first.path)).replace(first.item.id, "BUG-" + first.item.id[5:])
    await _aio.write_text(twin, text)
    xref = await svc.create("task", "xref", author="manager", body=f"see {first.item.id}")
    return xref.item.id


async def _run_with_a_writer_at(svc, other, method: str, verb, retype_id: str) -> None:
    """Run *verb* with a retype by another service started when *method* is first reached;
    the retype must still be waiting then, and must have run once *verb* has returned."""
    done = anyio.Event()
    original = getattr(svc, method)
    fired = False

    async def writer() -> None:
        await other.retype(retype_id, "bug")
        done.set()

    async def hooked(*args, **kwargs):
        nonlocal fired
        if not fired:
            fired = True
            tg.start_soon(writer)
            await anyio.sleep(0.4)
            assert not done.is_set(), "the writer ran inside the pass"
        return await original(*args, **kwargs)

    setattr(svc, method, hooked)
    async with anyio.create_task_group() as tg:
        await verb()
        assert fired
    assert done.is_set()


@pytest.mark.parametrize("method", ["_scan_records", "_apply_remap"])
async def test_a_retype_during_repair_renumber_waits_and_the_board_ends_consistent(
    svc, project, method
):
    xref = await _collide(svc)
    other = make_service(project)
    await _run_with_a_writer_at(svc, other, method, lambda: svc.repair(renumber=True), xref)
    assert [i for i in await svc.check() if i.level == "error"] == []


async def test_a_retype_during_repair_waits(svc, project):
    xref = await svc.create("task", "xref", author="manager")
    other = make_service(project)
    await _run_with_a_writer_at(svc, other, "_rebuild_index_from_disk", svc.repair, xref.item.id)
    assert [i for i in await svc.check() if i.level == "error"] == []


async def test_a_retype_during_renumber_waits(svc, project):
    xref = await svc.create("task", "xref", author="manager")
    later = await svc.create("task", "later", author="manager")
    other = make_service(project)
    await _run_with_a_writer_at(
        svc,
        other,
        "_apply_remap",
        lambda: svc.renumber(from_seq=later.item.sequence_id, by=1000),
        xref.item.id,
    )
    assert [i for i in await svc.check() if i.level == "error"] == []


async def test_a_retype_during_repad_waits(svc, project):
    xref = await svc.create("task", "xref", author="manager")
    other = make_service(project)
    await _run_with_a_writer_at(svc, other, "_scan_records", lambda: svc.repad(7), xref.item.id)
    assert [i for i in await svc.check() if i.level == "error"] == []


async def _bump_counter_after_a_cached_read(svc, project):
    """Cache the index, then let another writer create and purge an item: the counter in the
    index is now ahead of the cached read and of every file."""
    await svc.create("task", "keep", author="manager")
    await svc.store.load()
    other = make_service(project)
    gone = await other.create("task", "gone", author="manager")
    await other.remove_work_item(gone.item.id)
    return (await other.store.load(fresh=True)).counter


async def test_repad_keeps_a_counter_another_writer_advanced_after_the_cached_read(svc, project):
    with read_scope():
        expected = await _bump_counter_after_a_cached_read(svc, project)
        await svc.repad(7)
    assert (await svc.store.load(fresh=True)).counter >= expected


async def test_repair_keeps_a_counter_another_writer_advanced_after_the_cached_read(svc, project):
    with read_scope():
        expected = await _bump_counter_after_a_cached_read(svc, project)
        await svc.repair()
    assert (await svc.store.load(fresh=True)).counter >= expected


async def test_renumber_refuses_an_offset_only_safe_against_a_cached_counter(svc, project):
    top = await svc.create("task", "top", author="manager")
    from_seq = top.item.sequence_id
    with read_scope():
        await svc.store.load()
        other = make_service(project)
        gone = await other.create("task", "gone", author="manager")
        await other.remove_work_item(gone.item.id)
        by = 1  # the smallest offset that clears the cached counter (from_seq + 1 > from_seq)
        with pytest.raises(SquadsError, match="unsafe"):
            await svc.renumber(from_seq=from_seq, by=by)
    assert top.path.exists()
    assert (await svc.store.load(fresh=True)).counter >= gone.item.sequence_id
