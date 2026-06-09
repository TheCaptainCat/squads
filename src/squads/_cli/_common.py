"""Shared CLI helpers: console, error handling, service resolution, value parsing."""

import functools
import json
import sys
from collections.abc import Callable

import typer
from rich.console import Console
from rich.markup import escape

from squads import __version__, _clock
from squads._errors import SquadsError
from squads._models._enums import ItemType, Severity, Status
from squads._models._schema import SCHEMA_VERSION
from squads._paths import resolve
from squads._services._results import BlockResult
from squads._services._service import Service, open_service

console = Console()
err_console = Console(stderr=True)

# The active squad folder from the global --dir option, set once by the root callback.
_active_dir: str | None = None


def set_active_dir(value: str | None) -> None:
    global _active_dir
    _active_dir = value


def apply_timestamp(at: str | None) -> None:
    """Honour the global ``--at`` option: forge `clock.now()` for this invocation (or clear it)."""
    if at is None:
        _clock.set_now(None)
        return
    try:
        _clock.set_now(_clock.parse_iso(at))
    except ValueError:
        err_console.print(
            f"[red]error:[/red] invalid --at timestamp {at!r} "
            "(use ISO 8601, e.g. 2024-01-15 or 2024-01-15T09:30:00Z)"
        )
        raise typer.Exit(2) from None


def e(value: object) -> str:
    """Escape a dynamic string so Rich does not interpret ``[...]`` as markup."""
    return escape(str(value))


def print_block(parent_id: str, res: BlockResult, json_out: bool) -> None:
    """Report a scaffolded story/subtask/finding block + where the agent should write its body."""
    if json_out:
        console.print_json(
            json.dumps(
                {
                    "local_id": res.local_id,
                    "file": str(res.path),
                    "region": res.body_tag,
                    "start_line": res.start_line,
                    "end_line": res.end_line,
                }
            )
        )
        return
    console.print(f"added [bold]{res.local_id}[/bold] to {parent_id}")
    console.print(
        f"  write in [cyan]{res.path}[/cyan] between "
        f"[dim]<!-- sq:{res.body_tag} -->[/dim] (line {res.start_line}) "
        f"and its [dim]:end[/dim] (line {res.end_line})"
    )
    console.print("  [dim]free-form paragraphs or bullets; leave the marker lines untouched.[/dim]")


def get_service() -> Service:
    return open_service(_active_dir)


def handle_errors[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return fn(*args, **kwargs)
        except SquadsError as exc:
            err_console.print(f"[red]error:[/red] {exc}")
            raise typer.Exit(1) from exc

    return wrapper


def version_tuple(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for p in version.split("."):
        num = "".join(c for c in p if c.isdigit())
        parts.append(int(num) if num else 0)
    return tuple(parts)


def version_notice() -> None:
    """Print a non-fatal notice if the installed squads is newer than the managed files."""
    try:
        sp = resolve(_active_dir)
    except SquadsError:
        return  # not initialized yet (e.g. before `sq init`)
    recorded = sp.config.squads_version
    if recorded and version_tuple(__version__) > version_tuple(recorded):
        err_console.print(
            f"[yellow]squads {__version__} detected (managed files at {recorded}). "
            f"Run `sq sync` to refresh them.[/yellow]"
        )


def require_current_schema(subcommand: str | None) -> None:
    """Hard-stop when the squad's on-disk schema mismatches this build — except for migrate/help.

    Behind → tell the user to run ``sq migrate``; ahead → tell them to upgrade the package.
    """
    if subcommand in (None, "migrate") or "--help" in sys.argv or "-h" in sys.argv:
        return
    try:
        sp = resolve(_active_dir)
    except SquadsError:
        return  # not initialized yet — nothing to gate
    disk = sp.config.schema_version
    if disk == SCHEMA_VERSION:
        return
    if disk < SCHEMA_VERSION:
        err_console.print(
            f"[red]error:[/red] this squad is at schema v{disk}; squads {__version__} "
            f"expects v{SCHEMA_VERSION}. Run [bold]sq migrate up[/bold] to upgrade it "
            "(see `sq migrate help`)."
        )
    else:
        err_console.print(
            f"[red]error:[/red] this squad is at schema v{disk}, newer than squads "
            f"{__version__} (v{SCHEMA_VERSION}). Upgrade the squads package."
        )
    raise typer.Exit(1)


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


def parse_severity(value: str) -> Severity:
    try:
        return Severity(value.strip().lower())
    except ValueError:
        choices = ", ".join(s.value for s in Severity)
        raise SquadsError(f"unknown severity {value!r} (one of: {choices})") from None
