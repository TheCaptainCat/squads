"""`ReaderScreen`: the standalone item reader, pushed wherever an item must open outside
the browse tree."""

import pytest

from _helpers import create_item

pytest.importorskip("textual")

from textual.app import App
from textual.widgets import Markdown, Static

from squads._tui._reader import ReaderScreen

from ._helpers import wait_until

pytestmark = pytest.mark.anyio


async def test_reader_screen_loads_the_item_and_pops_on_escape(svc):
    feat = (await create_item(svc, "feature", "Standalone", body="Hello world")).item

    app = App[None]()
    async with app.run_test() as pilot:
        await app.push_screen(ReaderScreen(svc, feat.id))

        header = app.screen.query_one("#glance-header", Static)
        body = app.screen.query_one("#body-view", Markdown)
        await wait_until(pilot, lambda: "Hello world" in body._markdown)
        assert "Draft" in str(header.content)

        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, ReaderScreen)


async def test_reader_screen_shows_a_view_tags_rendered_output_not_the_literal_tag(svc):
    """The TUI reader inherits view-tag expansion from ``Service.read_body`` directly."""
    task = (await create_item(svc, "task", "T")).item
    await svc.add_view(task.id, "milestone_rollup")
    expected = (await svc.render_view("milestone_rollup", task.id)).strip()

    app = App[None]()
    async with app.run_test() as pilot:
        await app.push_screen(ReaderScreen(svc, task.id))

        body = app.screen.query_one("#body-view", Markdown)
        await wait_until(pilot, lambda: expected in body._markdown)
        assert "sq:view:milestone_rollup" not in body._markdown


async def test_reader_screen_expands_no_tag_and_no_index_load_for_an_untagged_body(
    svc, monkeypatch
):
    """A browse-tree selection with no view tag never reaches expansion at all, driven
    through the real component."""
    from squads import _views as views

    feat = (await create_item(svc, "feature", "Standalone", body="Hello world")).item

    calls: list[str] = []
    original = views.expand_view_tags

    def counted(*args, **kwargs):
        calls.append(args[1].id)
        return original(*args, **kwargs)

    monkeypatch.setattr(views, "expand_view_tags", counted)

    app = App[None]()
    async with app.run_test() as pilot:
        await app.push_screen(ReaderScreen(svc, feat.id))

        body = app.screen.query_one("#body-view", Markdown)
        await wait_until(pilot, lambda: "Hello world" in body._markdown)

    assert calls == [], "an untagged body must never reach view-tag expansion"
