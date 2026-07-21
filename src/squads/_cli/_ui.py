"""`sq ui` — browse the squad in a full-screen terminal app (read-only)."""

from squads._cli import app
from squads._cli._common import get_service, handle_errors
from squads._errors import SquadsError


@app.command("ui")
@handle_errors
def ui() -> None:
    """Launch the sq ui terminal browser."""
    svc = get_service()
    try:
        from squads._tui._app import SquadsApp
    except ModuleNotFoundError as exc:
        raise SquadsError(
            "the sq ui terminal UI needs the optional 'tui' extra — "
            "install it with `pip install squads[tui]`"
        ) from exc
    SquadsApp(svc).run()
