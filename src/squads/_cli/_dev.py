"""`sq dev` — stack-specific developer roles, created on demand."""

import typer
from rich.table import Table

import squads._cli._common as common
from squads._cli._common import console, e, get_service
from squads._models._extras import ExtraKey as X
from squads._workflow import META_ROLE

dev_app = typer.Typer(no_args_is_help=True, help="Manage stack-specific developer roles.")


@dev_app.command("add")
@common.command
async def dev_add(
    tech: str = typer.Option(..., "--tech", help="Technology, e.g. dotnet, python, react."),
    name: str | None = typer.Option(
        None, "--name", help="Full name (auto from a pool if omitted)."
    ),
    model: str | None = typer.Option(None, "--model", help="sonnet | opus | haiku."),
):
    """Bootstrap a developer for a technology (e.g. `sq dev add --tech dotnet`)."""
    svc = get_service()
    item = await svc.add_dev(tech, name=name, model=model)
    console.print(
        f"added [bold]{e(item.extra.get(X.FULL_NAME, item.title))}[/bold] "
        f"(`{item.extra.get(X.SLUG)}`) {item.id}"
    )


@dev_app.command("list")
@common.command
async def dev_list():
    """List the activated developer roles."""
    svc = get_service()
    devs = [it for it in await svc.list_items(item_type=META_ROLE) if it.extra.get(X.IS_DEV)]
    if not devs:
        console.print("[dim]no developers (try `sq dev add --tech <t>`)[/dim]")
        return
    table = Table(box=None, pad_edge=False)
    for col in ("ID", "Slug", "Name", "Tech"):
        table.add_column(col)
    for it in devs:
        table.add_row(
            it.id,
            it.extra.get(X.SLUG, it.slug),
            e(it.extra.get(X.FULL_NAME, it.title)),
            it.extra.get(X.TECH, ""),
        )
    console.print(table)
