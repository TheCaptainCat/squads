"""The `sq ui` Textual application: a thin shell that pushes the browse screen."""

from typing import ClassVar

from textual.app import App
from textual.binding import BindingType

from squads._services._service import Service
from squads._tui._browse import BrowseScreen


class SquadsApp(App[None]):
    """The `sq ui` shell: holds the in-process `Service` handle, pushes `BrowseScreen`."""

    TITLE = "sq ui"
    BINDINGS: ClassVar[list[BindingType]] = [("q", "quit", "Quit")]

    def __init__(self, svc: Service) -> None:
        super().__init__()
        self._svc = svc

    async def on_mount(self) -> None:
        await self.push_screen(BrowseScreen(self._svc))
