"""`SearchScreen`: open from browse, query -> results with snippets, the empty-query and
no-results states, and escape back to browse.
"""

import anyio
import pytest

pytest.importorskip("textual")

from textual.content import Content
from textual.widgets import ListView
from textual.widgets.tree import TreeNode

from squads._tui._app import SquadsApp
from squads._tui._browse import BrowseScreen
from squads._tui._reader import ReaderScreen
from squads._tui._search import (
    SearchScreen,
    _HitItem,  # pyright: ignore[reportPrivateUsage]
)

pytestmark = pytest.mark.anyio


def _find(root: TreeNode[str], item_id: str) -> TreeNode[str]:
    """Find *item_id* anywhere under *root* — items nest under the Work/Roster groups."""
    nodes = [root]
    while nodes:
        node = nodes.pop()
        if node.data == item_id:
            return node
        nodes.extend(node.children)
    raise LookupError(item_id)


def _status_text(search: SearchScreen) -> str:
    content = search._status.content  # pyright: ignore[reportPrivateUsage]
    if isinstance(content, Content):
        return content.plain
    assert isinstance(content, str)
    return content


async def test_search_key_opens_the_full_screen_search_page(svc):
    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        browse = app.screen
        assert isinstance(browse, BrowseScreen)

        await pilot.press("/")
        await pilot.pause()

        assert isinstance(app.screen, SearchScreen)


async def test_submitting_a_query_lists_hits_with_id_type_title_and_snippets(svc):
    feat = (await svc.create("feature", "Login flow", body="Implements OAuth login")).item

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("/")
        await pilot.pause()
        search = app.screen
        assert isinstance(search, SearchScreen)

        search._query.value = "oauth"  # pyright: ignore[reportPrivateUsage]
        await pilot.press("enter")
        await pilot.pause()

        results = search.query_one(ListView)
        hits = [c for c in results.children if isinstance(c, _HitItem)]
        assert len(hits) == 1
        assert hits[0].item_id == feat.id


async def test_blank_query_shows_the_prompt_state_without_calling_search(svc, monkeypatch):
    calls: list[str] = []
    original = type(svc).search

    async def _spy(self: object, text: str, **kwargs: object) -> object:
        calls.append(text)
        return await original(self, text, **kwargs)

    monkeypatch.setattr(type(svc), "search", _spy)

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("/")
        await pilot.pause()
        search = app.screen
        assert isinstance(search, SearchScreen)

        search._query.value = "   "  # pyright: ignore[reportPrivateUsage]
        await pilot.press("enter")
        await pilot.pause()

        assert "type to search" in _status_text(search).lower()
        assert not calls


async def test_a_query_with_no_matches_shows_a_clean_no_results_state(svc):
    await svc.create("feature", "Unrelated")

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("/")
        await pilot.pause()
        search = app.screen
        assert isinstance(search, SearchScreen)

        search._query.value = "no-such-needle-xyz"  # pyright: ignore[reportPrivateUsage]
        await pilot.press("enter")
        await pilot.pause()

        assert "no results" in _status_text(search).lower()
        assert len(search.query_one(ListView).children) == 0


async def test_results_list_fills_the_remaining_screen_height(svc):
    app = SquadsApp(svc)
    async with app.run_test(size=(80, 30)) as pilot:
        await pilot.pause()
        await pilot.press("/")
        await pilot.pause()
        search = app.screen
        assert isinstance(search, SearchScreen)

        filters_row = search.query_one("#search-filters")
        results = search.query_one(ListView)
        assert results.size.height > filters_row.size.height * 2


async def test_a_searching_state_is_shown_while_the_worker_runs(svc, monkeypatch):
    await svc.create("feature", "Findable", body="needle-xyz here")
    gate = anyio.Event()
    original = type(svc).search

    async def _gated(self: object, text: str, **kwargs: object) -> object:
        await gate.wait()
        return await original(self, text, **kwargs)

    monkeypatch.setattr(type(svc), "search", _gated)

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
        assert search.query_one(ListView).loading
        assert "search" in _status_text(search).lower()

        gate.set()
        await pilot.pause()
        await pilot.pause()
        assert not search.query_one(ListView).loading


async def test_escape_returns_to_browse_with_the_tree_position_intact(svc):
    feat = (await svc.create("feature", "Alpha")).item

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        browse = app.screen
        assert isinstance(browse, BrowseScreen)
        node = _find(browse._tree.root, feat.id)  # pyright: ignore[reportPrivateUsage]
        browse._tree.cursor_line = node.line  # pyright: ignore[reportPrivateUsage]
        await pilot.pause()

        await pilot.press("/")
        await pilot.pause()
        assert isinstance(app.screen, SearchScreen)

        await pilot.press("escape")
        await pilot.pause()

        assert app.screen is browse
        cursor_node = browse._tree.cursor_node  # pyright: ignore[reportPrivateUsage]
        assert cursor_node is not None
        assert cursor_node.data == feat.id


async def test_type_and_status_narrowing_are_forwarded_to_svc_search(svc, monkeypatch):
    calls: list[tuple[str, str | None, str | None]] = []
    original = type(svc).search

    async def _spy(self: object, text: str, **kwargs: object):
        item_type = kwargs.get("item_type")
        status = kwargs.get("status")
        calls.append((text, item_type, status))  # pyright: ignore[reportArgumentType]
        return await original(self, text, **kwargs)

    monkeypatch.setattr(type(svc), "search", _spy)
    feat = (await svc.create("feature", "OAuth flow")).item
    task = (await svc.create("task", "OAuth task", parent=feat.id)).item

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("/")
        await pilot.pause()
        search = app.screen
        assert isinstance(search, SearchScreen)

        search._query.value = "oauth"  # pyright: ignore[reportPrivateUsage]
        await pilot.press("enter")
        await pilot.pause()
        assert calls[-1] == ("oauth", None, None)

        search._type_select.value = "task"  # pyright: ignore[reportPrivateUsage]
        await pilot.pause()
        assert calls[-1] == ("oauth", "task", None)

        results = search.query_one(ListView)
        hits = [c for c in results.children if isinstance(c, _HitItem)]
        assert {h.item_id for h in hits} == {task.id}
        assert feat.id not in {h.item_id for h in hits}


async def test_selecting_a_hit_pushes_a_reader_screen_without_moving_browse_selection(svc):
    feat = (await svc.create("feature", "Alpha", body="oauth token flow")).item
    closed = (await svc.create("feature", "Legacy", body="oauth legacy code")).item
    await svc.update(closed.id, status="Done", force=True)

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        browse = app.screen
        assert isinstance(browse, BrowseScreen)
        feat_node = _find(browse._tree.root, feat.id)  # pyright: ignore[reportPrivateUsage]
        browse._tree.cursor_line = feat_node.line  # pyright: ignore[reportPrivateUsage]
        await pilot.pause()

        await pilot.press("/")
        await pilot.pause()
        search = app.screen
        assert isinstance(search, SearchScreen)

        search._query.value = "oauth"  # pyright: ignore[reportPrivateUsage]
        await pilot.press("enter")
        await pilot.pause()

        results = search.query_one(ListView)
        hits = [c for c in results.children if isinstance(c, _HitItem)]
        assert {h.item_id for h in hits} == {feat.id, closed.id}  # closed hit still found

        closed_hit = next(h for h in hits if h.item_id == closed.id)
        results.index = list(results.children).index(closed_hit)
        results.focus()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        reader = app.screen
        assert isinstance(reader, ReaderScreen)

        await pilot.press("escape")
        await pilot.pause()
        assert app.screen is search

        await pilot.press("escape")
        await pilot.pause()
        assert app.screen is browse
        cursor_node = browse._tree.cursor_node  # pyright: ignore[reportPrivateUsage]
        assert cursor_node is not None
        assert cursor_node.data == feat.id  # browse selection untouched by the search excursion
