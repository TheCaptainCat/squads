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
    """A genuinely empty pool (no entries, nothing unreadable) collapses to a leaf -- a
    `memory: 0` you could nonetheless expand invites a click that answers nothing."""
    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.screen.query_one(Tree)
        node = _find_item(tree.root, _ROLE_ID)
        assert "memory: 0" in str(node.label)
        assert len(node.children) == 0
        assert node.allow_expand is False


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


async def test_a_skill_sharing_the_roles_slug_gains_no_memory_signal_or_children(svc):
    """Eligibility is a function of item type alone, not a slug lookup. `do-the-thing` above
    cannot collide with anything, so it cannot fail for the defect this drives -- a skill
    slugified to the *same* string as the role's own slug (`add_skill("Manager")` -> "manager")
    must still get no glance suffix and no children, while the role keeps both."""
    skill = await svc.add_skill("Manager")
    assert skill.extra["slug"] == _ROLE_SLUG  # the collision this test depends on
    await svc.memory_add(_ROLE_SLUG, "a fact belonging to the role, not the skill")

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.screen.query_one(Tree)
        skill_node = _find_item(tree.root, skill.id)
        assert "memory" not in str(skill_node.label)
        assert len(skill_node.children) == 0

        role_node = _find_item(tree.root, _ROLE_ID)
        assert "memory: 1" in str(role_node.label)


async def test_a_role_node_with_item_children_keeps_its_memory_signal_and_children(svc):
    """Gating the memory branch on `not node.children` (rather than on item type) would
    silently drop the whole signal the moment an eligible identity also has real item
    children. Unreachable through the bundled spec (roster types declare no parents) but
    reachable the instant a squad's own spec parents a type under role -- so this drives the
    shape directly against the real render path (`tree_view` -> `populate_tree`) rather than
    skipping it as "can't happen today"."""
    await svc.memory_add(_ROLE_SLUG, "a fact")
    child = (await create_item(svc, "task", "a child of a role")).item
    async with svc.store.transaction() as db:
        db.get(child.id).parent = _ROLE_ID

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.screen.query_one(Tree)
        role_node = _find_item(tree.root, _ROLE_ID)
        assert "memory: 1" in str(role_node.label)
        assert role_node.allow_expand is True
        item_children = [c.data for c in role_node.children if isinstance(c.data, str)]
        assert item_children == [child.id]
        memory_children = [c.data for c in role_node.children if isinstance(c.data, MemoryNodeData)]
        assert len(memory_children) == 1


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


async def test_a_pool_whose_files_are_all_unreadable_keeps_its_branch_not_a_leaf(svc):
    """Asserted separately from the genuinely-empty case above so the two cannot be folded
    into one condition by mistake: a pool that reads `memory: 0` only because every file in it
    failed to read must keep its branch -- the partial-listing child is a real child, and
    collapsing it to a leaf would hide the reason the count reads zero."""
    bad = await svc.memory_add(_ROLE_SLUG, "about to go entirely unreadable", slug="bad")
    undo = make_unreadable_by_the_os(_role_memory_folder(svc) / f"{bad.slug}.md")
    try:
        app = SquadsApp(svc)
        async with app.run_test() as pilot:
            await pilot.pause()
            tree = app.screen.query_one(Tree)
            role_node = _find_item(tree.root, _ROLE_ID)
            assert "memory: 0" in str(role_node.label)
            assert role_node.allow_expand is True
            assert len(role_node.children) == 1
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


_BRACKETY = "a [bold red]summary[/] with [/dim] and [x] brackets"


async def test_a_memory_tree_leaf_label_with_brackets_renders_literally(svc):
    """A memory summary is free-form and may contain literal bracket sequences, which Rich
    would otherwise parse as markup. Content is spans built by `Text.assemble`, never a markup
    string built by concatenation, so it must render as plain text."""
    await svc.memory_add(_ROLE_SLUG, _BRACKETY, slug="bracketed")

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.screen.query_one(Tree)
        role_node = _find_item(tree.root, _ROLE_ID)
        role_node.expand()
        await pilot.pause()

        child = _find_memory_child(tree.root, _ROLE_SLUG, "bracketed")
        assert _BRACKETY in str(child.label)


async def test_a_role_glance_suffix_survives_a_bracketed_summary_elsewhere_in_the_pool(svc):
    """The glance suffix itself (`memory: N · age`) is a fixed, never-free-form string, so the
    thing worth falsifying is that a bracketed *sibling* entry's summary cannot corrupt it --
    proven by asserting the suffix is intact on the identity's own label next to the bracketed
    child above."""
    await svc.memory_add(_ROLE_SLUG, _BRACKETY, slug="bracketed")

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.screen.query_one(Tree)
        role_node = _find_item(tree.root, _ROLE_ID)
        assert "memory: 1" in str(role_node.label)


async def test_the_memory_reader_header_with_brackets_and_a_bracketed_tag_renders_literally(svc):
    """Same bracket family, on the memory reader's glance header -- summary is not shown there
    (only slug/created-at/tags), so the tag is what carries free-form bracket content through
    this surface."""
    entry = await svc.memory_add(
        _ROLE_SLUG, "a fact with a bracketed tag", slug="tagged", tags=["[tag]"]
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

        header = app.screen.query_one("#memory-glance-header", Static)
        await wait_until(pilot, lambda: "[tag]" in str(header.content))
