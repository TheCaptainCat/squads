"""``tree_view``'s filtering mechanism, proven once against a real hierarchy: a match always
carries its full ancestor chain (no orphaned match), an ancestor that isn't itself a match is
flagged ``path_only`` while a matching ancestor is not, ``--depth`` truncates strictly (a match
below the cut is dropped, not "orphaned in"), an explicit root scopes the whole walk, and the
closed-item gate mirrors ``list``'s own default-hides-closed behaviour. Also: the same
``ItemFilter`` selects the same items ``list_items`` would (no drift between the two callers).
"""

import pytest

from squads._services._base import ItemFilter

pytestmark = pytest.mark.anyio


def _ids(nodes) -> set[str]:
    out: set[str] = set()
    for n in nodes:
        out.add(n.item.id)
        out |= _ids(n.children)
    return out


def _path_only_ids(nodes) -> set[str]:
    out: set[str] = set()
    for n in nodes:
        if n.path_only:
            out.add(n.item.id)
        out |= _path_only_ids(n.children)
    return out


async def _hierarchy(svc):
    """EPIC -> FEAT -> TASK, plus a standalone BUG."""
    epic = (await svc.create("epic", "Epic")).item
    feat = (await svc.create("feature", "Feature", parent=epic.id)).item
    task = (await svc.create("task", "Task", parent=feat.id)).item
    bug = (await svc.create("bug", "Bug")).item
    return epic.id, feat.id, task.id, bug.id


async def test_empty_filter_returns_every_open_item(svc):
    epic_id, feat_id, task_id, bug_id = await _hierarchy(svc)
    all_ids = _ids(await svc.tree_view())
    assert {epic_id, feat_id, task_id, bug_id} <= all_ids


async def test_a_filter_narrows_to_matches_while_preserving_their_full_ancestor_chain(svc):
    epic_id, feat_id, task_id, bug_id = await _hierarchy(svc)
    nodes = await svc.tree_view(filter=ItemFilter(item_type="task"))
    all_ids = _ids(nodes)
    assert {epic_id, feat_id, task_id} <= all_ids
    assert bug_id not in all_ids  # not a task and has no matching descendant
    path_only = _path_only_ids(nodes)
    assert {epic_id, feat_id} <= path_only and task_id not in path_only


async def test_a_matching_ancestor_is_not_flagged_path_only(svc):
    root = (await svc.create("epic", "Root")).item
    feat = (await svc.create("feature", "Feat", parent=root.id)).item
    task = (await svc.create("task", "Task", parent=feat.id)).item
    await svc.update(feat.id, priority="high")
    await svc.update(task.id, priority="high")

    nodes = await svc.tree_view(filter=ItemFilter(badges=(("priority", "high"),)))
    path_only = _path_only_ids(nodes)
    assert feat.id not in path_only and task.id not in path_only  # both match
    assert root.id in path_only  # root has no priority=high of its own


async def test_combined_filter_dimensions_are_anded(svc):
    _epic_id, _feat_id, task_id, _bug_id = await _hierarchy(svc)
    await svc.update(task_id, priority="high")

    task_and_high = ItemFilter(item_type="task", badges=(("priority", "high"),))
    matched = await svc.tree_view(filter=task_and_high)
    assert task_id in _ids(matched)
    bug_and_high = ItemFilter(item_type="bug", badges=(("priority", "high"),))
    unmatched = await svc.tree_view(filter=bug_and_high)
    assert _ids(unmatched) == set()


async def test_an_explicit_root_scopes_the_walk_to_that_subtree(svc):
    epic_id, feat_id, task_id, bug_id = await _hierarchy(svc)
    nodes = await svc.tree_view(feat_id)
    all_ids = _ids(nodes)
    assert {feat_id, task_id} <= all_ids
    assert epic_id not in all_ids and bug_id not in all_ids


async def test_depth_zero_returns_roots_only_with_no_children(svc):
    epic_id, feat_id, task_id, bug_id = await _hierarchy(svc)
    nodes = await svc.tree_view(depth=0)
    assert all(n.children == [] for n in nodes)
    all_ids = _ids(nodes)
    assert feat_id not in all_ids and task_id not in all_ids
    assert epic_id in all_ids and bug_id in all_ids


async def test_depth_wins_over_a_match_below_the_cut(svc):
    """A deeper match is not shown even though it would otherwise be preserved as an ancestor
    chain — depth truncation applies before ancestor preservation, not after."""
    root = (await svc.create("epic", "Root")).item
    mid = (await svc.create("feature", "Mid", parent=root.id)).item
    leaf = (await svc.create("task", "Leaf", parent=mid.id)).item
    await svc.update(leaf.id, priority="high")

    nodes = await svc.tree_view(filter=ItemFilter(badges=(("priority", "high"),)), depth=1)
    assert _ids(nodes) == set()  # leaf (depth 2) is cut; its now-childless ancestors drop too


async def test_a_match_within_depth_renders_with_its_in_depth_ancestors(svc):
    root = (await svc.create("epic", "Root")).item
    mid = (await svc.create("feature", "Mid", parent=root.id)).item
    await svc.update(mid.id, priority="high")

    nodes = await svc.tree_view(filter=ItemFilter(badges=(("priority", "high"),)), depth=1)
    all_ids = _ids(nodes)
    assert mid.id in all_ids and root.id in all_ids


async def test_closed_items_are_hidden_by_default_and_revealed_by_include_closed_or_status_match(
    svc,
):
    feat = (await svc.create("feature", "Feat")).item
    await svc.set_status(feat.id, "InProgress")
    await svc.set_status(feat.id, "Done")

    assert feat.id not in _ids(await svc.tree_view())
    assert feat.id in _ids(await svc.tree_view(include_closed=True))
    # a status filter that matches a closed item only reveals it when paired with include_closed
    assert feat.id in _ids(
        await svc.tree_view(filter=ItemFilter(status="Done"), include_closed=True)
    )
    assert feat.id not in _ids(await svc.tree_view(filter=ItemFilter(status="Done")))


async def test_item_filter_selects_the_same_items_that_list_items_does(svc):
    feat = (await svc.create("feature", "Feat")).item
    t1 = (await svc.create("task", "T1", priority="high", parent=feat.id)).item
    t2 = (await svc.create("task", "T2", priority="low", parent=feat.id)).item
    await svc.create("bug", "B1")

    listed_ids = {i.id for i in await svc.list_items(item_type="task", badges={"priority": "high"})}
    f = ItemFilter(item_type="task", badges=(("priority", "high"),))
    filter_ids = {i.id for i in await svc.list_items() if f.matches(i)}

    assert listed_ids == filter_ids == {t1.id}
    assert t2.id not in filter_ids
