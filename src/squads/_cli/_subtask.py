"""`sq subtask` — a task's subtasks."""

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

subtask_app = typer.Typer(no_args_is_help=True, help="Manage a task's subtasks.")


@subtask_app.command("add")
@handle_errors
def subtask_add(
    task_id: str = typer.Argument(...),
    title: str = typer.Argument("", help="Optional checklist label; write detail in the body."),
    story: str | None = typer.Option(
        None,
        "--story",
        help="User story this subtask implements (e.g. US2; must exist in the parent feature).",
    ),
    json_out: bool = typer.Option(False, "--json"),
):
    """Scaffold a subtask (free-form body + its own discussion) on a task."""
    svc = get_service()
    print_block(task_id, svc.add_subtask(task_id, title, story=story), json_out)


@subtask_app.command("list")
@handle_errors
def subtask_list(task_id: str = typer.Argument(...)):
    """List a task's subtasks with their status and user-story map."""
    blocks = get_service().list_subtasks(task_id)
    if not blocks:
        console.print("[dim]no subtasks[/dim]")
        return
    table = Table(box=None, pad_edge=False)
    for col in ("ID", "Status", "Subtask", "Story"):
        table.add_column(col)
    for b in blocks:
        table.add_row(b.local_id, b.status, e(b.title), b.story or "")
    console.print(table)


@subtask_app.command("status")
@handle_errors
def subtask_status(
    task_id: str = typer.Argument(...),
    local_id: str = typer.Argument(..., metavar="STn"),
    new_status: str = typer.Argument(..., metavar="STATUS"),
    force: bool = typer.Option(False, "--force"),
):
    """Transition a subtask (Todo → InProgress → Done; + Blocked, Cancelled)."""
    svc = get_service()
    svc.set_subtask_status(task_id, local_id, parse_status(new_status), force=force)
    console.print(f"{task_id} {local_id} → [bold]{parse_status(new_status).value}[/bold]")


@subtask_app.command("done")
@handle_errors
def subtask_done(
    task_id: str = typer.Argument(...),
    local_id: str = typer.Argument(..., metavar="STn"),
    undo: bool = typer.Option(False, "--undo", help="Re-open the subtask (back to Todo)."),
):
    """Shortcut: mark a subtask Done (or re-open it with --undo)."""
    svc = get_service()
    svc.set_subtask_done(task_id, local_id, done=not undo)
    console.print(f"{task_id} {local_id} → {'Todo' if undo else 'Done'}")
