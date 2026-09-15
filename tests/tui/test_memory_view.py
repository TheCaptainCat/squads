"""Role/Operator identities under Roster nest their memory pool as tree children: a
glance-level count + most-recent-entry age on the identity's own label before anything is
expanded, entries as children ordered oldest-touched first (ties broken by slug), a
degraded-partial signal when a pool file can't be read, and skill nodes gaining nothing.
Selecting a memory child opens a memory-shaped reader, never the item `ReaderPanel`.
"""

from datetime import UTC, datetime

import pytest

from _helpers import create_item, make_unreadable_by_the_os

pytest.importorskip("textual")

from textual.widgets import ContentSwitcher, Markdown, Static, Tree
from textual.widgets.tree import TreeNode

from squads import _clock as clock
from squads._tui._app import SquadsApp
from squads._tui._tree import MemoryNodeData, NodeData

from ._helpers import wait_until

pytestmark = pytest.mark.anyio

_ROLE_ID = "ROLE-1"
_ROLE_SLUG = "manager"  # the "minimal" fixture's only registered role


def _role_memory_folder(svc):
    return svc.paths.squad_dir / "agents" / "memory" / _ROLE_SLUG


def _find_item(root: TreeNode[NodeData], item_id: str) -> TreeNode[NodeData]:
    nodes = [root]
    while nodes:
        node = nodes.pop()
        if node.data == item_id:
            return node
        nodes.extend(node.children)
    raise LookupError(item_id)


def _find_memory_child(
    root: TreeNode[NodeData], role_slug: str, entry_slug: str
) -> TreeNode[NodeData]:
    nodes = [root]
    while nodes:
        node = nodes.pop()
        data = node.data
        if (
            isinstance(data, MemoryNodeData)
            and data.role_slug == role_slug
            and data.entry_slug == entry_slug
        ):
            return node
        nodes.extend(node.children)
    raise LookupError((role_slug, entry_slug))


async def test_a_role_node_with_an_empty_pool_shows_zero_before_expansion(svc):
    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.screen.query_one(Tree)
        node = _find_item(tree.root, _ROLE_ID)
        assert "memory: 0" in str(node.label)
        assert len(node.children) == 0


async def test_a_role_node_with_entries_shows_count_and_recency_before_expansion(svc, frozen_time):
    await svc.memory_add(_ROLE_SLUG, "a fact worth remembering")

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.screen.query_one(Tree)
        node = _find_item(tree.root, _ROLE_ID)
        label = str(node.label)
        assert "memory: 1" in label
        assert "ago" in label or "just now" in label


async def test_an_operator_node_also_gets_a_memory_count(svc):
    op = await svc.add_operator("Alice", slug="op-alice")
    await svc.memory_add("op-alice", "an operator-authored fact")

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.screen.query_one(Tree)
        node = _find_item(tree.root, op.id)
        assert "memory: 1" in str(node.label)


async def test_a_skill_node_gains_no_memory_signal_or_children(svc):
    skill = await svc.add_skill("Do the thing")

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.screen.query_one(Tree)
        node = _find_item(tree.root, skill.id)
        assert "memory" not in str(node.label)
        assert len(node.children) == 0


async def test_expanding_a_role_node_lists_entries_oldest_first_with_stable_slug_tiebreak(svc):
    clock.set_now(datetime(2026, 1, 1, tzinfo=UTC))
    await svc.memory_add(_ROLE_SLUG, "an older fact", slug="older")
    clock.set_now(datetime(2026, 6, 1, tzinfo=UTC))
    # Two entries at the same later instant: order between them must fall back to slug.
    await svc.memory_add(_ROLE_SLUG, "b tie", slug="b-tie")
    await svc.memory_add(_ROLE_SLUG, "a tie", slug="a-tie")

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.screen.query_one(Tree)
        role_node = _find_item(tree.root, _ROLE_ID)
        child_slugs = [
            c.data.entry_slug for c in role_node.children if isinstance(c.data, MemoryNodeData)
        ]
        assert child_slugs == ["older", "a-tie", "b-tie"]


async def test_a_pool_with_an_unreadable_file_still_lists_readable_entries_and_flags_partial(
    svc,
):
    good = await svc.memory_add(_ROLE_SLUG, "a readable fact", slug="good")
    bad = await svc.memory_add(_ROLE_SLUG, "a fact about to go bad", slug="bad")
    undo = make_unreadable_by_the_os(_role_memory_folder(svc) / f"{bad.slug}.md")
    try:
        app = SquadsApp(svc)
        async with app.run_test() as pilot:
            await pilot.pause()
            tree = app.screen.query_one(Tree)
            role_node = _find_item(tree.root, _ROLE_ID)
            child_slugs = [
                c.data.entry_slug for c in role_node.children if isinstance(c.data, MemoryNodeData)
            ]
            assert child_slugs == [good.slug]
            note_labels = [str(c.label) for c in role_node.children if c.data is None]
            assert any("could not be read" in label for label in note_labels)
            assert any("partial" in label for label in note_labels)
    finally:
        undo()


async def test_selecting_a_memory_child_opens_the_memory_reader_not_the_item_reader(svc):
    entry = await svc.memory_add(
        _ROLE_SLUG, "a fact with a distinctive body", body="Distinctive body prose."
    )

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.screen.query_one(Tree)
        role_node = _find_item(tree.root, _ROLE_ID)
        role_node.expand()
        await pilot.pause()

        child = _find_memory_child(tree.root, _ROLE_SLUG, entry.slug)
        tree.cursor_line = child.line
        await pilot.pause()

        switcher = app.screen.query_one("#reader-switcher", ContentSwitcher)
        assert switcher.current == "memory-reader-panel"

        header = app.screen.query_one("#memory-glance-header", Static)
        await wait_until(pilot, lambda: entry.slug in str(header.content))

        body = app.screen.query_one("#memory-body-view", Markdown)
        await wait_until(pilot, lambda: "Distinctive body prose." in body._markdown)


async def test_selecting_an_item_after_a_memory_child_switches_back_to_the_item_reader(svc):
    feat = (await create_item(svc, "feature", "Feature", body="Feature body.")).item
    entry = await svc.memory_add(_ROLE_SLUG, "a fact")

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.screen.query_one(Tree)
        role_node = _find_item(tree.root, _ROLE_ID)
        role_node.expand()
        await pilot.pause()

        child = _find_memory_child(tree.root, _ROLE_SLUG, entry.slug)
        tree.cursor_line = child.line
        await pilot.pause()
        switcher = app.screen.query_one("#reader-switcher", ContentSwitcher)
        assert switcher.current == "memory-reader-panel"

        feat_node = _find_item(tree.root, feat.id)
        tree.cursor_line = feat_node.line
        await pilot.pause()
        assert switcher.current == "reader-panel"

        body = app.screen.query_one("#body-view", Markdown)
        await wait_until(pilot, lambda: "Feature body." in body._markdown)
