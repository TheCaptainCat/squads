"""`sq role …` — manage agent roles (list/show/activate)."""

import typer
from rich.panel import Panel
from rich.table import Table

from squads.cli.common import console, get_service, handle_errors
from squads.models import ItemType
from squads.roles.catalog import PREDEFINED, role_by_slug

role_app = typer.Typer(no_args_is_help=True, help="Manage agent roles.")


@role_app.command("list")
@handle_errors
def list_roles(
    available: bool = typer.Option(
        False, "--available", help="Show the bundled catalog, not active roles."
    ),
):
    """List active roles (or the bundled catalog with --available)."""
    table = Table(box=None, pad_edge=False)
    if available:
        for col in ("Slug", "Name", "Title", "Default"):
            table.add_column(col)
        for r in PREDEFINED:
            table.add_row(r.slug, r.full_name, r.title, "✓" if r.is_default else "")
        console.print(table)
        return
    svc = get_service()
    roles = svc.list(type=ItemType.ROLE)
    if not roles:
        console.print("[dim]no active roles (try `sq role list --available`)[/dim]")
        return
    for col in ("ID", "Slug", "Name", "Status"):
        table.add_column(col)
    for it in roles:
        table.add_row(
            it.id,
            it.extra.get("slug", it.slug),
            it.extra.get("full_name", it.title),
            it.status.value,
        )
    console.print(table)


@role_app.command("show")
@handle_errors
def show_role(slug: str = typer.Argument(...)):
    """Show a bundled role's definition."""
    r = role_by_slug(slug)
    rows = [
        f"[bold]{r.full_name}[/bold] (`{r.slug}`)",
        f"[bold]title:[/bold] {r.title}",
        f"[bold]model:[/bold] {r.model or 'inherit'}",
        f"[bold]mission:[/bold] {r.mission}",
        "[bold]responsibilities:[/bold]",
        *(f"  - {x}" for x in r.responsibilities),
    ]
    console.print(Panel("\n".join(rows), expand=False))


@role_app.command("activate")
@handle_errors
def activate_role(slug: str = typer.Argument(...)):
    """Activate a bundled role: create its tracked item and Claude pointer."""
    svc = get_service()
    item = svc.activate_role(slug)
    svc.refresh_managed()
    console.print(f"activated [bold]{item.extra.get('full_name', item.title)}[/bold] ({item.id})")


@role_app.command("regen")
@handle_errors
def regen_role(item_id: str = typer.Argument(...)):
    """Regenerate a role's Claude pointer from its item."""
    get_service().regen(item_id)
    console.print(f"regenerated pointer for {item_id}")


@role_app.command("rm")
@handle_errors
def rm_role(
    item_id: str = typer.Argument(...),
    purge: bool = typer.Option(False, "--purge", help="Also delete the markdown file."),
):
    """Remove a role (and its pointer; --purge also deletes the markdown)."""
    svc = get_service()
    svc.remove_item(item_id, purge=purge)
    svc.refresh_managed()
    console.print(f"removed {item_id}" + (" (purged)" if purge else ""))
