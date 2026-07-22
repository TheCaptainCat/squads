"""`FilterScreen`: open/dismiss over `BrowseScreen`, seeded from and returning a
`BrowseState`, narrowing the tree while keeping ancestors of matches visible.
"""

import pytest

pytest.importorskip("textual")

from textual.widgets import Button, Select

from squads._tui._app import SquadsApp
from squads._tui._browse import BrowseScreen
from squads._tui._filter import FilterScreen

pytestmark = pytest.mark.anyio


def _all_ids(tree_screen: BrowseScreen) -> set[str]:
    ids: set[str] = set()

    def _walk(node: object) -> None:
        data = getattr(node, "data", None)
        if data:
            ids.add(data)
        for child in node.children:  # pyright: ignore[reportAttributeAccessIssue]
            _walk(child)

    _walk(tree_screen._tree.root)  # pyright: ignore[reportPrivateUsage]
    return ids


async def test_escape_dismisses_the_popup_without_applying_pending_changes(svc):
    await svc.create("feature", "Alpha")

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        browse = app.screen
        assert isinstance(browse, BrowseScreen)

        await pilot.press("f")
        await pilot.pause()
        popup = app.screen
        assert isinstance(popup, FilterScreen)
        popup._type_select.value = "task"  # pyright: ignore[reportPrivateUsage]

        await pilot.press("escape")
        await pilot.pause()

        assert app.screen is browse
        assert browse.state.filter.item_type is None


async def test_applying_a_type_filter_narrows_the_tree_keeping_an_ancestor_visible(svc):
    feat = (await svc.create("feature", "Alpha")).item
    task = (await svc.create("task", "Sub", parent=feat.id)).item

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        browse = app.screen
        assert isinstance(browse, BrowseScreen)

        await pilot.press("f")
        await pilot.pause()
        popup = app.screen
        assert isinstance(popup, FilterScreen)
        popup._type_select.value = "task"  # pyright: ignore[reportPrivateUsage]
        popup.query_one("#apply", Button).press()
        await pilot.pause()

        assert app.screen is browse
        ids = _all_ids(browse)
        assert task.id in ids
        assert feat.id in ids  # ancestor of the match kept as context


async def test_applying_returns_a_new_state_and_a_later_open_is_seeded_from_it(svc):
    await svc.create("feature", "Alpha")

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        browse = app.screen
        assert isinstance(browse, BrowseScreen)

        await pilot.press("f")
        await pilot.pause()
        popup = app.screen
        assert isinstance(popup, FilterScreen)
        popup._type_select.value = "feature"  # pyright: ignore[reportPrivateUsage]
        popup.query_one("#apply", Button).press()
        await pilot.pause()

        assert browse.state.filter.item_type == "feature"

        await pilot.press("f")
        await pilot.pause()
        reopened = app.screen
        assert isinstance(reopened, FilterScreen)
        assert reopened._type_select.value == "feature"  # pyright: ignore[reportPrivateUsage]


async def test_show_closed_toggle_reveals_and_hides_a_done_item(svc):
    closed = (await svc.create("feature", "Retired")).item
    await svc.update(closed.id, status="Done", force=True)

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        browse = app.screen
        assert isinstance(browse, BrowseScreen)
        assert closed.id not in _all_ids(browse)

        await pilot.press("f")
        await pilot.pause()
        popup = app.screen
        assert isinstance(popup, FilterScreen)
        popup._show_closed_switch.value = True  # pyright: ignore[reportPrivateUsage]
        popup.query_one("#apply", Button).press()
        await pilot.pause()
        assert closed.id in _all_ids(browse)

        await pilot.press("f")
        await pilot.pause()
        popup2 = app.screen
        assert isinstance(popup2, FilterScreen)
        popup2._show_closed_switch.value = False  # pyright: ignore[reportPrivateUsage]
        popup2.query_one("#apply", Button).press()
        await pilot.pause()
        assert closed.id not in _all_ids(browse)


async def test_sort_by_title_reorders_siblings_without_crossing_levels(svc):
    zeta = (await svc.create("feature", "Zeta")).item
    alpha = (await svc.create("feature", "Alpha")).item
    child = (await svc.create("task", "Only child", parent=zeta.id)).item

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        browse = app.screen
        assert isinstance(browse, BrowseScreen)

        await pilot.press("f")
        await pilot.pause()
        popup = app.screen
        assert isinstance(popup, FilterScreen)
        popup._sort_select.value = "title"  # pyright: ignore[reportPrivateUsage]
        popup.query_one("#apply", Button).press()
        await pilot.pause()

        work_group = browse._tree.root.children[0]  # pyright: ignore[reportPrivateUsage]
        top_level = [n.data for n in work_group.children if n.data in (zeta.id, alpha.id)]
        assert top_level == [alpha.id, zeta.id]  # "Alpha" sorts before "Zeta"

        zeta_node = next(n for n in work_group.children if n.data == zeta.id)
        assert [c.data for c in zeta_node.children] == [child.id]  # still nested under Zeta


async def test_clear_resets_the_popup_and_applying_reproduces_the_default_view(svc):
    closed = (await svc.create("feature", "Retired")).item
    await svc.update(closed.id, status="Done", force=True)

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        browse = app.screen
        assert isinstance(browse, BrowseScreen)

        await pilot.press("f")
        await pilot.pause()
        popup = app.screen
        assert isinstance(popup, FilterScreen)
        popup._type_select.value = "feature"  # pyright: ignore[reportPrivateUsage]
        popup._show_closed_switch.value = True  # pyright: ignore[reportPrivateUsage]
        popup._sort_select.value = "title"  # pyright: ignore[reportPrivateUsage]
        popup.query_one("#apply", Button).press()
        await pilot.pause()
        assert not browse.state.is_default()

        await pilot.press("f")
        await pilot.pause()
        popup2 = app.screen
        assert isinstance(popup2, FilterScreen)
        popup2.query_one("#clear", Button).press()
        await pilot.pause()
        assert not browse.state.is_default()  # clearing alone doesn't apply yet
        popup2.query_one("#apply", Button).press()
        await pilot.pause()

        assert browse.state.is_default()


async def test_applying_a_category_filter_round_trips_into_browse_state(svc):
    await svc.create("feature", "Alpha")
    decision = (await svc.create("decision", "Use widgets")).item

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        browse = app.screen
        assert isinstance(browse, BrowseScreen)

        await pilot.press("f")
        await pilot.pause()
        popup = app.screen
        assert isinstance(popup, FilterScreen)
        popup._category_select.value = "records"  # pyright: ignore[reportPrivateUsage]
        popup.query_one("#apply", Button).press()
        await pilot.pause()

        assert browse.state.filter.category == "records"
        ids = _all_ids(browse)
        assert decision.id in ids

        await pilot.press("f")
        await pilot.pause()
        reopened = app.screen
        assert isinstance(reopened, FilterScreen)
        assert reopened._category_select.value == "records"  # pyright: ignore[reportPrivateUsage]

        reopened.query_one("#clear", Button).press()
        await pilot.pause()
        assert reopened._category_select.value is Select.NULL  # pyright: ignore[reportPrivateUsage]
        reopened.query_one("#apply", Button).press()
        await pilot.pause()
        assert browse.state.filter.category is None


async def test_active_filter_indicator_shows_only_while_filtered(svc):
    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        browse = app.screen
        assert isinstance(browse, BrowseScreen)
        assert browse._indicator.content == ""  # pyright: ignore[reportPrivateUsage]

        await pilot.press("f")
        await pilot.pause()
        popup = app.screen
        assert isinstance(popup, FilterScreen)
        popup._type_select.value = "feature"  # pyright: ignore[reportPrivateUsage]
        popup.query_one("#apply", Button).press()
        await pilot.pause()
        assert browse._indicator.content != ""  # pyright: ignore[reportPrivateUsage]

        await pilot.press("f")
        await pilot.pause()
        popup2 = app.screen
        assert isinstance(popup2, FilterScreen)
        popup2.query_one("#clear", Button).press()
        popup2.query_one("#apply", Button).press()
        await pilot.pause()
        assert browse._indicator.content == ""  # pyright: ignore[reportPrivateUsage]
