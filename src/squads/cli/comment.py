"""`sq comment`, `sq story`, `sq subtask` — collaboration on item files."""

import json

import typer
from rich.table import Table

from squads.cli import app
from squads.cli.common import console, e, get_service, handle_errors
from squads.service import BlockResult

story_app = typer.Typer(no_args_is_help=True, help="Manage a feature's user stories.")
subtask_app = typer.Typer(no_args_is_help=True, help="Manage a task's subtasks.")


@app.command()
@handle_errors
def comment(
    item_id: str = typer.Argument(...),
    message: list[str] = typer.Option(..., "-m", "--message", help="A talking point (repeatable)."),
    as_: str = typer.Option("operator", "--as", help="Author: a role slug or 'operator'."),
    story: str | None = typer.Option(None, "--story", help="Target a user story (e.g. US1)."),
    subtask: str | None = typer.Option(None, "--subtask", help="Target a subtask (e.g. ST1)."),
):
    """Append a timestamped comment to an item's discussion."""
    svc = get_service()
    svc.comment(item_id, list(message), as_slug=as_, story=story, subtask=subtask)
    where = f" ({story or subtask})" if (story or subtask) else ""
    console.print(f"commented on {item_id}{where} as [bold]{svc.author(as_)}[/bold]")


def _print_block(parent_id: str, res: BlockResult, json_out: bool) -> None:
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


@story_app.command("add")
@handle_errors
def story_add(
    feature_id: str = typer.Argument(...),
    title: str = typer.Argument("", help="Optional short label; write the full story in the body."),
    json_out: bool = typer.Option(False, "--json"),
):
    """Scaffold a user story (free-form body + its own discussion) on a feature."""
    svc = get_service()
    _print_block(feature_id, svc.add_story(feature_id, title), json_out)


@story_app.command("list")
@handle_errors
def story_list(feature_id: str = typer.Argument(...)):
    """List a feature's user stories."""
    svc = get_service()
    stories = svc.list_stories(feature_id)
    if not stories:
        console.print("[dim]no user stories[/dim]")
        return
    table = Table(box=None, pad_edge=False)
    table.add_column("ID")
    table.add_column("Story")
    for sid, text in stories:
        table.add_row(sid, e(text))
    console.print(table)


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
    _print_block(task_id, svc.add_subtask(task_id, title, story=story), json_out)


@subtask_app.command("list")
@handle_errors
def subtask_list(task_id: str = typer.Argument(...)):
    """List a task's subtasks (with their checkbox and user-story map)."""
    svc = get_service()
    subs = svc.list_subtasks(task_id)
    if not subs:
        console.print("[dim]no subtasks[/dim]")
        return
    table = Table(box=None, pad_edge=False)
    table.add_column("ID")
    table.add_column("Subtask")
    for sid, text in subs:
        table.add_row(sid, e(text))
    console.print(table)


@subtask_app.command("done")
@handle_errors
def subtask_done(
    task_id: str = typer.Argument(...),
    local_id: str = typer.Argument(..., metavar="STn"),
    undo: bool = typer.Option(False, "--undo", help="Re-open the subtask."),
):
    """Mark a subtask done (or re-open it with --undo)."""
    svc = get_service()
    svc.set_subtask_done(task_id, local_id, done=not undo)
    console.print(f"{task_id} {local_id} → {'open' if undo else 'done'}")
