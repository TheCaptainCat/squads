"""`sq dev` — stack-specific developer roles, created on demand."""

import typer
from rich.table import Table

import squads._cli._common as common
import squads._cli._role as role_cli
from squads import _pronouns
from squads._cli._common import console, get_service
from squads._interactions._role_guidance import developer_roles
from squads._models import _attributes as attrs
from squads._roles._models import DEV_TEMPLATE_NAME
from squads._roles._resolver import resolve_role_tolerantly
from squads._workflow import ROSTER_ROLE

dev_app = typer.Typer(no_args_is_help=True, help="Manage stack-specific developer roles.")


@dev_app.command("add")
@common.command
async def dev_add(
    tech: str | None = common.tech_option(),
    name: str | None = typer.Option(
        None, "--name", help="Full name; without it, one is picked from the template's pool."
    ),
    model: str | None = common.model_option(),
    slug: str | None = typer.Option(
        None, "--slug", help="Slug to file the developer under instead of `<tech>-dev`."
    ),
    pronouns: str | None = common.pronouns_option(),
):
    """Add a developer role for one technology, such as `--tech dotnet`.

    Exactly `sq role activate [<slug>] --from dev --tech <t>`.
    """
    await role_cli.activate_with_template(
        slug, name=name, model=model, pronouns=pronouns, from_template=DEV_TEMPLATE_NAME, tech=tech
    )


@dev_app.command("list")
@common.command
async def dev_list():
    """List the live developer roles."""
    svc = get_service()
    live = svc.spec.live_statuses(ROSTER_ROLE)
    items = [it for it in await svc.list_items(item_type=ROSTER_ROLE) if it.status in live]
    roles = {
        it.slug: resolve_role_tolerantly(it, svc.paths.squad_dir, catalog=svc.catalog)
        for it in items
    }
    developers = {r.slug for r in developer_roles(roles.values(), svc.catalog())}
    devs = [it for it in items if it.slug in developers]
    if not devs:
        hint = (
            " (try `sq dev add --tech <t>`)" if DEV_TEMPLATE_NAME in svc.catalog().templates else ""
        )
        console.print(f"[dim]no developers{hint}[/dim]", soft_wrap=True)
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
