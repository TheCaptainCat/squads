"""Dynamic content containing literal bracket sequences (e.g. `[/dim]`) must render as plain
text, not crash the Textual content-markup parser — across every Static/Tree-label surface
that interpolates free-form item/discussion/search text.
"""

import pytest

pytest.importorskip("textual")

from textual.widgets import ListView, Markdown, Static
from textual.widgets.tree import TreeNode

from squads._tui._app import SquadsApp
from squads._tui._browse import BrowseScreen
from squads._tui._search import SearchScreen, _HitItem  # pyright: ignore[reportPrivateUsage]

pytestmark = pytest.mark.anyio

_BRACKETY = "has a [/dim] stray closing tag, a [Note] callout, and [bold]nested[/bold] markup"


def _find(root: TreeNode[str], item_id: str) -> TreeNode[str]:
    """Find *item_id* anywhere under *root* — items nest under the category groups."""
    nodes = [root]
    while nodes:
        node = nodes.pop()
        if node.data == item_id:
            return node
        nodes.extend(node.children)
    raise LookupError(item_id)


async def test_a_tree_item_title_with_brackets_renders_without_crashing(svc):
    feat = (await svc.create("feature", f"Title {_BRACKETY}")).item

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        browse = app.screen
        assert isinstance(browse, BrowseScreen)
        node = _find(browse._tree.root, feat.id)  # pyright: ignore[reportPrivateUsage]
        assert _BRACKETY in str(node.label)


async def test_a_discussion_comment_with_brackets_renders_without_crashing(svc):
    feat = (await svc.create("feature", "Chatty")).item
    await svc.comment(feat.id, [f"comment {_BRACKETY}"], as_slug="manager")

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        browse = app.screen
        assert isinstance(browse, BrowseScreen)
        node = _find(browse._tree.root, feat.id)  # pyright: ignore[reportPrivateUsage]
        browse._tree.cursor_line = node.line  # pyright: ignore[reportPrivateUsage]
        await pilot.pause()

        disc_view = browse.query_one("#discussion-view", Markdown)
        assert _BRACKETY in disc_view._markdown  # pyright: ignore[reportPrivateUsage]


async def test_a_glance_assignee_with_brackets_renders_without_crashing(svc, monkeypatch):
    # Assignee is validated against registered participants (slugs can't carry brackets), so a
    # bracket-laden assignee can only come from an on-disk file edited outside `sq` — simulate
    # that by having `svc.get` return an item with one, exercising the real render path for it.
    feat = (await svc.create("feature", "Assigned")).item
    mutated = (await svc.get(feat.id)).model_copy(update={"assignee": f"weird {_BRACKETY}"})
    original_get = type(svc).get

    async def _get(self: object, item_id: str) -> object:
        return mutated if item_id == feat.id else await original_get(self, item_id)

    monkeypatch.setattr(type(svc), "get", _get)

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        browse = app.screen
        assert isinstance(browse, BrowseScreen)
        node = _find(browse._tree.root, feat.id)  # pyright: ignore[reportPrivateUsage]
        browse._tree.cursor_line = node.line  # pyright: ignore[reportPrivateUsage]
        await pilot.pause()

        header = browse.query_one("#glance-header", Static)
        assert _BRACKETY in str(header.content)


async def test_a_sub_entity_body_with_brackets_renders_without_crashing(svc):
    feat = (await svc.create("feature", "Has stories")).item
    await svc.add_story(feat.id, "Login")
    await svc.set_story_body(feat.id, "US1", f"body prose {_BRACKETY}")

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        browse = app.screen
        assert isinstance(browse, BrowseScreen)
        node = _find(browse._tree.root, feat.id)  # pyright: ignore[reportPrivateUsage]
        browse._tree.cursor_line = node.line  # pyright: ignore[reportPrivateUsage]
        await pilot.pause()

        sub_view = browse.query_one("#subentities-view", Markdown)
        assert _BRACKETY in sub_view._markdown  # pyright: ignore[reportPrivateUsage]


async def test_a_search_snippet_with_brackets_renders_without_crashing(svc):
    await svc.create("feature", f"Findable {_BRACKETY}", body=f"needle-xyz {_BRACKETY}")

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("/")
        await pilot.pause()
        search = app.screen
        assert isinstance(search, SearchScreen)

        search._query.value = "needle-xyz"  # pyright: ignore[reportPrivateUsage]
        await pilot.press("enter")
        await pilot.pause()

        results = search.query_one(ListView)
        hits = [c for c in results.children if isinstance(c, _HitItem)]
        assert len(hits) == 1
        row_static = hits[0].query_one(Static)
        assert _BRACKETY in str(row_static.content)
