"""The board screen: current notices, newest-first — a modal peer to `FilterScreen`/
`SearchScreen`, opened by a keybinding on `BrowseScreen`. Read-only: no post/clear path."""

import re
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import VerticalScroll
from textual.content import Content
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Markdown, Static

from squads._api import BoardListRequest, BoardShowRequest, NoticeDetail, ops
from squads._errors import SquadsError
from squads._tui._session import Session

_EMPTY = "*(no notices)*"


def _skipped_note(count: int) -> Content:
    """The notices shown are real but partial: *count* could not be read or changed meanwhile."""
    notices = "notice" if count == 1 else "notices"
    return Content.from_markup(
        "[yellow]$count $notices could not be shown — listing partial[/yellow]",
        count=str(count),
        notices=notices,
    )


def _bold_lines(text: str) -> str:
    """*text* as markdown with each non-blank line bold on its own, so a blank line cannot break
    the emphasis; markdown punctuation is escaped."""
    escaped = re.sub(r"([\\`*_\[\]<>#])", r"\\\1", text)
    return "\n".join(f"**{line}**" if line.strip() else "" for line in escaped.splitlines())


def _notice_block(notice: NoticeDetail) -> str:
    header = f"**{notice.author}** — {notice.posted_at}"
    if notice.until:
        header += f" (expires {notice.until})"
    text = f"{header}\n\n{_bold_lines(notice.summary)}".rstrip("\n")
    return f"{text}\n\n{notice.body}" if notice.body else text


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
        skipped = len(listed.omitted)
        notices: list[NoticeDetail] = []
        for row in listed.data.items:
            try:
                shown = await self._session.call(ops.BOARD_SHOW, BoardShowRequest(n=row.n))
            except SquadsError:
                skipped += 1
                continue
            if shown.data.id == row.id:
                notices.append(shown.data)
            else:
                skipped += 1
        newest_first = sorted(notices, key=lambda n: (n.posted_at, n.id), reverse=True)
        md = "\n\n---\n\n".join(_notice_block(n) for n in newest_first) if newest_first else _EMPTY
        await self._body.update(md)
        self._status.update(_skipped_note(skipped) if skipped else "")

    def action_close(self) -> None:
        self.dismiss()
