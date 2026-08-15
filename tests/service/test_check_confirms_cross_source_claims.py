"""``Service.check()`` partitions status/parent drift and both directions of index/disk
reconciliation into candidates, confirmed by exactly one cheap re-read before being reported.
A mutation racing the scan must never survive that confirm round; a real, durable
inconsistency must always survive it (the risk this design carries — the
swallow-a-true-positive boundary is exercised explicitly below).
"""

from datetime import timedelta
from pathlib import Path

import anyio
import pytest

from _helpers import create_item
from squads import _aio
from squads import _clock as clock
from squads import _sections as sections
from squads._index._store import IndexStore
from squads._itemfile import read_frontmatter
from squads._models._item import Item
from squads._services._results import CheckIssue

pytestmark = pytest.mark.anyio


def _edit_frontmatter(path: Path, **fields: object) -> None:
    """Directly rewrite frontmatter fields on a squad-data file, bypassing the service — the
    only way to produce the frontmatter/index mismatches these tests need to construct."""
    text = path.read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    fm.update(fields)
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")


async def _race_a_mutation_against_check(svc, mutate) -> list[CheckIssue]:
    """Run ``svc.check()`` concurrently with *mutate* (an async no-arg callable), pausing the
    scan right after the index snapshot is loaded so *mutate* commits its whole transaction
    before the scan (and therefore the confirm pass) ever runs — the same stale-comparison
    window a real concurrent mutator can hit, reproduced here with two real coroutines, a
    real transaction, and real files sharing one event loop.
    """
    started = anyio.Event()
    release = anyio.Event()
    orig_scan = svc._scan_for_check

    async def paused_scan():
        started.set()
        await release.wait()
        return await orig_scan()

    svc._scan_for_check = paused_scan

    issues: list[CheckIssue] = []

    async def run_check() -> None:
        issues.extend(await svc.check())

    async def run_mutation() -> None:
        await started.wait()
        await mutate()
        release.set()

    async with anyio.create_task_group() as tg:
        tg.start_soon(run_check)
        tg.start_soon(run_mutation)

    return issues


# --------------------------------------------------------------- phantom candidates, confirmed away


async def test_status_drift_candidate_from_a_racing_mutation_is_not_reported(svc):
    task = (await create_item(svc, "task", "t")).item

    async def mutate() -> None:
        await svc.set_status(task.id, "InProgress")

    issues = await _race_a_mutation_against_check(svc, mutate)
    assert not any("drift" in i.message for i in issues), issues


async def test_on_disk_not_indexed_candidate_from_an_in_flight_create_is_not_reported(svc):
    created: dict[str, Item] = {}

    async def mutate() -> None:
        created["item"] = (await create_item(svc, "task", "brand new")).item

    issues = await _race_a_mutation_against_check(svc, mutate)
    assert not any("on disk but not in index" in i.message for i in issues), issues
    # sanity: the create really did land, and really was a candidate the scan could have seen
    assert created["item"] is not None


async def test_in_index_but_no_file_candidate_from_an_in_flight_remove_is_not_reported(svc):
    task = (await create_item(svc, "task", "t")).item

    async def mutate() -> None:
        await svc.remove_work_item(task.id)

    issues = await _race_a_mutation_against_check(svc, mutate)
    assert not any("no markdown file found" in i.message for i in issues), issues


async def test_clean_board_loads_the_index_once_and_never_rereads_a_file(svc, monkeypatch):
    await create_item(svc, "task", "a")
    await create_item(svc, "task", "b")

    load_calls = 0
    orig_load = svc.store.load

    async def counted_load():
        nonlocal load_calls
        load_calls += 1
        return await orig_load()

    monkeypatch.setattr(svc.store, "load", counted_load)

    read_paths: list[Path] = []
    orig_read = _aio.read_text

    async def counted_read(path: Path) -> str:
        read_paths.append(path)
        return await orig_read(path)

    monkeypatch.setattr(_aio, "read_text", counted_read)

    issues = await svc.check()
    assert not any(i.level == "error" for i in issues), issues
    assert load_calls == 1
    assert len(read_paths) == len(set(read_paths)), "a clean board must never re-read a file"


# --------------------------------------------------------------- single-source stays unconfirmed


async def test_single_source_marker_damage_is_reported_with_no_second_read(svc, monkeypatch):
    task = (await create_item(svc, "task", "t")).item
    path = svc.paths.abspath(task.path)
    path.write_text(
        path.read_text(encoding="utf-8").replace("<!-- sq:body:end -->", ""), encoding="utf-8"
    )

    load_calls = 0
    orig_load = svc.store.load

    async def counted_load():
        nonlocal load_calls
        load_calls += 1
        return await orig_load()

    monkeypatch.setattr(svc.store, "load", counted_load)

    issues = await svc.check()
    assert any("sq:body" in i.message for i in issues)
    assert load_calls == 1, "a single-source issue must never trigger the confirm round"


# --------------------------------------------------------------- durable inconsistencies, reported


async def test_durable_status_drift_is_reported(svc):
    task = (await create_item(svc, "task", "t")).item
    _edit_frontmatter(svc.paths.abspath(task.path), status="InProgress")

    issues = await svc.check()
    hit = next(i for i in issues if "status drift" in i.message and i.item == task.id)
    assert hit.level == "warn"


async def test_durable_drift_survives_a_stale_index_path_from_an_interrupted_rename(
    svc, monkeypatch
):
    """An interrupted title-changing update leaves the file at its new path and the index
    still holding the old one -- the confirm round must re-observe wherever the sequence
    number actually lives, not only where the (stale) index path points, or a real, durable
    drift is silently dropped instead of reported.
    """
    task = (await create_item(svc, "task", "original title")).item

    real_atomic_write = IndexStore._atomic_write

    async def _boom(self, db):
        raise OSError("simulated crash during the index commit")

    monkeypatch.setattr(IndexStore, "_atomic_write", _boom)
    try:
        with pytest.raises(OSError):
            await svc.update(task.id, title="renamed mid crash", status="InProgress", force=True)
    finally:
        monkeypatch.setattr(IndexStore, "_atomic_write", real_atomic_write)

    # The rename and the frontmatter write both landed; the index commit never did -- the
    # index still has the old path and the old status.
    reloaded = await svc.get(task.id)
    assert reloaded.path == task.path
    assert reloaded.status == "Draft"
    assert not svc.paths.abspath(task.path).exists()

    issues = await svc.check()
    assert any("status drift" in i.message and i.item == task.id for i in issues), (
        f"a durable drift must survive a stale index path, got: {issues}"
    )


async def test_durable_orphan_file_is_reported(svc):
    task = (await create_item(svc, "task", "t")).item
    async with svc.store.transaction() as db:
        del db.items[task.sequence_id]

    issues = await svc.check()
    assert any("on disk but not in index" in i.message and i.item == task.id for i in issues), (
        issues
    )


async def test_durable_missing_file_is_reported(svc):
    task = (await create_item(svc, "task", "t")).item
    svc.paths.abspath(task.path).unlink()

    issues = await svc.check()
    assert any("no markdown file found" in i.message and i.item == task.id for i in issues), issues


async def test_confirm_round_reloads_index_when_candidates_exist(svc, monkeypatch):
    """The other half of the "pays nothing when clean" contract: a real candidate does cost
    exactly one extra index load (never zero, never more)."""
    task = (await create_item(svc, "task", "t")).item
    svc.paths.abspath(task.path).unlink()

    load_calls = 0
    orig_load = svc.store.load

    async def counted_load():
        nonlocal load_calls
        load_calls += 1
        return await orig_load()

    monkeypatch.setattr(svc.store, "load", counted_load)

    await svc.check()
    assert load_calls == 2


# --------------------------------------------------------------- skew direction


async def test_confirmed_drift_names_the_markdown_ahead_direction(svc):
    task = (await create_item(svc, "task", "t")).item
    # advance the frontmatter's own `updated_at` past the index's frozen one
    ahead = clock.now() + timedelta(seconds=5)
    _edit_frontmatter(
        svc.paths.abspath(task.path), status="InProgress", updated_at=clock.iso(ahead)
    )

    issues = await svc.check()
    hit = next(i for i in issues if "status drift" in i.message and i.item == task.id)
    assert hit.level == "warn"
    assert "markdown is ahead" in hit.message


async def test_confirmed_drift_names_the_index_ahead_direction(svc):
    task = (await create_item(svc, "task", "t")).item
    _edit_frontmatter(svc.paths.abspath(task.path), status="InProgress")

    async with svc.store.transaction() as db:
        item = db.items[task.sequence_id]
        item.updated_at = item.updated_at + timedelta(seconds=10)

    issues = await svc.check()
    hit = next(i for i in issues if "status drift" in i.message and i.item == task.id)
    assert hit.level == "warn"
    assert "index is ahead of markdown" in hit.message


async def test_confirmed_drift_names_no_direction_when_timestamps_do_not_order_the_pair(svc):
    task = (await create_item(svc, "task", "t")).item
    _edit_frontmatter(svc.paths.abspath(task.path), status="InProgress")

    issues = await svc.check()
    hit = next(i for i in issues if "status drift" in i.message and i.item == task.id)
    assert hit.level == "warn"
    assert "ahead" not in hit.message
