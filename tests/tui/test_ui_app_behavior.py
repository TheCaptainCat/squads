"""The `sq ui` Textual app: tree/`svc.tree_view()` parity, keyboard navigation, and the
reader panel (selection wiring, at-a-glance header, body/sub-entities/discussion tabs +
their empty states).
"""

import io

import pytest

pytest.importorskip("textual")

from rich.console import Console
from rich.table import Table
from textual.containers import VerticalScroll
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


def _text(content: object) -> str:
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
        tree = app.query_one(Tree)
        assert _ids(tree.root) >= {epic.id, feat.id, task.id}

        expected_children = {n.item.id for n in await svc.tree_view()}
        actual_top_level = {child.data for child in tree.root.children}
        assert actual_top_level == expected_children


async def test_keyboard_moves_between_siblings_into_children_and_back_to_parent(svc):
    feat = (await svc.create("feature", "Feature")).item
    task1 = (await svc.create("task", "Task one", parent=feat.id)).item
    task2 = (await svc.create("task", "Task two", parent=feat.id)).item

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.query_one(Tree)
        feat_node = next(n for n in tree.root.children if n.data == feat.id)
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
        tree = app.query_one(Tree)
        node1 = next(n for n in tree.root.children if n.data == feat1.id)
        node2 = next(n for n in tree.root.children if n.data == feat2.id)

        tree.cursor_line = node1.line
        await pilot.pause()
        body = app.query_one("#body-view", Markdown)
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
        tree = app.query_one(Tree)
        node = next(n for n in tree.root.children if n.data == with_priority.id)
        tree.cursor_line = node.line
        await pilot.pause()
        header = app.query_one("#glance-header", Static)
        assert "Draft" in _text(header.content)
        assert "High" in _text(header.content)
        assert "manager" in _text(header.content)

        bare_node = next(n for n in tree.root.children if n.data == bare.id)
        tree.cursor_line = bare_node.line
        await pilot.pause()
        assert "unassigned" in _text(header.content)


async def test_body_tab_renders_markdown_blocks_and_an_empty_state_for_a_blank_body(svc):
    with_body = (await svc.create("feature", "Doc'd", body="# Heading\n\nSome text.")).item
    blank = (await svc.create("feature", "Blank", body="")).item

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.query_one(Tree)
        node = next(n for n in tree.root.children if n.data == with_body.id)
        tree.cursor_line = node.line
        await pilot.pause()
        body = app.query_one("#body-view", Markdown)
        assert any(isinstance(w, MarkdownH1) for w in body.children)
        assert any(isinstance(w, MarkdownParagraph) for w in body.children)

        blank_node = next(n for n in tree.root.children if n.data == blank.id)
        tree.cursor_line = blank_node.line
        await pilot.pause()
        assert "no body yet" in body._markdown  # pyright: ignore[reportPrivateUsage]


async def test_body_tab_scrolls_to_reach_content_below_the_fold(svc):
    tall_body = "\n\n".join(f"Paragraph {i}" for i in range(200))
    tall = (await svc.create("feature", "Tall", body=tall_body)).item

    app = SquadsApp(svc)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        tree = app.query_one(Tree)
        node = next(n for n in tree.root.children if n.data == tall.id)
        tree.cursor_line = node.line
        await pilot.pause()

        scroll = app.query_one("#body-scroll", VerticalScroll)
        assert scroll.max_scroll_y > 0

        scroll.focus()
        await pilot.pause()
        await pilot.press("end")
        await pilot.pause()
        assert scroll.scroll_y == scroll.max_scroll_y


async def test_subentities_tab_lists_rows_and_shows_empty_states(svc):
    feat = (await svc.create("feature", "Has stories")).item
    await svc.add_story(feat.id, "Login", assignee="manager")
    feat_empty = (await svc.create("feature", "No stories")).item
    role = await svc.get("ROLE-1")

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.query_one(Tree)

        node = next(n for n in tree.root.children if n.data == feat.id)
        tree.cursor_line = node.line
        await pilot.pause()
        sub_view = app.query_one("#subentities-view", Static)
        assert isinstance(sub_view.content, Table)
        buf = io.StringIO()
        Console(width=100, file=buf).print(sub_view.content)
        rendered = buf.getvalue()
        assert "Login" in rendered
        assert "manager" in rendered

        empty_node = next(n for n in tree.root.children if n.data == feat_empty.id)
        tree.cursor_line = empty_node.line
        await pilot.pause()
        assert sub_view.content == "[dim](none)[/dim]"

        role_node = next(n for n in tree.root.children if n.data == role.id)
        tree.cursor_line = role_node.line
        await pilot.pause()
        assert sub_view.content == "[dim](none)[/dim]"


async def test_discussion_tab_lists_ordered_comments_and_shows_empty_state(svc):
    feat = (await svc.create("feature", "Chatty")).item
    await svc.comment(feat.id, ["first"], as_slug="manager")
    await svc.comment(feat.id, ["second"], as_slug="manager")
    quiet = (await svc.create("feature", "Quiet")).item

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.query_one(Tree)

        node = next(n for n in tree.root.children if n.data == feat.id)
        tree.cursor_line = node.line
        await pilot.pause()
        disc_view = app.query_one("#discussion-view", Static)
        rendered = _text(disc_view.content)
        assert rendered.index("first") < rendered.index("second")
        assert await svc.author("manager") in rendered

        quiet_node = next(n for n in tree.root.children if n.data == quiet.id)
        tree.cursor_line = quiet_node.line
        await pilot.pause()
        assert disc_view.content == "[dim](none)[/dim]"


async def test_reader_tabs_are_switchable_by_keyboard(svc):
    feat = (await svc.create("feature", "Feature")).item

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.query_one(Tree)
        node = next(n for n in tree.root.children if n.data == feat.id)
        tree.cursor_line = node.line
        await pilot.pause()

        tabs = app.query_one(TabbedContent)
        assert tabs.active == "tab-body"
        app.query_one(Tabs).focus()
        await pilot.pause()

        await pilot.press("right")
        await pilot.pause()
        assert tabs.active == "tab-subentities"

        await pilot.press("right")
        await pilot.pause()
        assert tabs.active == "tab-discussion"
