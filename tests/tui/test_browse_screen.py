"""`BrowseScreen`: tree/`svc.tree_view()` parity, keyboard navigation, and the embedded
reader panel (selection wiring, at-a-glance header, body/sub-entities/discussion tabs +
their empty states).
"""

import pytest

pytest.importorskip("textual")

from textual.containers import VerticalScroll
from textual.content import Content
from textual.widgets import Markdown, Static, TabbedContent, Tabs, Tree
from textual.widgets._markdown import (  # pyright: ignore[reportPrivateImportUsage]
    MarkdownH1,
    MarkdownParagraph,
)
from textual.widgets.tree import TreeNode

from squads._tui._app import SquadsApp

pytestmark = pytest.mark.anyio


def _ids(node: TreeNode[str]) -> set[str]:
    out = {node.data} if node.data else set()
    for child in node.children:
        out |= _ids(child)
    return out


def _find(root: TreeNode[str], item_id: str) -> TreeNode[str]:
    """Find *item_id* anywhere under *root* — items now nest under the Work/Roster groups."""
    for node in _ids_with_nodes(root):
        if node.data == item_id:
            return node
    raise LookupError(item_id)


def _ids_with_nodes(node: TreeNode[str]):
    yield node
    for child in node.children:
        yield from _ids_with_nodes(child)


def _text(content: object) -> str:
    if isinstance(content, Content):
        return content.plain
    assert isinstance(content, str)
    return content


async def test_launching_and_quitting_leaves_no_running_app(svc):
    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        assert app.is_running
        await pilot.press("q")
    assert not app.is_running


async def test_tree_matches_the_service_tree_view_structure(svc):
    epic = (await svc.create("epic", "Epic")).item
    feat = (await svc.create("feature", "Feature", parent=epic.id)).item
    task = (await svc.create("task", "Task", parent=feat.id)).item

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.screen.query_one(Tree)
        assert _ids(tree.root) >= {epic.id, feat.id, task.id}

        expected_roots = {n.item.id for n in await svc.tree_view()}
        work_group, roster_group = tree.root.children
        actual_roots = {c.data for c in work_group.children} | {
            c.data for c in roster_group.children
        }
        assert actual_roots == expected_roots


async def test_tree_splits_top_level_into_work_and_roster_groups(svc):
    epic = (await svc.create("epic", "Epic")).item
    feat = (await svc.create("feature", "Feature")).item

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.screen.query_one(Tree)
        assert [str(n.label) for n in tree.root.children] == ["Work", "Roster"]

        work_group, roster_group = tree.root.children
        work_ids = {c.data for c in work_group.children}
        roster_ids = {c.data for c in roster_group.children}

        assert {epic.id, feat.id} <= work_ids
        assert roster_ids == {"ROLE-1"}  # the "minimal" fixture's only registered role
        assert work_ids.isdisjoint(roster_ids)


async def test_keyboard_moves_between_siblings_into_children_and_back_to_parent(svc):
    feat = (await svc.create("feature", "Feature")).item
    task1 = (await svc.create("task", "Task one", parent=feat.id)).item
    task2 = (await svc.create("task", "Task two", parent=feat.id)).item

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.screen.query_one(Tree)
        feat_node = _find(tree.root, feat.id)
        tree.cursor_line = feat_node.line
        await pilot.pause()

        await pilot.press("down")
        await pilot.pause()
        assert tree.cursor_node is not None
        assert tree.cursor_node.data == task1.id

        await pilot.press("down")
        await pilot.pause()
        assert tree.cursor_node is not None
        assert tree.cursor_node.data == task2.id

        await pilot.press("shift+left")
        await pilot.pause()
        assert tree.cursor_node is not None
        assert tree.cursor_node.data == feat.id


async def test_selecting_a_node_loads_its_detail_and_reselection_refreshes_it(svc):
    feat1 = (await svc.create("feature", "First", body="First body")).item
    feat2 = (await svc.create("feature", "Second", body="Second body")).item

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.screen.query_one(Tree)
        node1 = _find(tree.root, feat1.id)
        node2 = _find(tree.root, feat2.id)

        tree.cursor_line = node1.line
        await pilot.pause()
        body = app.screen.query_one("#body-view", Markdown)
        assert "First body" in body._markdown  # pyright: ignore[reportPrivateUsage]

        tree.cursor_line = node2.line
        await pilot.pause()
        assert "Second body" in body._markdown  # pyright: ignore[reportPrivateUsage]


async def test_reader_header_shows_status_priority_and_assignee_gracefully(svc):
    with_priority = (
        await svc.create("feature", "Prioritized", priority="high", assignee="manager")
    ).item
    bare = (await svc.create("feature", "Bare")).item

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.screen.query_one(Tree)
        node = _find(tree.root, with_priority.id)
        tree.cursor_line = node.line
        await pilot.pause()
        header = app.screen.query_one("#glance-header", Static)
        assert "Draft" in _text(header.content)
        assert "High" in _text(header.content)
        assert "manager" in _text(header.content)

        bare_node = _find(tree.root, bare.id)
        tree.cursor_line = bare_node.line
        await pilot.pause()
        assert "unassigned" in _text(header.content)


async def test_body_tab_renders_markdown_blocks_and_an_empty_state_for_a_blank_body(svc):
    with_body = (await svc.create("feature", "Doc'd", body="# Heading\n\nSome text.")).item
    blank = (await svc.create("feature", "Blank", body="")).item

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.screen.query_one(Tree)
        node = _find(tree.root, with_body.id)
        tree.cursor_line = node.line
        await pilot.pause()
        body = app.screen.query_one("#body-view", Markdown)
        assert any(isinstance(w, MarkdownH1) for w in body.children)
        assert any(isinstance(w, MarkdownParagraph) for w in body.children)

        blank_node = _find(tree.root, blank.id)
        tree.cursor_line = blank_node.line
        await pilot.pause()
        assert "no body yet" in body._markdown  # pyright: ignore[reportPrivateUsage]


async def test_body_tab_scrolls_to_reach_content_below_the_fold(svc):
    tall_body = "\n\n".join(f"Paragraph {i}" for i in range(200))
    tall = (await svc.create("feature", "Tall", body=tall_body)).item

    app = SquadsApp(svc)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        tree = app.screen.query_one(Tree)
        node = _find(tree.root, tall.id)
        tree.cursor_line = node.line
        await pilot.pause()

        scroll = app.screen.query_one("#body-scroll", VerticalScroll)
        assert scroll.max_scroll_y > 0

        scroll.focus()
        await pilot.pause()
        await pilot.press("end")
        await pilot.pause()
        assert scroll.scroll_y == scroll.max_scroll_y


async def test_subentities_tab_shows_each_blocks_head_and_body_with_empty_states(svc):
    feat = (await svc.create("feature", "Has stories")).item
    await svc.add_story(feat.id, "Login", assignee="manager")
    await svc.set_story_body(feat.id, "US1", "Some story prose.")
    feat_empty = (await svc.create("feature", "No stories")).item
    role = await svc.get("ROLE-1")

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.screen.query_one(Tree)

        node = _find(tree.root, feat.id)
        tree.cursor_line = node.line
        await pilot.pause()
        sub_view = app.screen.query_one("#subentities-view", Markdown)
        source = sub_view._markdown  # pyright: ignore[reportPrivateUsage]
        assert "US1" in source
        assert "Login" in source
        assert "manager" in source
        assert "Some story prose." in source

        empty_node = _find(tree.root, feat_empty.id)
        tree.cursor_line = empty_node.line
        await pilot.pause()
        assert sub_view._markdown == "*(none)*"  # pyright: ignore[reportPrivateUsage]

        role_node = _find(tree.root, role.id)
        tree.cursor_line = role_node.line
        await pilot.pause()
        assert sub_view._markdown == "*(none)*"  # pyright: ignore[reportPrivateUsage]


async def test_discussion_tab_renders_markdown_ordered_comments_and_empty_state(svc):
    feat = (await svc.create("feature", "Chatty")).item
    await svc.comment(feat.id, ["first\n- a bullet"], as_slug="manager")
    await svc.comment(feat.id, ["second"], as_slug="manager")
    quiet = (await svc.create("feature", "Quiet")).item

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.screen.query_one(Tree)

        node = _find(tree.root, feat.id)
        tree.cursor_line = node.line
        await pilot.pause()
        disc_view = app.screen.query_one("#discussion-view", Markdown)
        source = disc_view._markdown  # pyright: ignore[reportPrivateUsage]
        assert source.index("first") < source.index("second")
        assert await svc.author("manager") in source
        assert any(isinstance(w, MarkdownParagraph) for w in disc_view.children)

        quiet_node = _find(tree.root, quiet.id)
        tree.cursor_line = quiet_node.line
        await pilot.pause()
        assert disc_view._markdown == "*(none)*"  # pyright: ignore[reportPrivateUsage]


async def test_reader_tabs_are_switchable_by_keyboard(svc):
    feat = (await svc.create("feature", "Feature")).item

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.screen.query_one(Tree)
        node = _find(tree.root, feat.id)
        tree.cursor_line = node.line
        await pilot.pause()

        tabs = app.screen.query_one(TabbedContent)
        assert tabs.active == "tab-body"
        app.screen.query_one(Tabs).focus()
        await pilot.pause()

        await pilot.press("right")
        await pilot.pause()
        assert tabs.active == "tab-subentities"

        await pilot.press("right")
        await pilot.pause()
        assert tabs.active == "tab-discussion"
