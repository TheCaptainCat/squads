"""The CLI surface for `sq list`/`sq tree`: closed items are hidden by default and revealed by
``--all`` or an explicit ``--status``, ``tree`` accepts an explicit root and a ``--depth`` bound,
and the human tree rendering separates a priority badge from the title with a middle dot (the
``--json`` surface carries the raw value with no such decoration).

Also: the category-aware default visibility rule — a records item (e.g. an Accepted decision)
stays visible by default past a work item's equivalent terminal status, hides once retired — and
the empty-view "N closed items hidden" hint both commands print instead of a bare "no items"/
empty tree.
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


async def test_accepted_decision_shows_by_default_while_done_feature_hides(project, invoke):
    await invoke(["create", "decision", "Use JWT", "--author", "manager"])
    await invoke(["decision", "2", "status", "Accepted"])
    await invoke(["create", "feature", "Feat", "--author", "manager"])
    await invoke(["feature", "3", "status", "InProgress"])
    await invoke(["feature", "3", "status", "Done"])

    listed = await invoke(["list"])
    assert "ADR-2" in listed.output and "FEAT-3" not in listed.output

    tree = await invoke(["tree"])
    assert "ADR-2" in tree.output and "FEAT-3" not in tree.output


async def test_superseded_decision_hides_by_default_but_all_reveals_it(project, invoke):
    await invoke(["create", "decision", "Old choice", "--author", "manager"])
    await invoke(["decision", "2", "status", "Accepted"])
    await invoke(["decision", "2", "status", "Superseded"])

    default = await invoke(["list"])
    assert "ADR-2" not in default.output
    with_all = await invoke(["list", "--all"])
    assert "ADR-2" in with_all.output


async def test_empty_default_view_prints_the_hidden_count_hint_instead_of_bare_no_items(
    project, invoke
):
    await invoke(["create", "task", "T1", "--author", "manager"])
    await invoke(["task", "2", "status", "InProgress"])
    await invoke(["task", "2", "status", "Done"])

    listed = await invoke(["list", "--type", "task"])
    assert "closed" in listed.output and "hidden" in listed.output and "--all" in listed.output

    tree = await invoke(["tree", "--type", "task"])
    assert "closed" in tree.output and "hidden" in tree.output and "--all" in tree.output


async def test_a_view_with_nothing_hidden_still_prints_the_plain_no_items_message(project, invoke):
    """No bugs exist and none were hidden by the default filter — the plain message, not the
    hidden-count hint."""
    listed = await invoke(["list", "--type", "bug"])
    assert "no items" in listed.output
    assert "hidden" not in listed.output


async def test_tree_type_filter_still_renders_path_only_ancestors_but_excludes_siblings(
    project, invoke
):
    """A ``--type`` filter dims non-matching ancestors (path-only) rather than hiding them, and
    drops a sibling subtree with no matching descendant entirely."""
    await invoke(["create", "epic", "Epic A", "--author", "manager"])
    await invoke(["create", "feature", "Feature B", "--author", "manager", "--parent", "EPIC-2"])
    await invoke(["create", "task", "Task C", "--author", "manager", "--parent", "FEAT-3"])
    await invoke(["create", "bug", "Bug D", "--author", "manager", "--parent", "FEAT-3"])

    r = await invoke(["tree", "--type", "task"])
    assert r.exit_code == 0, r.output
    assert "TASK-4" in r.output
    assert "EPIC-2" in r.output and "FEAT-3" in r.output  # path-only ancestors still rendered
    assert "BUG-5" not in r.output  # non-matching sibling excluded entirely

    scoped = await invoke(["tree", "FEAT-3", "--type", "task"])
    assert "TASK-4" in scoped.output and "FEAT-3" in scoped.output
    assert "EPIC-2" not in scoped.output
