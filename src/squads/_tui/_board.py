"""The board screen: current notices, newest-first — a modal peer to `FilterScreen`/
`SearchScreen`, opened by a keybinding on `BrowseScreen`. Read-only: no post/clear path."""

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import VerticalScroll
from textual.content import Content
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Markdown, Static

from squads._board._model import BoardNotice
from squads._services._service import Service

_EMPTY = "*(no notices)*"


def _skipped_note(count: int) -> Content:
    """Mirrors `_search.py`'s `_skipped_note`: the notices shown are real but partial."""
    files = "file" if count == 1 else "files"
    return Content.from_markup(
        "[yellow]$count notice $files could not be read — listing partial[/yellow]",
        count=str(count),
        files=files,
    )


def _notice_block(notice: BoardNotice) -> str:
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

    def __init__(self, svc: Service) -> None:
        super().__init__()
        self._svc = svc
        self._status = Static(id="board-status")
        self._body = Markdown(id="board-body")

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="board-body-scroll"):
            yield self._body
        yield self._status
        yield Footer()

    async def on_mount(self) -> None:
        notices, unreadable = await self._svc.board_list()
        newest_first = sorted(notices, key=lambda n: (n.posted_at, n.id), reverse=True)
        md = "\n\n---\n\n".join(_notice_block(n) for n in newest_first) if newest_first else _EMPTY
        await self._body.update(md)
        self._status.update(_skipped_note(len(unreadable)) if unreadable else "")

    def action_close(self) -> None:
        self.dismiss()
