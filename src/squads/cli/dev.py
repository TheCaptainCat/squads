"""`sq dev` — stack-specific developer roles, created on demand."""

import typer
from rich.table import Table

from squads.cli.common import console, e, get_service, handle_errors
from squads.models import ItemType

dev_app = typer.Typer(no_args_is_help=True, help="Manage stack-specific developer roles.")


@dev_app.command("add")
@handle_errors
def dev_add(
    tech: str = typer.Option(..., "--tech", help="Technology, e.g. dotnet, python, react."),
    name: str | None = typer.Option(
        None, "--name", help="Full name (auto from a pool if omitted)."
    ),
    model: str | None = typer.Option(None, "--model", help="sonnet | opus | haiku."),
):
    """Bootstrap a developer for a technology (e.g. `sq dev add --tech dotnet`)."""
    svc = get_service()
    item = svc.add_dev(tech, name=name, model=model)
    console.print(
        f"added [bold]{e(item.extra.get('full_name', item.title))}[/bold] "
        f"(`{item.extra.get('slug')}`) {item.id}"
    )


@dev_app.command("list")
@handle_errors
def dev_list():
    """List the activated developer roles."""
    svc = get_service()
    devs = [it for it in svc.list(type=ItemType.ROLE) if it.extra.get("is_dev")]
    if not devs:
        console.print("[dim]no developers (try `sq dev add --tech <t>`)[/dim]")
        return
    table = Table(box=None, pad_edge=False)
    for col in ("ID", "Slug", "Name", "Tech"):
        table.add_column(col)
    for it in devs:
        table.add_row(
            it.id,
            it.extra.get("slug", it.slug),
            e(it.extra.get("full_name", it.title)),
            it.extra.get("tech", ""),
        )
    console.print(table)
