"""`sq dev` — stack-specific developer roles, created on demand."""

import typer

import squads._cli._common as common
import squads._cli._role as role_cli
from squads._api import _ops as ops
from squads._cli import _calls as calls
from squads._cli._common import console
from squads._cli._roster import json_option
from squads._roles._models import DEV_TEMPLATE_NAME

dev_app = typer.Typer(no_args_is_help=True, help="Manage stack-specific developer roles.")


@dev_app.command("add")
@common.handle_errors
def dev_add(
    tech: str | None = common.tech_option(),
    name: str | None = typer.Option(
        None, "--name", help="Full name; without it, one is picked from the template's pool."
    ),
    model: str | None = common.model_option(),
    slug: str | None = typer.Option(
        None, "--slug", help="Slug to file the developer under instead of `<tech>-dev`."
    ),
    pronouns: str | None = common.pronouns_option(),
    as_: str | None = common.edit_as_option(),
    json_out: bool = json_option("Print one JSON object: the developer role added."),
):
    """Add a developer role for one technology, such as `--tech dotnet`.

    Exactly `sq role activate [<slug>] --from dev --tech <t>`.
    """
    from squads._api._dto._roles import RoleActivateRequest

    request = RoleActivateRequest(
        slug=slug,
        name=name,
        model=model,
        pronouns=pronouns,
        from_template=DEV_TEMPLATE_NAME,
        tech=tech,
    )
    role_cli.activate(request, as_, json_out=json_out)


@dev_app.command("list")
@common.handle_errors
def dev_list(
    json_out: bool = json_option(
        "Print one JSON object: the live developers, the table's columns and whether the "
        "developer template is there to add one."
    ),
):
    """List the live developer roles."""
    from squads._api._dto._roles import DeveloperListRequest
    from squads._cli._render._roster import render_developer_list

    response = calls.call(ops.DEVELOPERS_LIST, DeveloperListRequest())
    if json_out:
        calls.print_json(ops.DEVELOPERS_LIST, response)
        return
    calls.print_warnings(response)
    render_developer_list(response.data, console)
