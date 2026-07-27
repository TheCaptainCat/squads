"""The headline guarantee of the atomic write path: a process killed mid-write can no longer
truncate an item's `.md` and cost it the board.

Faults the LIVE primitive (`_aio.atomic_write_text`) at its own rename step -- `tmp.replace`,
the exact boundary between "the temp file holds the complete new bytes" and "the target
actually shows them" -- rather than replacing the primitive with a stub. A stub's "the real
target is untouched" is guaranteed by its own construction; faulting the real code path is
what actually observes it.

The hook is scoped to this item's own path (a global `Path.replace` patch would also trip the
index commit's own replace, misattributing that failure) and does not touch `os.fsync`: the
design explicitly reserves the right to drop that call under measured load (see the decision
this work implements), so a test pinned to it would fail on a sanctioned change that breaks
nothing. The rename is the one step neither that change nor its absence can move.
"""

from os import PathLike
from pathlib import Path

import pytest

from squads._itemfile import read_frontmatter

pytestmark = pytest.mark.anyio


class _SimulatedProcessDeath(BaseException):
    """Deliberately NOT an `Exception` subclass -- a real `SIGKILL` gives the process no
    chance to run `except Exception` handlers either; this pins that nothing upstream
    swallows the interruption and quietly "completes" the mutation."""


async def test_a_kill_right_before_the_replace_leaves_the_item_fully_intact_and_recoverable(svc):
    task = (await svc.create("task", "Crash target")).item
    path = svc.paths.abspath(task.path)
    complete_bytes_before = path.read_bytes()

    real_replace = Path.replace

    def _replace_or_die(self: Path, target: str | PathLike[str]) -> Path:
        # By the time this runs, the primitive has already written and flushed (and, unless
        # fsync has been dropped, fsynced) the complete new bytes to the temp file -- only
        # the rename onto the real target is left. Raise only for THIS item's target so the
        # index's own unrelated `.squads.json` replace (the transaction's last write) goes
        # through untouched.
        if Path(target) == path:
            raise _SimulatedProcessDeath("process died right before the replace")
        return real_replace(self, target)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(Path, "replace", _replace_or_die)
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
