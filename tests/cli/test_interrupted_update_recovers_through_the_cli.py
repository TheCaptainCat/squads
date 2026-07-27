"""CLI smoke test for the atomic write path: an update interrupted right at the write
boundary (temp file written, the durability barrier never completes) leaves the item exactly
where the CLI left off, still fully visible through `show`/`list -a`, and `sq repair` still
converges.

Faults the LIVE primitive's own rename step (`tmp.replace`), scoped to this item's own target
path, rather than `os.fsync`: the design explicitly reserves the right to drop that call under
measured load, so a test pinned to it would fail on a sanctioned change that breaks nothing.
Scoping to this item's path (rather than a global `Path.replace` patch) also means the index
commit's own unrelated `.squads.json` replace is never touched, so the non-zero exit this test
asserts is produced by the item-file write failing -- never by the index's own atomic write.
"""

from os import PathLike
from pathlib import Path

import pytest

from squads._index._resolver import item_file
from squads._itemfile import read_frontmatter

pytestmark = pytest.mark.anyio


async def test_an_interrupted_update_still_leaves_the_item_reachable_and_repairable(
    project, svc, invoke
):
    task = (await svc.create("task", "CLI smoke target")).item
    path = item_file(svc.paths, task)

    real_replace = Path.replace

    def _replace_or_die(self: Path, target: str | PathLike[str]) -> Path:
        if Path(target) == path:
            raise OSError("simulated crash right before the replace")
        return real_replace(self, target)

    # `--desc`, not `--title`: a title change also moves the file (a rename), whose own
    # repair-recoverable skew is covered separately (see the retype/rename case in
    # test_repair_converges_after_an_interrupted_mutation.py) -- this test's job is the
    # plain, no-move case: the file itself stays fully readable, at the same path, with no
    # `sq repair` required first.
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(Path, "replace", _replace_or_die)
        r = await invoke(["task", str(task.sequence_id), "update", "--desc", "Renamed"])
        assert r.exit_code != 0

    # The proof that the interrupted description update never landed has to read the file
    # itself, not `show` -- `show` renders from the index, which would report this correctly
    # whether or not the markdown write ever completed.
    frontmatter = read_frontmatter(path=path)
    assert frontmatter.get("description") != "Renamed"

    shown = await invoke(["task", str(task.sequence_id), "show"])
    assert shown.exit_code == 0
    assert "CLI smoke target" in shown.output

    listed = await invoke(["list", "-a"])
    assert listed.exit_code == 0
    assert task.id in listed.output

    repaired = await invoke(["repair"])
    assert repaired.exit_code == 0
    assert f"{task.id}:" not in repaired.output  # never reported as a missing/orphaned item

    shown_again = await invoke(["task", str(task.sequence_id), "show"])
    assert shown_again.exit_code == 0
    assert "CLI smoke target" in shown_again.output
