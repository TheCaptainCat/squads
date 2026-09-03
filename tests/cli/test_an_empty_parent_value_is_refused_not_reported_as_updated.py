"""``update`` refuses an empty ``--parent`` instead of reporting a write it never performed.

The option was tested for truthiness rather than for presence, so an empty string fell through
both the mutual-exclusion guard and the resolution below: the command printed ``updated <ID>``
and exited 0 with the parent untouched. Same write-door class as a silently-accepted cycle — a
success line for a write that did not happen — and the first thing an operator reaches for when
trying to undo a bad parent edge.

The priority pair carries the identical shape on the same guard and is closed here too.
"""

import pytest

from _helpers import create_item

pytestmark = pytest.mark.anyio


async def test_an_empty_parent_is_refused_and_prints_no_success_line(svc, invoke):
    epic = (await create_item(svc, "epic", "Epic")).item
    feat = (await create_item(svc, "feature", "Feature", parent=epic.id)).item

    result = await invoke(["feature", str(feat.sequence_id), "update", "--parent", ""])
    assert result.exit_code != 0, result.output
    assert "updated" not in result.output
    assert "--no-parent" in result.output
    assert (await svc.get(feat.id)).parent == epic.id


async def test_a_whitespace_only_parent_is_refused_the_same_way(svc, invoke):
    epic = (await create_item(svc, "epic", "Epic")).item
    feat = (await create_item(svc, "feature", "Feature", parent=epic.id)).item

    result = await invoke(["feature", str(feat.sequence_id), "update", "--parent", "   "])
    assert result.exit_code != 0, result.output
    # Refused by the same guard, not by the id parser failing further down: the remedy is
    # named, which a parse error would not do.
    assert "--no-parent" in result.output
    assert (await svc.get(feat.id)).parent == epic.id


async def test_an_empty_parent_no_longer_slips_past_the_mutual_exclusion_guard(svc, invoke):
    epic = (await create_item(svc, "epic", "Epic")).item
    feat = (await create_item(svc, "feature", "Feature", parent=epic.id)).item

    result = await invoke(
        ["feature", str(feat.sequence_id), "update", "--parent", "", "--no-parent"]
    )
    assert result.exit_code != 0, result.output
    assert "not both" in result.output
    assert (await svc.get(feat.id)).parent == epic.id


async def test_an_empty_priority_no_longer_slips_past_its_mutual_exclusion_guard(svc, invoke):
    task = (await create_item(svc, "task", "Task", priority="high")).item

    result = await invoke(
        ["task", str(task.sequence_id), "update", "--priority", "", "--no-priority"]
    )
    assert result.exit_code != 0, result.output
    assert "not both" in result.output
    assert (await svc.get(task.id)).priority == "high"


async def test_the_ordinary_parent_forms_still_work(svc, invoke):
    epic = (await create_item(svc, "epic", "Epic")).item
    feat = (await create_item(svc, "feature", "Feature")).item
    addr = ["feature", str(feat.sequence_id), "update"]

    assert (await invoke([*addr, "--parent", epic.id])).exit_code == 0
    assert (await svc.get(feat.id)).parent == epic.id

    assert (await invoke([*addr, "--no-parent"])).exit_code == 0
    assert (await svc.get(feat.id)).parent is None

    # The bare-number form resolves the same way.
    assert (await invoke([*addr, "--parent", str(epic.sequence_id)])).exit_code == 0
    assert (await svc.get(feat.id)).parent == epic.id
