"""The CLI surface for `sq list`/`sq tree`: closed items are hidden by default and revealed by
``--all`` or an explicit ``--status``, ``tree`` accepts an explicit root and a ``--depth`` bound,
and the human tree rendering separates a priority badge from the title with a middle dot (the
``--json`` surface carries the raw value with no such decoration).
"""

import json

import pytest

pytestmark = pytest.mark.anyio


async def test_list_and_tree_hide_closed_by_default_all_and_status_reveal_it(project, invoke):
    await invoke(["create", "task", "Open one", "--author", "manager"])
    await invoke(["create", "task", "Closed one", "--author", "manager"])
    await invoke(["task", "3", "status", "InProgress"])
    await invoke(["task", "3", "status", "Done"])

    default = await invoke(["list", "--type", "task"])
    assert "TASK-2" in default.output and "TASK-3" not in default.output
    with_all = await invoke(["list", "--type", "task", "--all"])
    assert "TASK-3" in with_all.output
    by_status = await invoke(["list", "--status", "Done"])
    assert "TASK-3" in by_status.output

    tree_default = await invoke(["tree"])
    assert "TASK-3" not in tree_default.output
    tree_all = await invoke(["tree", "--all"])
    assert "TASK-3" in tree_all.output


async def test_tree_accepts_an_explicit_root_and_a_depth_bound(project, invoke):
    await invoke(["create", "epic", "Epic A", "--author", "manager"])
    await invoke(["create", "feature", "Feature B", "--author", "manager", "--parent", "EPIC-2"])
    await invoke(["create", "task", "Task C", "--author", "manager", "--parent", "FEAT-3"])

    rooted = await invoke(["tree", "FEAT-3"])
    assert "EPIC-2" not in rooted.output and "TASK-4" in rooted.output

    shallow = await invoke(["tree", "--depth", "0"])
    assert "TASK-4" not in shallow.output and "EPIC-2" in shallow.output


def _find_node(nodes: list[dict[str, object]], item_id: str) -> dict[str, object] | None:
    for n in nodes:
        if n["id"] == item_id:
            return n
        hit = _find_node(list(n["children"]), item_id)  # type: ignore[arg-type]
        if hit:
            return hit
    return None


async def test_tree_human_render_separates_priority_badge_and_title_with_a_middle_dot(
    project, invoke
):
    await invoke(
        ["create", "task", "My important task", "--author", "manager", "--priority", "high"]
    )
    out = (await invoke(["tree"])).output
    assert "high · My important task" in out

    all_nodes = json.loads((await invoke(["tree", "--json"])).output)
    task_node = _find_node(all_nodes, "TASK-2")
    assert task_node is not None
    assert task_node["priority"] == "high" and "·" not in str(task_node["priority"])
