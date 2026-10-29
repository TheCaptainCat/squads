"""The board screen: current notices, newest-first — a modal peer to `FilterScreen`/
`SearchScreen`, opened by a keybinding on `BrowseScreen`. Read-only: no post/clear path."""

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import VerticalScroll
from textual.content import Content
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Markdown, Static

from squads._api import _ops as ops
from squads._api._dto._board import BoardListRequest, NoticeRow
from squads._tui._session import Session

_EMPTY = "*(no notices)*"


def _skipped_note(count: int) -> Content:
    """Mirrors `_search.py`'s `_skipped_note`: the notices shown are real but partial."""
    files = "file" if count == 1 else "files"
    return Content.from_markup(
        "[yellow]$count notice $files could not be read — listing partial[/yellow]",
        count=str(count),
        files=files,
    )


def _notice_block(notice: NoticeRow) -> str:
    header = f"**{notice.author}** — {notice.posted_at}"
    if notice.until:
        header += f" (expires {notice.until})"
    return f"{header}\n\n{notice.body}"


class BoardScreen(ModalScreen[None]):
    """Read-only listing of current board notices, newest-first; escape closes it."""

    BINDINGS: ClassVar[list[BindingType]] = [("escape", "close", "Back")]

    DEFAULT_CSS = """
    BoardScreen #board-body-scroll {
        height: 1fr;
    }
    """

    def __init__(self, session: Session) -> None:
        super().__init__()
        self._session = session
        self._status = Static(id="board-status")
        self._body = Markdown(id="board-body")

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="board-body-scroll"):
            yield self._body
        yield self._status
        yield Footer()

    async def on_mount(self) -> None:
        listed = await self._session.call(ops.BOARD_LIST, BoardListRequest())
        unreadable = listed.omitted
        newest_first = sorted(listed.data.items, key=lambda n: (n.posted_at, n.id), reverse=True)
        md = "\n\n---\n\n".join(_notice_block(n) for n in newest_first) if newest_first else _EMPTY
        await self._body.update(md)
        self._status.update(_skipped_note(len(unreadable)) if unreadable else "")

    def action_close(self) -> None:
        self.dismiss()
