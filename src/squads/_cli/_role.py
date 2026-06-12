"""`sq role …` — manage agent roles (list/show/activate)."""

import typer
from rich.panel import Panel
from rich.table import Table

from squads._cli._common import console, e, get_service, handle_errors, resolve_item_id_typed
from squads._errors import SquadsError
from squads._models._enums import ItemType
from squads._models._extras import ExtraKey as X
from squads._roles._catalog import PREDEFINED, role_by_slug

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
    roles = svc.list_items(item_type=ItemType.ROLE)
    if not roles:
        console.print("[dim]no active roles (try `sq role list --available`)[/dim]")
        return
    for col in ("ID", "Slug", "Name", "Status"):
        table.add_column(col)
    for it in roles:
        table.add_row(
            it.id,
            it.extra.get(X.SLUG, it.slug),
            it.extra.get(X.FULL_NAME, it.title),
            it.status.value,
        )
    console.print(table)


@role_app.command("show")
@handle_errors
def show_role(slug: str = typer.Argument(...)):
    """Show a role's complete definition: catalog card plus active item body."""
    r = role_by_slug(slug)
    rows = [
        f"[bold]{e(r.full_name)}[/bold] (`{e(r.slug)}`)",
        f"[bold]title:[/bold] {e(r.title)}",
        f"[bold]model:[/bold] {e(r.model or 'inherit')}",
        f"[bold]mission:[/bold] {e(r.mission)}",
        "[bold]responsibilities:[/bold]",
        *(f"  - {e(x)}" for x in r.responsibilities),
    ]
    console.print(Panel("\n".join(rows), expand=False))

    # Attempt to show the active item body (working agreements, skills, etc.).
    # FEAT-000026 (panes/--raw) has not landed; keep current Rich rendering style.
    # If the squad is not initialized, treat it the same as a bundled-only role.
    body: str | None = None
    try:
        svc = get_service()
        body = svc.role_body(slug)
    except SquadsError:
        body = None

    console.print()
    if body:
        console.print(e(body))
    else:
        # Bundled-only role (no tracked item) or squad not initialised.
        # Degrade gracefully with an activation hint.
        console.print(
            f"[dim](no active item for {e(slug)} — run `sq role activate {e(slug)}`"
            " then `sq sync` to populate the full definition)[/dim]"
        )


@role_app.command("activate")
@handle_errors
def activate_role(slug: str = typer.Argument(...)):
    """Activate a bundled role: create its tracked item and Claude pointer."""
    svc = get_service()
    item = svc.activate_role(slug)
    svc.refresh_managed()
    console.print(f"activated [bold]{item.extra.get(X.FULL_NAME, item.title)}[/bold] ({item.id})")


@role_app.command("regen")
@handle_errors
def regen_role(item_id: str = typer.Argument(...)):
    """Regenerate a role's Claude pointer from its item."""
    svc = get_service()
    resolved = resolve_item_id_typed(item_id, ItemType.ROLE, svc)
    svc.regen(resolved)
    console.print(f"regenerated pointer for {resolved}")


@role_app.command("rm")
@handle_errors
def rm_role(
    item_id: str = typer.Argument(...),
    purge: bool = typer.Option(False, "--purge", help="Also delete the markdown file."),
):
    """Remove a role (and its pointer; --purge also deletes the markdown)."""
    svc = get_service()
    resolved = resolve_item_id_typed(item_id, ItemType.ROLE, svc)
    svc.remove_item(resolved, purge=purge)
    svc.refresh_managed()
    console.print(f"removed {resolved}" + (" (purged)" if purge else ""))
