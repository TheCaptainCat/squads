"""The `sq ui` Textual application: a thin shell that pushes the browse screen."""

from typing import ClassVar

from textual.app import App
from textual.binding import BindingType

from squads._tui._browse import BrowseScreen, BrowseState, BrowseView, fetch_view
from squads._tui._session import ApiSelector, Session


async def open_session(select_api: ApiSelector) -> tuple[Session, BrowseView]:
    """A session on *select_api* with its catalogs loaded, and the first view of the tree: a
    refusal surfaces here, before the app starts."""
    session = Session(select_api)
    await session.load_catalogs()
    return session, await fetch_view(session, BrowseState())


class SquadsApp(App[None]):
    """The `sq ui` shell: holds the session and pushes `BrowseScreen` on its opening view."""

    TITLE = "sq ui"
    BINDINGS: ClassVar[list[BindingType]] = [("q", "quit", "Quit")]

    def __init__(self, session: Session, opening: BrowseView) -> None:
        super().__init__()
        self._session = session
        self._opening = opening

    async def on_mount(self) -> None:
        await self.push_screen(BrowseScreen(self._session, self._opening))
