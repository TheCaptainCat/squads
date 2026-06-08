"""`sq skill` — manage agent skills (real definition under the squad folder + .claude pointer)."""

import typer
from rich.panel import Panel
from rich.table import Table

from squads._cli._common import console, e, get_service, handle_errors
from squads._models._enums import ItemType
from squads._models._extras import ExtraKey as X

skill_app = typer.Typer(no_args_is_help=True, help="Manage agent skills.")


@skill_app.command("add")
@handle_errors
def skill_add(
    name: str = typer.Argument(...),
    desc: str = typer.Option("", "--desc"),
    when_to_use: str = typer.Option("", "--when-to-use"),
    allowed_tools: str = typer.Option("", "--allowed-tools"),
    parent: str | None = typer.Option(None, "--parent"),
):
    """Create a skill item and its Claude pointer."""
    svc = get_service()
    item = svc.add_skill(
        name, description=desc, when_to_use=when_to_use, allowed_tools=allowed_tools, parent=parent
    )
    console.print(f"created skill [bold]{item.id}[/bold] → {item.path}")


@skill_app.command("list")
@handle_errors
def skill_list():
    svc = get_service()
    skills = svc.list_items(item_type=ItemType.SKILL)
    if not skills:
        console.print("[dim]no skills[/dim]")
        return
    table = Table(box=None, pad_edge=False)
    for col in ("ID", "Slug", "Name", "Status"):
        table.add_column(col)
    for it in skills:
        table.add_row(it.id, it.extra.get(X.SLUG, it.slug), e(it.title), it.status.value)
    console.print(table)


@skill_app.command("show")
@handle_errors
def skill_show(item_id: str = typer.Argument(...)):
    svc = get_service()
    it = svc.get(item_id)
    rows = [
        f"[bold]{it.id}[/bold] {e(it.title)}",
        f"[bold]slug:[/bold] {it.extra.get(X.SLUG, it.slug)}",
        f"[bold]status:[/bold] {it.status.value}",
        f"[bold]file:[/bold] {it.path}",
    ]
    if it.extra.get(X.WHEN_TO_USE):
        rows.append(f"[bold]when to use:[/bold] {e(it.extra[X.WHEN_TO_USE])}")
    console.print(Panel("\n".join(rows), expand=False))


@skill_app.command("regen")
@handle_errors
def skill_regen(item_id: str = typer.Argument(...)):
    """Regenerate the Claude pointer from the item."""
    get_service().regen(item_id)
    console.print(f"regenerated pointer for {item_id}")


@skill_app.command("rm")
@handle_errors
def skill_rm(
    item_id: str = typer.Argument(...),
    purge: bool = typer.Option(False, "--purge", help="Also delete the markdown file."),
):
    """Remove a skill (and its pointer; --purge also deletes the markdown)."""
    get_service().remove_item(item_id, purge=purge)
    console.print(f"removed {item_id}" + (" (purged)" if purge else ""))
