"""`BoardScreen`: opened by a keybinding on `BrowseScreen`, lists current notices newest-first
with author/posted-at/expiry/body, reports unreadable notices rather than dropping them
silently, and escape closes it back to browse — read-only throughout (no post/clear path).
"""

import pytest

from _helpers import make_unreadable_by_the_os

pytest.importorskip("textual")

from textual.widgets import Markdown, Static

from squads._tui._app import SquadsApp
from squads._tui._board import BoardScreen
from squads._tui._browse import BrowseScreen

from ._helpers import wait_until

pytestmark = pytest.mark.anyio


def _board_folder(svc):
    return svc.paths.squad_dir / "board"


async def test_the_board_keybinding_opens_and_escape_closes_it(svc):
    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, BrowseScreen)

        await pilot.press("b")
        await pilot.pause()
        assert isinstance(app.screen, BoardScreen)

        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, BrowseScreen)


async def test_notices_render_newest_first_with_author_posted_at_expiry_and_body(svc):
    await svc.board_post("manager", "the older notice", until="2030-01-01")
    await svc.board_post("op-alice", "the newer notice")

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.press("b")
        await pilot.pause()
        body = app.screen.query_one("#board-body", Markdown)
        await wait_until(pilot, lambda: "the newer notice" in body._markdown)

        text = body._markdown
        assert "the older notice" in text
        assert "op-alice" in text
        assert "manager" in text
        assert "2030-01-01" in text
        # Newest-first: the second-posted notice's body precedes the first-posted's.
        assert text.index("the newer notice") < text.index("the older notice")


async def test_an_empty_board_renders_without_error(svc):
    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.press("b")
        await pilot.pause()
        body = app.screen.query_one("#board-body", Markdown)
        await wait_until(pilot, lambda: "no notices" in body._markdown)


async def test_an_unreadable_notice_is_reported_not_silently_dropped(svc):
    await svc.board_post("manager", "a readable notice")
    bad = await svc.board_post("manager", "a notice about to go bad")
    undo = make_unreadable_by_the_os(_board_folder(svc) / f"{bad.id}.md")
    try:
        app = SquadsApp(svc)
        async with app.run_test() as pilot:
            await pilot.press("b")
            await pilot.pause()
            body = app.screen.query_one("#board-body", Markdown)
            await wait_until(pilot, lambda: "a readable notice" in body._markdown)
            assert "a notice about to go bad" not in body._markdown

            status = app.screen.query_one("#board-status", Static)
            await wait_until(pilot, lambda: "could not be read" in str(status.content))
            assert "partial" in str(status.content)
    finally:
        undo()


async def test_a_notice_body_with_brackets_renders_literally(svc):
    bracketed = "has a [/dim] stray closing tag and a [Note] callout"
    await svc.board_post("manager", bracketed)

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.press("b")
        await pilot.pause()
        body = app.screen.query_one("#board-body", Markdown)
        await wait_until(pilot, lambda: bracketed in body._markdown)
