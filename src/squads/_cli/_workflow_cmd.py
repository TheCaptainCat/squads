"""`sq workflow` — workflow cheatsheet + spec validation surface.

Sub-commands:
- ``sq workflow`` / ``sq workflow show``  — print the team cheatsheet.
- ``sq workflow lint``                   — verbose collect-all-errors spec validation.
- one catalog command per declared ``WorkflowSpec`` vocabulary map (``types``,
  ``subentity-kinds``, ``collections``, ``statuses``, ``roles``, ``lifecycles``,
  ``ref-kinds``), each a human Rich table by default and a bare JSON array under ``--json``:
  one row per declared entry in a documented order, every key present on every row, and
  cross-references carried by name so a client joins catalogs instead of receiving copies.

``lint`` runs the checks ``compose_service`` runs fail-closed (pure-spec validation plus the
live-index cross-check) but prints every error and warning with its config key and a fix hint.
Exit 0 on a clean spec, 1 when any error is present. Its operation reads the override file
itself: a spec that makes ``compose_service`` hard-stop is exactly what an author runs it to
diagnose.

Each command makes one call; the catalogs and the cheatsheet also answer outside a squad, from
the bundled spec.
"""

from collections.abc import Callable

import typer
from pydantic import BaseModel
from rich.console import Console

import squads._cli._common as common
from squads._api import _ops as ops
from squads._api._api import Operation
from squads._api._dto._workflow import (
    CatalogRequest,
    CheatsheetRequest,
    LintRequest,
    ViewResolveRequest,
)
from squads._cli import _calls as calls
from squads._cli._common import console, e, handle_errors
from squads._cli._render import _workflow as render
from squads._errors import SquadsError

workflow_app = typer.Typer(
    no_args_is_help=False,
    invoke_without_command=True,
    help="Show the team workflow and the active spec's vocabulary.",
)


# ─── show (default — bare `sq workflow`) ───────────────────────────────────────


def _print_cheatsheet(*, raw: bool, json_out: bool = False) -> None:
    """Render the cheatsheet — Rich markdown by default, its markdown text verbatim with
    ``--raw`` (no box-drawing or ANSI), as ``sq show --raw`` and ``sq docs`` do."""
    response = calls.call(ops.WORKFLOW_SHOW, CheatsheetRequest())
    if json_out:
        calls.print_json(ops.WORKFLOW_SHOW, response)
        return
    calls.print_warnings(response)
    render.render_cheatsheet(response.data, console, raw=raw)


@workflow_app.callback()
@handle_errors
def workflow_default(
    ctx: typer.Context,
    raw: bool = common.raw_option(),
) -> None:
    """Print the team workflow cheatsheet when no sub-command is given."""
    if ctx.invoked_subcommand is None:
        _print_cheatsheet(raw=raw)


@workflow_app.command("show")
@handle_errors
def workflow_show(
    raw: bool = common.raw_option(),
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: the cheatsheet as markdown."
    ),
) -> None:
    """Print the team workflow cheatsheet: who writes what, how items link."""
    _print_cheatsheet(raw=raw, json_out=json_out)


# ─── catalogs ─────────────────────────────────────────────────────────────────


def _catalog[Res: BaseModel](
    op: Operation[CatalogRequest, Res], json_out: bool, renderer: Callable[[Res, Console], None]
) -> None:
    """Print one catalog: its table, or its rows as a JSON array."""
    response = calls.call(op, CatalogRequest())
    if json_out:
        calls.print_json(op, response)
        return
    calls.print_warnings(response)
    renderer(response.data, console)


@workflow_app.command("types")
@handle_errors
def workflow_types(
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per declared type."
    ),
) -> None:
    """List every declared type in the active workflow spec.

    Fields: sq docs stability
    """
    _catalog(ops.WORKFLOW_TYPES, json_out, render.render_types)


@workflow_app.command("subentity-kinds")
@handle_errors
def workflow_subentity_kinds(
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per sub-entity kind."
    ),
) -> None:
    """List every declared sub-entity kind in the active workflow spec.

    Fields: sq docs stability
    """
    _catalog(ops.WORKFLOW_SUBENTITY_KINDS, json_out, render.render_subentity_kinds)


@workflow_app.command("lifecycles")
@handle_errors
def workflow_lifecycles(
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per lifecycle."
    ),
) -> None:
    """List every declared lifecycle in the active workflow spec.

    Fields: sq docs stability
    """
    _catalog(ops.WORKFLOW_LIFECYCLES, json_out, render.render_lifecycles)


@workflow_app.command("collections")
@handle_errors
def workflow_collections(
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per badge collection."
    ),
) -> None:
    """List every declared badge collection in the active workflow spec.

    Fields: sq docs stability
    """
    _catalog(ops.WORKFLOW_COLLECTIONS, json_out, render.render_collections)


@workflow_app.command("statuses")
@handle_errors
def workflow_statuses(
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per status."
    ),
) -> None:
    """List every declared status in the active workflow spec.

    Fields: sq docs stability
    """
    _catalog(ops.WORKFLOW_STATUSES, json_out, render.render_statuses)


@workflow_app.command("roles")
@handle_errors
def workflow_roles(
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per status role."
    ),
) -> None:
    """List every status role in the active workflow spec.

    A status role says whether its statuses are settled, hidden or live.
    Fields: sq docs stability
    """
    _catalog(ops.WORKFLOW_ROLES, json_out, render.render_roles)


@workflow_app.command("ref-kinds")
@handle_errors
def workflow_ref_kinds(
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per ref kind."
    ),
) -> None:
    """List every declared ref kind in the active workflow spec.

    Fields: sq docs stability
    """
    _catalog(ops.WORKFLOW_REF_KINDS, json_out, render.render_ref_kinds)


@workflow_app.command("views")
@handle_errors
def workflow_views(
    json_out: bool = typer.Option(False, "--json", help="Print a JSON array, one object per view."),
) -> None:
    """List every declared derived view in the active workflow spec.

    Resolve one against an item with `sq workflow view <name> <id>`.
    Fields: sq docs stability
    """
    _catalog(ops.WORKFLOW_VIEWS, json_out, render.render_views)


# ─── view ─────────────────────────────────────────────────────────────────────


@workflow_app.command("view")
@handle_errors
def workflow_view(
    name: str = typer.Argument(..., help="Declared view name (see `sq workflow views`)."),
    item_id: str = typer.Argument(..., metavar="id", help="Item to resolve the view against."),
    json_out: bool = typer.Option(
        False, "--json", help="Print the resolved source as JSON, in its source's own shape."
    ),
) -> None:
    """Resolve one declared view against one item.

    Without `--json` the result renders through the view's template. `--json`
    prints the resolved source in the shape of the command it comes from, such as
    `sq tree --json` for a ref view.
    Fields: sq docs stability
    """
    request = ViewResolveRequest(name=name, item=item_id, render=not json_out)
    response = calls.call(ops.WORKFLOW_VIEW, request)
    if json_out:
        calls.print_json(ops.WORKFLOW_VIEW, response)
        return
    calls.print_warnings(response)
    render.render_view(response.data, console)


# ─── lint ─────────────────────────────────────────────────────────────────────


@workflow_app.command("lint")
@handle_errors
def workflow_lint(
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: the errors and warnings found."
    ),
) -> None:
    """Check the workflow override and list every error with a fix hint.

    It reads the override file directly, so it still runs when a broken spec stops
    other commands.

    Exit codes: 1 the spec has at least one error. See sq docs faq.
    """
    try:
        response = calls.call(ops.WORKFLOW_LINT, LintRequest())
    except SquadsError as exc:
        if json_out:
            raise
        common.print_notices(exc.warnings)
        console.print(f"[red]error[/red]: {e(common.error_text(exc))}", soft_wrap=True)
        raise typer.Exit(1) from exc
    if json_out:
        calls.print_json(ops.WORKFLOW_LINT, response)
    else:
        calls.print_warnings(response)
        render.render_lint(response.data, console)
    if response.data.errors:
        raise typer.Exit(1)
