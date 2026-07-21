"""`ReaderScreen`: the standalone item reader, pushed wherever an item must open outside
the browse tree (reused for search hits in the follow-up increment).
"""

import pytest

pytest.importorskip("textual")

from textual.app import App
from textual.widgets import Markdown, Static

from squads._tui._reader import ReaderScreen

pytestmark = pytest.mark.anyio


async def test_reader_screen_loads_the_item_and_pops_on_escape(svc):
    feat = (await svc.create("feature", "Standalone", body="Hello world")).item

    app = App[None]()
    async with app.run_test() as pilot:
        await app.push_screen(ReaderScreen(svc, feat.id))
        await pilot.pause()

        header = app.screen.query_one("#glance-header", Static)
        assert "Draft" in str(header.content)
        body = app.screen.query_one("#body-view", Markdown)
        assert "Hello world" in body._markdown  # pyright: ignore[reportPrivateUsage]

        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, ReaderScreen)
