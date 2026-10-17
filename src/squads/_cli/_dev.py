"""`sq dev` — stack-specific developer roles, created on demand."""

import typer
from rich.table import Table

import squads._cli._common as common
from squads import _pronouns
from squads._cli._common import console, get_service
from squads._interactions._role_guidance import developer_roles
from squads._models import _attributes as attrs
from squads._roles._loader import load_role_catalog
from squads._roles._resolver import resolve_pronouns, resolve_role_tolerantly
from squads._workflow import ROSTER_ROLE

dev_app = typer.Typer(no_args_is_help=True, help="Manage stack-specific developer roles.")


@dev_app.command("add")
@common.command
async def dev_add(
    tech: str = typer.Option(..., "--tech", help="Technology, e.g. dotnet, python, react."),
    name: str | None = typer.Option(
        None, "--name", help="Full name (auto from a pool if omitted)."
    ),
    model: str | None = typer.Option(None, "--model", help="sonnet | opus | haiku."),
    slug: str | None = typer.Option(
        None, "--slug", help="Slug to store the developer under (default: <tech>-dev)."
    ),
    pronouns: str | None = typer.Option(
        None, "--pronouns", help="Pronouns for this developer, e.g. they/them (one line, up to 40)."
    ),
):
    """Bootstrap a developer for a technology (e.g. `sq dev add --tech dotnet`)."""
    svc = get_service()
    item = await svc.add_dev(tech, name=name, model=model, slug=slug, pronouns=pronouns)
    name = common.named_markup(
        svc, item.title, resolve_pronouns(_pronouns.pronouns(item), svc.paths.squad_dir)
    )
    console.print(f"added [bold]{name}[/bold] (`{item.slug}`) {item.id}")


@dev_app.command("list")
@common.command
async def dev_list():
    """List the live developer roles: those holding a capability the ``[dev]`` table declares."""
    svc = get_service()
    live = svc.spec.live_statuses(ROSTER_ROLE)
    items = [it for it in await svc.list_items(item_type=ROSTER_ROLE) if it.status in live]
    roles = {it.slug: resolve_role_tolerantly(it, svc.paths.squad_dir) for it in items}
    developers = {
        r.slug for r in developer_roles(roles.values(), load_role_catalog(svc.paths.squad_dir))
    }
    devs = [it for it in items if it.slug in developers]
    if not devs:
        console.print("[dim]no developers (try `sq dev add --tech <t>`)[/dim]", soft_wrap=True)
        return
    table = Table(box=None, pad_edge=False)
    for col in ("ID", "Slug", "Name", "Tech"):
        table.add_column(col)
    for it in devs:
        table.add_row(
            it.id,
            it.slug,
            _pronouns.named(
                it.title,
                roles[it.slug].pronouns,
                enabled=svc.paths.config.display.pronouns,
            ),
            attrs.tech(it) or "",
        )
    console.print(table)
