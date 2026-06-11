"""`sq operator …` — register the humans (operators) who work on the project."""

import typer
from rich.table import Table

from squads._cli._common import console, e, get_service, handle_errors, resolve_item_id_typed
from squads._models._enums import ItemType
from squads._models._extras import ExtraKey as X

operator_app = typer.Typer(no_args_is_help=True, help="Manage human operators.")


@operator_app.command("add")
@handle_errors
def operator_add(
    name: str = typer.Argument(..., help='The human\'s display name, e.g. "Pierre Chat".'),
    slug: str | None = typer.Option(None, "--slug", help="Override the derived `op-<first>` slug."),
):
    """Register a human operator (assignable + can author items/comments)."""
    svc = get_service()
    item = svc.add_operator(name, slug=slug)
    console.print(
        f"registered [bold]{e(item.extra.get(X.FULL_NAME, item.title))}[/bold] "
        f"(`{item.extra.get(X.SLUG)}`) {item.id}"
    )


@operator_app.command("list")
@handle_errors
def operator_list():
    """List the registered operators."""
    svc = get_service()
    ops = svc.list_operators()
    if not ops:
        console.print('[dim]no operators (try `sq operator add "<name>"`)[/dim]')
        return
    table = Table(box=None, pad_edge=False)
    for col in ("ID", "Slug", "Name"):
        table.add_column(col)
    for it in ops:
        table.add_row(it.id, it.extra.get(X.SLUG, it.slug), e(it.extra.get(X.FULL_NAME, it.title)))
    console.print(table)


@operator_app.command("rm")
@handle_errors
def operator_rm(
    item_id: str = typer.Argument(...),
    purge: bool = typer.Option(False, "--purge", help="Also delete the markdown file."),
):
    """Remove an operator (--purge also deletes the markdown)."""
    svc = get_service()
    resolved = resolve_item_id_typed(item_id, ItemType.OPERATOR, svc)
    svc.remove_item(resolved, purge=purge)
    svc.refresh_managed()
    console.print(f"removed {resolved}" + (" (purged)" if purge else ""))
