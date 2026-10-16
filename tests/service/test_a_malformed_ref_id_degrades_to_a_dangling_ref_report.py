"""A ref whose id does not parse never aborts the corpus scan or a write: `sq check` reports it as
a dangling ref and exits 0, and a write on an unrelated item is accepted, for a ref of each
kind the incoming-edge walk reads and for one it does not.
"""

import pytest

from _helpers import create_item

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("kind", ["supersedes", "blocks", "depends-on", "related"])
async def test_a_malformed_ref_is_a_dangling_ref_report_and_blocks_no_write(
    project, invoke, svc, kind: str
) -> None:
    holder = (await create_item(svc, "task", "holder")).item
    other = (await create_item(svc, "task", "other")).item
    async with svc.store.transaction() as db:
        db.items[holder.sequence_id].refs.append(f"TASK-abc:{kind}")

    issues = await svc.check()
    assert [i.message for i in issues if i.item == holder.id and "dangling" in i.message] == [
        "dangling ref TASK-abc"
    ]
    assert not any("could not scan" in i.message for i in issues)

    checked = await invoke(["check"])
    assert checked.exit_code == 0, checked.output
    assert "dangling ref TASK-abc" in checked.output

    updated = await invoke(["task", str(other.sequence_id), "update", "--title", "renamed"])
    assert updated.exit_code == 0, updated.output
