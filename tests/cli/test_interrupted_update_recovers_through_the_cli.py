"""CLI smoke test for the atomic write path: an update interrupted right at the write
boundary (temp file complete, `os.replace` never runs) leaves the item exactly where the CLI
left off, still fully visible through `show`/`list -a`, and `sq repair` still converges.
"""

import pathlib

import pytest

pytestmark = pytest.mark.anyio


async def test_an_interrupted_update_still_leaves_the_item_reachable_and_repairable(
    project, svc, invoke
):
    task = (await svc.create("task", "CLI smoke target")).item

    def _raise(self, target):
        raise OSError("simulated crash after the temp write, before the replace")

    # `--desc`, not `--title`: a title change also moves the file (a rename), whose own
    # repair-recoverable skew is covered separately (see the retype/rename case in
    # test_repair_converges_after_an_interrupted_mutation.py) -- this test's job is the
    # plain, no-move case: the file itself stays fully readable, at the same path, with no
    # `sq repair` required first.
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(pathlib.Path, "replace", _raise)
        r = await invoke(["task", str(task.sequence_id), "update", "--desc", "Renamed"])
        assert r.exit_code != 0

    shown = await invoke(["task", str(task.sequence_id), "show"])
    assert shown.exit_code == 0
    assert "CLI smoke target" in shown.output  # the interrupted description update never landed

    listed = await invoke(["list", "-a"])
    assert listed.exit_code == 0
    assert task.id in listed.output

    repaired = await invoke(["repair"])
    assert repaired.exit_code == 0
    assert f"{task.id}:" not in repaired.output  # never reported as a missing/orphaned item

    shown_again = await invoke(["task", str(task.sequence_id), "show"])
    assert shown_again.exit_code == 0
    assert "CLI smoke target" in shown_again.output
