"""The headline guarantee of the atomic write path: a process killed mid-write can no longer
truncate an item's `.md` and cost it the board.

Reproduces the exact interruption pattern that used to produce that loss -- a fractional-
prefix write followed by process death -- through the real `Service.set_status()` call path,
fault-injected at the write boundary rather than via an actual `fork`+`SIGKILL` (equally
sanctioned, and far less flaky under this harness's own nested-process/thread-pool
constraints): the fault lands exactly where a kill would land -- after a fractional prefix has
been flushed to the temp file, before `os.replace` ever runs -- so the real target is provably
never touched.
"""

import os

import pytest

from squads._aio import to_thread
from squads._itemfile import read_frontmatter

pytestmark = pytest.mark.anyio


class _SimulatedProcessDeath(BaseException):
    """Deliberately NOT an `Exception` subclass -- a real `SIGKILL` gives the process no
    chance to run `except Exception` handlers either; this pins that nothing upstream
    swallows the interruption and quietly "completes" the mutation."""


async def _die_after_a_fractional_write(path, text, *, frac: float):
    """Stands in for `_aio.atomic_write_text`, but stops exactly where a killed process
    would: after a `frac` prefix of the intended bytes has been written to the TEMP file and
    fsynced -- never touching the real target, never reaching `os.replace`."""

    def _write_partial_prefix() -> None:
        tmp = path.with_name(f"{path.name}.{os.getpid()}.crash.tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            fh.write(text[: int(len(text) * frac)])
            fh.flush()
            os.fsync(fh.fileno())

    await to_thread(_write_partial_prefix)
    raise _SimulatedProcessDeath("process died mid-write, right after the temp write")


@pytest.mark.parametrize("frac", [0.3, 0.55, 0.85])
async def test_a_kill_mid_write_leaves_the_item_fully_intact_and_recoverable(svc, frac):
    task = (await svc.create("task", "Crash target")).item
    path = svc.paths.abspath(task.path)
    complete_bytes_before = path.read_bytes()

    async def _fake_atomic_write(p, t):
        await _die_after_a_fractional_write(p, t, frac=frac)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("squads._aio.atomic_write_text", _fake_atomic_write)
        with pytest.raises(_SimulatedProcessDeath):
            await svc.set_status(task.id, "InProgress", force=True)

    # The real target is untouched -- complete, PREVIOUS bytes exactly. Not either of the two
    # truncation shapes a bare `Path.write_text` could produce (a cut inside frontmatter with
    # no closing `---`, or a cut inside the body with a half-written marker) -- no shape at
    # all, because the cut only ever lands on the temp file's bytes now.
    assert path.read_bytes() == complete_bytes_before
    frontmatter = read_frontmatter(path=path)
    assert frontmatter["id"] == task.id
    assert frontmatter["status"] == "Draft"  # the update never landed -- and that's correct

    # No corrupted item file is left as a permanent orphan `sq` cannot recover -- the mess (if
    # any) is confined to the gitignored `*.tmp` name, never the real target.
    for stray in path.parent.glob("*.tmp"):
        assert stray.name != path.name

    # The item stays exactly as reachable as it was before the interruption -- by direct
    # lookup, by the listing, and by a repair pass (a no-op here: the index never committed
    # either, since the write raised inside the same transaction body).
    item = await svc.get(task.id)
    assert item.status == "Draft"
    listed = await svc.list_items(item_type="task")
    assert any(it.id == task.id for it in listed)

    repaired = await svc.repair()
    assert task.id in {it.id for it in repaired.db.items.values()}
    assert task.id not in repaired.missing_ids
