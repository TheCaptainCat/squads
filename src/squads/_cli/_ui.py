"""`sq ui` — browse the squad in a full-screen terminal app (read-only)."""

import asyncio

from squads._api._api import Api
from squads._cli import app
from squads._cli._calls import select_api
from squads._cli._common import handle_errors
from squads._context import get_context
from squads._errors import SquadsError


@app.command("ui")
@handle_errors
def ui() -> None:
    """Launch the sq ui terminal browser."""
    try:
        import textual  # noqa: F401  # pyright: ignore[reportUnusedImport]
    except ModuleNotFoundError as exc:
        raise SquadsError(
            "the sq ui terminal UI needs the optional 'tui' extra — "
            "install it with `pip install squads[tui]`"
        ) from exc
    from squads._tui._app import SquadsApp, open_session

    api = get_context().api or select_api()

    def selector() -> Api:
        return api

    session, opening = asyncio.run(open_session(selector))
    SquadsApp(session, opening).run()
