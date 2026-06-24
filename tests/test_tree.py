"""Tests for sq tree filters + --depth (TASK-000185 / FEAT-000039).

Coverage:
- ItemFilter: each field alone, combined (AND), is_empty, matches logic.
- Shared-filter regression: ItemFilter selects the same items as list_items field-by-field.
- tree_view service: empty filter == today's tree; each filter alone; combined; with/without
  explicit root; ancestor preservation (no orphaned matches); path_only flag; depth truncation;
  depth-wins-over-deeper-match; include_closed gate (mirrors list's closed-item gate).
- CLI smoke: each flag alone and combined; explicit root; --all; --depth; dim rendering for
  path_only ancestors; --json same shape (pruned not reshaped), no path_only key in JSON;
  --json golden; --status reveals closed; non-status filter does not widen to closed.
"""

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from squads._cli import app
from squads._models._enums import ItemType, Priority, Status
from squads._services._base import ItemFilter
from squads._services._results import TreeNode

pytestmark = pytest.mark.anyio

GOLDENS_DIR = Path(__file__).parent / "goldens"
_UPDATE = os.getenv("UPDATE_GOLDENS") == "1"


# ---------------------------------------------------------------------------
# Golden helper (same pattern as test_graph.py)
# ---------------------------------------------------------------------------


def _check_golden(name: str, actual_data: object) -> None:
    path = GOLDENS_DIR / f"{name}.json"
    if _UPDATE:
        GOLDENS_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(actual_data, indent=2) + "\n", encoding="utf-8")
        return
    assert path.exists(), (
        f"Golden file missing: {path}\n"
        f"Run UPDATE_GOLDENS=1 uv run pytest tests/test_tree.py to generate it."
    )
    expected = json.loads(path.read_text(encoding="utf-8"))
    assert actual_data == expected, (
        f"Golden mismatch for {name!r}.\n"
        f"Regenerate with: UPDATE_GOLDENS=1 uv run pytest tests/test_tree.py -v"
    )


# ---------------------------------------------------------------------------
# ItemFilter unit tests
# ---------------------------------------------------------------------------


def test_item_filter_is_empty_when_no_fields_set():
    f = ItemFilter()
    assert f.is_empty() is True


def test_item_filter_not_empty_with_any_field():
    assert ItemFilter(item_type=ItemType.TASK).is_empty() is False
    assert ItemFilter(status=Status.READY).is_empty() is False
    assert ItemFilter(assignee="qa").is_empty() is False
    assert ItemFilter(priority=Priority.HIGH).is_empty() is False
    assert ItemFilter(parent="FEAT-000001").is_empty() is False
    assert ItemFilter(label="urgent").is_empty() is False


async def test_item_filter_matches_type(svc):
    task = (await svc.create(ItemType.TASK, "A task")).item
    feat = (await svc.create(ItemType.FEATURE, "A feat")).item

    f_task = ItemFilter(item_type=ItemType.TASK)
    assert f_task.matches(task) is True
    assert f_task.matches(feat) is False


async def test_item_filter_matches_status(svc):
    item = (await svc.create(ItemType.TASK, "T")).item
    # Draft is initial status for tasks
    assert item.status is Status.DRAFT
    f_draft = ItemFilter(status=Status.DRAFT)
    assert f_draft.matches(item) is True
    f_ready = ItemFilter(status=Status.READY)
    assert f_ready.matches(item) is False


async def test_item_filter_matches_assignee(svc):
    item = (await svc.create(ItemType.TASK, "T")).item
    await svc.update(item.id, assignee="manager")
    updated = await svc.get(item.id)
    f_match = ItemFilter(assignee="manager")
    f_other = ItemFilter(assignee="product-owner")
    assert f_match.matches(updated) is True
    assert f_other.matches(updated) is False


async def test_item_filter_matches_priority(svc):
    item = (await svc.create(ItemType.TASK, "T", priority=Priority.HIGH)).item
    f_high = ItemFilter(priority=Priority.HIGH)
    f_low = ItemFilter(priority=Priority.LOW)
    assert f_high.matches(item) is True
    assert f_low.matches(item) is False


async def test_item_filter_matches_combined_and(svc):
    """Combined filter = AND of all set dimensions."""
    item = (await svc.create(ItemType.TASK, "T", priority=Priority.HIGH)).item
    # Matches type AND priority
    f = ItemFilter(item_type=ItemType.TASK, priority=Priority.HIGH)
    assert f.matches(item) is True
    # Matches type but not priority
    f_wrong_prio = ItemFilter(item_type=ItemType.TASK, priority=Priority.LOW)
    assert f_wrong_prio.matches(item) is False
    # Matches priority but not type
    f_wrong_type = ItemFilter(item_type=ItemType.FEATURE, priority=Priority.HIGH)
    assert f_wrong_type.matches(item) is False


# ---------------------------------------------------------------------------
# Shared-filter regression: ItemFilter must agree with list_items field-by-field
# ---------------------------------------------------------------------------


async def test_shared_filter_matches_same_as_list_items(svc):
    """The same ItemFilter selects the same items that list_items would (no drift)."""
    feat = (await svc.create(ItemType.FEATURE, "Feat")).item
    t1 = (await svc.create(ItemType.TASK, "T1", priority=Priority.HIGH, parent=feat.id)).item
    t2 = (await svc.create(ItemType.TASK, "T2", priority=Priority.LOW, parent=feat.id)).item
    _bug = (await svc.create(ItemType.BUG, "B1")).item

    # Filter: type=task, priority=high
    f = ItemFilter(item_type=ItemType.TASK, priority=Priority.HIGH)

    # list_items path
    listed = await svc.list_items(item_type=ItemType.TASK, priority=Priority.HIGH)
    listed_ids = {i.id for i in listed}

    # ItemFilter path
    all_items_listed = await svc.list_items()
    filter_ids = {i.id for i in all_items_listed if f.matches(i)}

    assert listed_ids == filter_ids
    assert t1.id in filter_ids
    assert t2.id not in filter_ids


# ---------------------------------------------------------------------------
# Service: tree_view — basic behaviour
# ---------------------------------------------------------------------------


async def _make_hierarchy(svc):
    """Create a 3-level hierarchy: EPIC → FEAT → TASK (and a standalone BUG).

    Returns (epic_id, feat_id, task_id, bug_id).
    """
    epic = (await svc.create(ItemType.EPIC, "Epic")).item
    feat = (await svc.create(ItemType.FEATURE, "Feature", parent=epic.id)).item
    task = (await svc.create(ItemType.TASK, "Task", parent=feat.id)).item
    bug = (await svc.create(ItemType.BUG, "Bug")).item
    return epic.id, feat.id, task.id, bug.id


async def test_tree_view_empty_filter_returns_all_open(svc):
    """Empty filter == today's tree: all open items appear."""
    epic_id, feat_id, task_id, bug_id = await _make_hierarchy(svc)
    nodes = await svc.tree_view()
    all_ids = _collect_ids(nodes)
    assert epic_id in all_ids
    assert feat_id in all_ids
    assert task_id in all_ids
    assert bug_id in all_ids


async def test_tree_view_filter_type(svc):
    """--type task shows only tasks (and their ancestors as path-only)."""
    epic_id, feat_id, task_id, bug_id = await _make_hierarchy(svc)
    nodes = await svc.tree_view(filter=ItemFilter(item_type=ItemType.TASK))
    all_ids = _collect_ids(nodes)
    assert task_id in all_ids
    # Epic and feat are ancestors of task → kept as path-only
    assert epic_id in all_ids
    assert feat_id in all_ids
    # Bug is not a task and has no matching descendants → dropped
    assert bug_id not in all_ids
    # Verify path_only flags
    path_only_ids = _collect_path_only_ids(nodes)
    assert epic_id in path_only_ids
    assert feat_id in path_only_ids
    assert task_id not in path_only_ids


async def test_tree_view_filter_priority(svc):
    """--priority filter narrows to matching items, with ancestors preserved."""
    epic_id, feat_id, task_id, bug_id = await _make_hierarchy(svc)
    await svc.update(task_id, priority=Priority.HIGH)

    nodes = await svc.tree_view(filter=ItemFilter(priority=Priority.HIGH))
    all_ids = _collect_ids(nodes)
    assert task_id in all_ids
    # Ancestors preserved as path-only
    assert epic_id in all_ids
    assert feat_id in all_ids
    # Bug has no priority matching high
    assert bug_id not in all_ids
    path_only_ids = _collect_path_only_ids(nodes)
    assert epic_id in path_only_ids
    assert feat_id in path_only_ids


async def test_tree_view_filter_assignee(svc):
    """--assignee filter shows only items with that assignee (+ ancestors)."""
    epic_id, feat_id, task_id, bug_id = await _make_hierarchy(svc)
    await svc.update(task_id, assignee="manager")

    nodes = await svc.tree_view(filter=ItemFilter(assignee="manager"))
    all_ids = _collect_ids(nodes)
    assert task_id in all_ids
    assert epic_id in all_ids
    assert feat_id in all_ids
    assert bug_id not in all_ids


async def test_tree_view_filter_combined_and(svc):
    """Combined filter = AND — type AND priority must both match."""
    _epic_id, _feat_id, task_id, _bug_id = await _make_hierarchy(svc)
    await svc.update(task_id, priority=Priority.HIGH)

    # type=task AND priority=high → task matches
    nodes = await svc.tree_view(filter=ItemFilter(item_type=ItemType.TASK, priority=Priority.HIGH))
    all_ids = _collect_ids(nodes)
    assert task_id in all_ids

    # type=bug AND priority=high → nothing matches
    nodes2 = await svc.tree_view(filter=ItemFilter(item_type=ItemType.BUG, priority=Priority.HIGH))
    assert _collect_ids(nodes2) == set()


async def test_tree_view_explicit_root(svc):
    """Explicit root limits the tree to the subtree under that root."""
    epic_id, feat_id, task_id, bug_id = await _make_hierarchy(svc)
    nodes = await svc.tree_view(feat_id)
    all_ids = _collect_ids(nodes)
    assert feat_id in all_ids
    assert task_id in all_ids
    # Epic is NOT in the subtree rooted at feat
    assert epic_id not in all_ids
    # Bug is not a descendant of feat
    assert bug_id not in all_ids


async def test_tree_view_explicit_root_with_filter(svc):
    """Explicit root + filter prunes within the subtree."""
    epic_id, feat_id, task_id, _bug_id = await _make_hierarchy(svc)
    await svc.update(task_id, priority=Priority.HIGH)

    # Root at feat, filter type=task
    nodes = await svc.tree_view(feat_id, filter=ItemFilter(item_type=ItemType.TASK))
    all_ids = _collect_ids(nodes)
    assert feat_id in all_ids  # feat is root, task matches → feat is path-only
    assert task_id in all_ids
    assert epic_id not in all_ids


# ---------------------------------------------------------------------------
# Service: ancestor preservation
# ---------------------------------------------------------------------------


async def test_tree_view_ancestor_preservation_no_orphan(svc):
    """A deep match always carries its full ancestor chain (no orphaned match)."""
    root = (await svc.create(ItemType.EPIC, "Root")).item
    mid = (await svc.create(ItemType.FEATURE, "Mid", parent=root.id)).item
    leaf = (await svc.create(ItemType.TASK, "Leaf", parent=mid.id)).item
    other = (await svc.create(ItemType.BUG, "Other")).item

    # Filter to task only — leaf should appear with its full ancestor chain
    nodes = await svc.tree_view(filter=ItemFilter(item_type=ItemType.TASK))
    all_ids = _collect_ids(nodes)
    assert leaf.id in all_ids
    assert mid.id in all_ids
    assert root.id in all_ids
    assert other.id not in all_ids  # has no task descendants

    # Root and mid are path-only; leaf is not
    path_only_ids = _collect_path_only_ids(nodes)
    assert root.id in path_only_ids
    assert mid.id in path_only_ids
    assert leaf.id not in path_only_ids


async def test_tree_view_path_only_flag_set_for_non_matching_ancestors(svc):
    """Ancestors that aren't themselves matches carry path_only=True."""
    root = (await svc.create(ItemType.EPIC, "Root")).item
    mid = (await svc.create(ItemType.FEATURE, "Mid", parent=root.id)).item
    leaf = (await svc.create(ItemType.TASK, "Leaf", parent=mid.id)).item

    nodes = await svc.tree_view(filter=ItemFilter(item_type=ItemType.TASK))
    root_node = nodes[0]
    assert root_node.item.id == root.id
    assert root_node.path_only is True
    assert len(root_node.children) == 1
    mid_node = root_node.children[0]
    assert mid_node.item.id == mid.id
    assert mid_node.path_only is True
    assert len(mid_node.children) == 1
    leaf_node = mid_node.children[0]
    assert leaf_node.item.id == leaf.id
    assert leaf_node.path_only is False


async def test_tree_view_matching_ancestor_not_path_only(svc):
    """If both a parent and its child match the filter, the parent is NOT path-only."""
    root = (await svc.create(ItemType.EPIC, "Root")).item
    feat = (await svc.create(ItemType.FEATURE, "Feat", parent=root.id)).item
    task = (await svc.create(ItemType.TASK, "Task", parent=feat.id)).item
    await svc.update(feat.id, priority=Priority.HIGH)
    await svc.update(task.id, priority=Priority.HIGH)

    nodes = await svc.tree_view(filter=ItemFilter(priority=Priority.HIGH))
    all_path_only = _collect_path_only_ids(nodes)
    # Both feat and task match → neither is path_only
    assert feat.id not in all_path_only
    assert task.id not in all_path_only
    # Root (epic) has no priority=high → is path_only
    assert root.id in all_path_only


# ---------------------------------------------------------------------------
# Service: depth truncation
# ---------------------------------------------------------------------------


async def test_tree_view_depth_zero_returns_roots_only(svc):
    """depth=0 shows only root-level items (their children are not rendered)."""
    epic_id, feat_id, task_id, bug_id = await _make_hierarchy(svc)
    nodes = await svc.tree_view(depth=0)
    # Roots (no parent): epic and bug
    assert any(n.item.id == epic_id for n in nodes)
    assert any(n.item.id == bug_id for n in nodes)
    # No children at any root
    for n in nodes:
        assert n.children == []
    # feat and task are NOT in the roots' children (depth=0)
    all_ids = _collect_ids(nodes)
    assert feat_id not in all_ids
    assert task_id not in all_ids


async def test_tree_view_depth_one(svc):
    """depth=1 shows roots + their direct children, nothing deeper."""
    epic_id, feat_id, task_id, bug_id = await _make_hierarchy(svc)
    nodes = await svc.tree_view(depth=1)
    all_ids = _collect_ids(nodes)
    assert epic_id in all_ids
    assert feat_id in all_ids  # one level down from epic
    assert task_id not in all_ids  # two levels down from epic
    assert bug_id in all_ids


async def test_tree_view_depth_wins_over_deep_match(svc):
    """--depth N wins: a match below the cut is NOT shown (not an 'orphaned match')."""
    root = (await svc.create(ItemType.EPIC, "Root")).item
    mid = (await svc.create(ItemType.FEATURE, "Mid", parent=root.id)).item
    leaf = (await svc.create(ItemType.TASK, "Leaf", parent=mid.id)).item
    await svc.update(leaf.id, priority=Priority.HIGH)

    # depth=1 means root (level 0) and mid (level 1) are in range;
    # leaf (level 2) is cut by depth — even though it matches the filter.
    nodes = await svc.tree_view(filter=ItemFilter(priority=Priority.HIGH), depth=1)
    all_ids = _collect_ids(nodes)
    assert leaf.id not in all_ids  # depth wins: match below cut is not shown
    # The in-depth ancestors (root, mid) still render since they ARE within depth
    # But mid is path_only and has no children within depth → mid is dropped (empty anchor)
    # root is also path_only with no children → root is dropped
    # Result: empty tree (no matches within depth)
    assert len(nodes) == 0


async def test_tree_view_depth_in_range_match_visible(svc):
    """A match within --depth is shown normally, with in-depth ancestors intact."""
    root = (await svc.create(ItemType.EPIC, "Root")).item
    mid = (await svc.create(ItemType.FEATURE, "Mid", parent=root.id)).item
    await svc.update(mid.id, priority=Priority.HIGH)

    # depth=1: mid is at level 1 from root → within depth; matches filter
    nodes = await svc.tree_view(filter=ItemFilter(priority=Priority.HIGH), depth=1)
    all_ids = _collect_ids(nodes)
    assert mid.id in all_ids
    assert root.id in all_ids  # root is path_only ancestor within depth


# ---------------------------------------------------------------------------
# Service: closed-item gate — mirrors list's behaviour
# ---------------------------------------------------------------------------


async def test_tree_view_closed_items_hidden_by_default(svc):
    """Closed items are not shown unless include_closed=True."""
    feat = (await svc.create(ItemType.FEATURE, "Feat")).item
    await svc.set_status(feat.id, Status.IN_PROGRESS)
    await svc.set_status(feat.id, Status.DONE)

    nodes = await svc.tree_view()
    assert feat.id not in _collect_ids(nodes)


async def test_tree_view_include_closed_shows_closed(svc):
    """include_closed=True reveals closed items."""
    feat = (await svc.create(ItemType.FEATURE, "Feat")).item
    await svc.set_status(feat.id, Status.IN_PROGRESS)
    await svc.set_status(feat.id, Status.DONE)

    nodes = await svc.tree_view(include_closed=True)
    assert feat.id in _collect_ids(nodes)


async def test_tree_view_status_filter_reveals_closed_match(svc):
    """A status filter that matches a closed item is used with include_closed=True."""
    feat = (await svc.create(ItemType.FEATURE, "Feat")).item
    await svc.set_status(feat.id, Status.IN_PROGRESS)
    await svc.set_status(feat.id, Status.DONE)

    # Without include_closed, the done item is in the candidate set only if include_closed
    # (the CLI passes include_closed based on whether --status or --all is given)
    nodes_closed = await svc.tree_view(filter=ItemFilter(status=Status.DONE), include_closed=True)
    assert feat.id in _collect_ids(nodes_closed)

    nodes_open = await svc.tree_view(filter=ItemFilter(status=Status.DONE))
    # Not in candidate set (include_closed=False), so even though status matches, not shown
    assert feat.id not in _collect_ids(nodes_open)


# ---------------------------------------------------------------------------
# CLI smoke tests
# ---------------------------------------------------------------------------


@pytest.fixture
def tree_squad(tmp_path, monkeypatch, frozen_time):
    """A seeded squad for CLI tree tests.

    Hierarchy:
      ROLE-000001  manager (minimal)
      EPIC-000002  Epic A
        FEAT-000003  Feature B  (parent=EPIC-000002)
          TASK-000004  Task C   (parent=FEAT-000003, priority=high)
      BUG-000005   Bug D        (standalone, priority=low)
    """
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    def inv(args: list[str]) -> None:
        r = runner.invoke(app, args)
        assert r.exit_code == 0, f"setup {args!r} failed (exit {r.exit_code}):\n{r.output}"

    inv(["init", "--no-seed-skills", "--roles", "minimal"])
    inv(["create", "epic", "Epic A", "--author", "manager"])
    inv(["create", "feature", "Feature B", "--author", "manager", "--parent", "EPIC-000002"])
    inv(
        [
            "create",
            "task",
            "Task C",
            "--author",
            "manager",
            "--parent",
            "FEAT-000003",
            "--priority",
            "high",
        ]
    )
    inv(["create", "bug", "Bug D", "--author", "manager", "--priority", "low"])

    return runner


def test_cli_tree_no_filters_renders_all(tree_squad):
    """sq tree with no filters renders all open items."""
    r = tree_squad.invoke(app, ["tree"])
    assert r.exit_code == 0, r.output
    assert "EPIC-000002" in r.output
    assert "FEAT-000003" in r.output
    assert "TASK-000004" in r.output
    assert "BUG-000005" in r.output


def test_cli_tree_filter_type(tree_squad):
    """sq tree --type task shows only tasks (ancestors dimmed)."""
    r = tree_squad.invoke(app, ["tree", "--type", "task"])
    assert r.exit_code == 0, r.output
    assert "TASK-000004" in r.output
    # Ancestors must appear (path-only, dimmed)
    assert "EPIC-000002" in r.output
    assert "FEAT-000003" in r.output
    # Bug has no task descendants → not shown
    assert "BUG-000005" not in r.output


def test_cli_tree_filter_priority(tree_squad):
    """sq tree --priority high shows only high-priority items + their ancestors."""
    r = tree_squad.invoke(app, ["tree", "--priority", "high"])
    assert r.exit_code == 0, r.output
    assert "TASK-000004" in r.output
    assert "EPIC-000002" in r.output
    assert "FEAT-000003" in r.output
    # Bug D is low priority → not shown
    assert "BUG-000005" not in r.output


def test_cli_tree_filter_assignee(tmp_path, monkeypatch, frozen_time):
    """sq tree --assignee manager shows only manager-assigned items + ancestors."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    def inv(args: list[str]) -> None:
        r = runner.invoke(app, args)
        assert r.exit_code == 0, f"setup {args!r} failed (exit {r.exit_code}):\n{r.output}"

    inv(["init", "--no-seed-skills", "--roles", "minimal"])
    inv(["create", "epic", "Epic", "--author", "manager"])
    inv(["create", "feature", "Feat", "--author", "manager", "--parent", "EPIC-000002"])
    inv(["create", "task", "Task", "--author", "manager", "--parent", "FEAT-000003"])
    inv(["task", "4", "update", "--assignee", "manager"])

    r = runner.invoke(app, ["tree", "--assignee", "manager"])
    assert r.exit_code == 0, r.output
    assert "TASK-000004" in r.output
    assert "FEAT-000003" in r.output
    assert "EPIC-000002" in r.output


def test_cli_tree_filter_status(tree_squad):
    """sq tree --status Draft shows only draft items."""
    r = tree_squad.invoke(app, ["tree", "--status", "Draft"])
    assert r.exit_code == 0, r.output
    # All items are Draft by default — all should appear
    assert "TASK-000004" in r.output


def test_cli_tree_filter_combined(tree_squad):
    """sq tree --type task --priority high: both filters applied (AND)."""
    r = tree_squad.invoke(app, ["tree", "--type", "task", "--priority", "high"])
    assert r.exit_code == 0, r.output
    assert "TASK-000004" in r.output
    assert "BUG-000005" not in r.output


def test_cli_tree_depth(tree_squad):
    """sq tree --depth 1 shows only the top two levels (root and direct children)."""
    r = tree_squad.invoke(app, ["tree", "--depth", "1"])
    assert r.exit_code == 0, r.output
    assert "EPIC-000002" in r.output
    assert "FEAT-000003" in r.output  # level 1 from epic
    # Task is at level 2 from epic → not shown
    assert "TASK-000004" not in r.output


def test_cli_tree_depth_zero(tree_squad):
    """sq tree --depth 0 shows only top-level items (roots, no children)."""
    r = tree_squad.invoke(app, ["tree", "--depth", "0"])
    assert r.exit_code == 0, r.output
    assert "EPIC-000002" in r.output
    assert "BUG-000005" in r.output
    assert "FEAT-000003" not in r.output
    assert "TASK-000004" not in r.output


def test_cli_tree_explicit_root(tree_squad):
    """sq tree FEAT-000003 shows only the subtree rooted at that feature."""
    r = tree_squad.invoke(app, ["tree", "FEAT-000003"])
    assert r.exit_code == 0, r.output
    assert "FEAT-000003" in r.output
    assert "TASK-000004" in r.output
    assert "EPIC-000002" not in r.output
    assert "BUG-000005" not in r.output


def test_cli_tree_explicit_root_with_filter(tree_squad):
    """sq tree FEAT-000003 --type task works within the subtree."""
    r = tree_squad.invoke(app, ["tree", "FEAT-000003", "--type", "task"])
    assert r.exit_code == 0, r.output
    assert "TASK-000004" in r.output
    assert "FEAT-000003" in r.output
    assert "EPIC-000002" not in r.output


async def test_path_only_ancestors_flagged_and_match_not(svc):
    """Service layer: path-only ancestors carry path_only=True; the matching node does not.

    This is the authoritative assertion for the dim/path-only distinction.  The CLI
    renders path-only nodes inside [dim]...[/dim], which CliRunner strips — the
    service test is the reliable boundary to assert on.
    """
    root = (await svc.create(ItemType.EPIC, "Root")).item
    mid = (await svc.create(ItemType.FEATURE, "Mid", parent=root.id)).item
    leaf = (await svc.create(ItemType.TASK, "Leaf", parent=mid.id)).item

    nodes = await svc.tree_view(filter=ItemFilter(item_type=ItemType.TASK))
    path_only_ids = _collect_path_only_ids(nodes)
    all_ids = _collect_ids(nodes)

    # Ancestors are in the tree but are path-only (will be dimmed at the CLI edge)
    assert root.id in path_only_ids, "root ancestor must be path_only=True"
    assert mid.id in path_only_ids, "mid ancestor must be path_only=True"
    # The matching leaf is in the tree but is NOT path-only
    assert leaf.id in all_ids, "matching leaf must appear"
    assert leaf.id not in path_only_ids, "matching leaf must NOT be path_only"


def test_cli_tree_status_reveals_closed_with_status_flag(tmp_path, monkeypatch, frozen_time):
    """--status Done reveals matching closed items (mirrors list's closed-item gate)."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    def inv(args: list[str]) -> None:
        r = runner.invoke(app, args)
        assert r.exit_code == 0, f"setup {args!r} failed:\n{r.output}"

    inv(["init", "--no-seed-skills", "--roles", "minimal"])
    inv(["create", "feature", "F", "--author", "manager"])
    inv(["feature", "2", "status", "InProgress"])
    inv(["feature", "2", "status", "Done"])

    r_with_status = runner.invoke(app, ["tree", "--status", "Done"])
    assert r_with_status.exit_code == 0, r_with_status.output
    assert "FEAT-000002" in r_with_status.output


def test_cli_tree_non_status_filter_does_not_widen_to_closed(tmp_path, monkeypatch, frozen_time):
    """--priority/--assignee/--type alone do NOT reveal closed items."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    def inv(args: list[str]) -> None:
        r = runner.invoke(app, args)
        assert r.exit_code == 0, f"setup {args!r} failed:\n{r.output}"

    inv(["init", "--no-seed-skills", "--roles", "minimal"])
    inv(["create", "feature", "F", "--author", "manager", "--priority", "high"])
    inv(["feature", "2", "status", "InProgress"])
    inv(["feature", "2", "status", "Done"])

    r = runner.invoke(app, ["tree", "--priority", "high"])
    assert r.exit_code == 0, r.output
    # Feature is Done (closed) and not widened to closed by --priority alone
    assert "FEAT-000002" not in r.output


def test_cli_tree_all_includes_closed(tmp_path, monkeypatch, frozen_time):
    """sq tree --all shows closed items."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    def inv(args: list[str]) -> None:
        r = runner.invoke(app, args)
        assert r.exit_code == 0, f"setup {args!r} failed:\n{r.output}"

    inv(["init", "--no-seed-skills", "--roles", "minimal"])
    inv(["create", "feature", "F", "--author", "manager"])
    inv(["feature", "2", "status", "InProgress"])
    inv(["feature", "2", "status", "Done"])

    r_no_all = runner.invoke(app, ["tree"])
    r_all = runner.invoke(app, ["tree", "--all"])
    assert r_no_all.exit_code == 0
    assert r_all.exit_code == 0
    assert "FEAT-000002" not in r_no_all.output
    assert "FEAT-000002" in r_all.output


# ---------------------------------------------------------------------------
# CLI: --json shape (pruned, NOT reshaped)
# ---------------------------------------------------------------------------


def test_cli_tree_json_no_path_only_key(tree_squad):
    """--json output must NOT contain a path_only key in any node."""
    r = tree_squad.invoke(app, ["tree", "--json", "--type", "task"])
    assert r.exit_code == 0, r.output
    assert "\x1b[" not in r.output, "--json emitted ANSI escape codes"
    data = json.loads(r.output)
    _assert_no_path_only_in_json(data)


def test_cli_tree_json_same_shape_as_unfiltered(tree_squad):
    """--json nodes have exactly the same keys filtered and unfiltered."""
    r_all = tree_squad.invoke(app, ["tree", "--json"])
    r_filtered = tree_squad.invoke(app, ["tree", "--json", "--type", "task"])
    assert r_all.exit_code == 0
    assert r_filtered.exit_code == 0

    def collect_node_keys(nodes: list[dict[str, object]]) -> set[frozenset[str]]:
        keys: set[frozenset[str]] = set()
        for n in nodes:
            keys.add(frozenset(n.keys()))
            keys |= collect_node_keys(n.get("children", []))  # type: ignore[arg-type]
        return keys

    all_keys = collect_node_keys(json.loads(r_all.output))
    filtered_keys = collect_node_keys(json.loads(r_filtered.output))
    assert all_keys == filtered_keys
    expected_keys: frozenset[str] = frozenset(
        {"id", "type", "status", "priority", "assignee", "blocked", "children"}
    )
    assert all_keys == {expected_keys}


def test_cli_tree_json_is_ansi_free(tree_squad):
    """--json output is ANSI-free unconditionally (BUG-000183 regression)."""
    r = tree_squad.invoke(app, ["tree", "--json"])
    assert r.exit_code == 0, r.output
    assert "\x1b[" not in r.output, "sq tree --json emitted ANSI escape codes"
    json.loads(r.output)  # must be valid JSON


def test_cli_tree_json_pruned_consistently(tree_squad):
    """--json tree is pruned to the same nodes as the rendered tree."""
    # Filter to task only: only task + its ancestors should appear
    r = tree_squad.invoke(app, ["tree", "--json", "--type", "task"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)

    def collect_json_ids(nodes: list[dict[str, object]]) -> set[str]:
        ids: set[str] = set()
        for n in nodes:
            ids.add(str(n["id"]))
            ids |= collect_json_ids(n.get("children", []))  # type: ignore[arg-type]
        return ids

    ids = collect_json_ids(data)
    assert "TASK-000004" in ids
    assert "FEAT-000003" in ids
    assert "EPIC-000002" in ids
    assert "BUG-000005" not in ids  # no task descendants


def test_cli_tree_json_golden(tree_squad):
    """sq tree --json --type task: golden-test the exact shape."""
    r = tree_squad.invoke(app, ["tree", "--json", "--type", "task"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    _check_golden("tree_task_json", data)


def test_cli_tree_json_depth(tree_squad):
    """sq tree --json --depth 1 omits nodes beyond depth 1."""
    r = tree_squad.invoke(app, ["tree", "--json", "--depth", "1"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)

    def collect_json_ids(nodes: list[dict[str, object]]) -> set[str]:
        ids: set[str] = set()
        for n in nodes:
            ids.add(str(n["id"]))
            ids |= collect_json_ids(n.get("children", []))  # type: ignore[arg-type]
        return ids

    ids = collect_json_ids(data)
    assert "EPIC-000002" in ids
    assert "FEAT-000003" in ids
    assert "TASK-000004" not in ids  # depth=1 cuts before level 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collect_ids(nodes: list[TreeNode]) -> set[str]:
    ids: set[str] = set()
    for n in nodes:
        ids.add(n.item.id)
        ids |= _collect_ids(n.children)
    return ids


def _collect_path_only_ids(nodes: list[TreeNode]) -> set[str]:
    ids: set[str] = set()
    for n in nodes:
        if n.path_only:
            ids.add(n.item.id)
        ids |= _collect_path_only_ids(n.children)
    return ids


def _assert_no_path_only_in_json(nodes: list[dict[str, object]]) -> None:
    for n in nodes:
        assert "path_only" not in n, f"path_only key found in JSON node {n.get('id')}"
        assert "match" not in n, f"match key found in JSON node {n.get('id')}"
        _assert_no_path_only_in_json(n.get("children", []))  # type: ignore[arg-type]
