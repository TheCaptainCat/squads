"""The headline guarantee of the atomic write path: a process killed mid-write can no longer
truncate an item's `.md` and cost it the board.

Faults the LIVE primitive (`_aio.atomic_write_text`) at its own `os.fsync` call -- the exact
boundary between "the temp file holds whatever bytes made it to disk" and "the durability
barrier plus the rename that would make them visible at the real target" -- rather than
replacing the primitive with a stub. A stub's "the real target is untouched" is guaranteed by
its own construction; faulting the real code path is what actually observes it.
"""

import os

import pytest

from squads._itemfile import read_frontmatter

pytestmark = pytest.mark.anyio


class _SimulatedProcessDeath(BaseException):
    """Deliberately NOT an `Exception` subclass -- a real `SIGKILL` gives the process no
    chance to run `except Exception` handlers either; this pins that nothing upstream
    swallows the interruption and quietly "completes" the mutation."""


@pytest.mark.parametrize("frac", [0.3, 0.55, 0.85])
async def test_a_kill_mid_write_leaves_the_item_fully_intact_and_recoverable(svc, frac):
    task = (await svc.create("task", "Crash target")).item
    path = svc.paths.abspath(task.path)
    complete_bytes_before = path.read_bytes()

    real_fsync = os.fsync

    def _fsync_a_fractional_write_then_die(fd: int) -> None:
        # By the time `os.fsync` runs, the primitive's own `fh.write(text)` has already
        # handed the FULL intended bytes to the OS buffer for the temp file. A real kill can
        # land anywhere before they're durable, so truncate the temp file down to a `frac`
        # prefix of them -- standing in for "only this much actually made it to disk" -- fsync
        # that truncated state for real, then die before the primitive ever reaches
        # `tmp.replace`. The real target is never touched at any point in this sequence.
        size = os.fstat(fd).st_size
        os.ftruncate(fd, int(size * frac))
        real_fsync(fd)
        raise _SimulatedProcessDeath("process died mid-write, right after the partial fsync")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(os, "fsync", _fsync_a_fractional_write_then_die)
        with pytest.raises(_SimulatedProcessDeath):
            await svc.set_status(task.id, "InProgress", force=True)

    # The real target is untouched -- complete, PREVIOUS bytes exactly. Not either of the two
    # truncation shapes a bare `Path.write_text` could produce (a cut inside frontmatter with
    # no closing `---`, or a cut inside the body with a half-written marker) -- no shape at
    # all, because the cut only ever lands on the temp file's bytes, never the target's.
    assert path.read_bytes() == complete_bytes_before
    frontmatter = read_frontmatter(path=path)
    assert frontmatter["id"] == task.id
    assert frontmatter["status"] == "Draft"  # the update never landed -- and that's correct

    # The primitive's own error-path cleanup removes the temp sibling on the way out -- no
    # `*.tmp` litter left behind for a failed write to leak.
    assert list(path.parent.glob("*.tmp")) == []

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
