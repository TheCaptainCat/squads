"""Shared CLI helpers: console, error handling, service resolution, value parsing."""

import functools
from collections.abc import Callable

import typer
from rich.console import Console
from rich.markup import escape

from squads.errors import SquadsError
from squads.models import ItemType, Status
from squads.service import Service, open_service

console = Console()
err_console = Console(stderr=True)


def e(value: object) -> str:
    """Escape a dynamic string so Rich does not interpret ``[...]`` as markup."""
    return escape(str(value))


# Set by the root callback from the global --dir option.
STATE: dict[str, str | None] = {"dir": None}


def get_service() -> Service:
    return open_service(STATE["dir"])


def handle_errors[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return fn(*args, **kwargs)
        except SquadsError as exc:
            err_console.print(f"[red]error:[/red] {exc}")
            raise typer.Exit(1) from exc

    return wrapper


def _vtuple(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for p in version.split("."):
        num = "".join(c for c in p if c.isdigit())
        parts.append(int(num) if num else 0)
    return tuple(parts)


def version_notice() -> None:
    """Print a non-fatal notice if the installed squads is newer than the managed files."""
    from squads import __version__
    from squads.paths import resolve

    try:
        sp = resolve(STATE["dir"])
    except SquadsError:
        return  # not initialized yet (e.g. before `sq init`)
    recorded = sp.config.squads_version
    if recorded and _vtuple(__version__) > _vtuple(recorded):
        err_console.print(
            f"[yellow]squads {__version__} detected (managed files at {recorded}). "
            f"Run `sq sync` to refresh them.[/yellow]"
        )


def parse_type(value: str) -> ItemType:
    try:
        return ItemType(value)
    except ValueError:
        choices = ", ".join(t.value for t in ItemType)
        raise SquadsError(f"unknown type {value!r} (one of: {choices})") from None


def parse_status(value: str) -> Status:
    # accept either the canonical value ("InProgress") or a loose form ("in_progress", "inprogress")
    norm = value.replace("_", "").replace("-", "").lower()
    for s in Status:
        if s.value.lower() == norm or s.value == value:
            return s
    choices = ", ".join(s.value for s in Status)
    raise SquadsError(f"unknown status {value!r} (one of: {choices})") from None
