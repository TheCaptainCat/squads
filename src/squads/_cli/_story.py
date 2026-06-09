"""`sq story` — a feature's user stories."""

import typer
from rich.table import Table

from squads._cli._common import (
    console,
    e,
    get_service,
    handle_errors,
    parse_status,
    print_block,
)

story_app = typer.Typer(no_args_is_help=True, help="Manage a feature's user stories.")


@story_app.command("add")
@handle_errors
def story_add(
    feature_id: str = typer.Argument(...),
    title: str = typer.Argument("", help="Optional short label; write the full story in the body."),
    json_out: bool = typer.Option(False, "--json"),
):
    """Scaffold a user story (free-form body + its own discussion) on a feature."""
    svc = get_service()
    print_block(feature_id, svc.add_story(feature_id, title), json_out)


@story_app.command("list")
@handle_errors
def story_list(feature_id: str = typer.Argument(...)):
    """List a feature's user stories and their status."""
    blocks = get_service().list_stories(feature_id)
    if not blocks:
        console.print("[dim]no user stories[/dim]")
        return
    table = Table(box=None, pad_edge=False)
    for col in ("ID", "Status", "Story"):
        table.add_column(col)
    for b in blocks:
        table.add_row(b.local_id, b.status, e(b.title))
    console.print(table)


@story_app.command("status")
@handle_errors
def story_status(
    feature_id: str = typer.Argument(...),
    local_id: str = typer.Argument(..., metavar="USn"),
    new_status: str = typer.Argument(..., metavar="STATUS"),
    force: bool = typer.Option(False, "--force"),
):
    """Transition a user story (Todo → InProgress → Done; + Blocked, Cancelled)."""
    svc = get_service()
    svc.set_story_status(feature_id, local_id, parse_status(new_status), force=force)
    console.print(f"{feature_id} {local_id} → [bold]{parse_status(new_status).value}[/bold]")
