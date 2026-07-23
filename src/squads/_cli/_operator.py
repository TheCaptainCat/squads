"""`sq operator …` — register the humans (operators) who work on the project.

Grammar:
  sq operator add <name> [--slug SLUG]  — register a human operator
  sq operator <slug|id|n> show           — show an operator's metadata panel
  sq operator <slug|id|n> rm [--purge]   — remove an operator

Address resolution order (exact match, no fuzzy):
  full-ID shape (OPER-000001) → bare number → exact slug (op-<first>)
"""
# Commands registered via Typer decorators (side effects) read as unused to static analysis.
# pyright: reportUnusedFunction=false

import json
from typing import ClassVar

import typer
from rich.panel import Panel
from rich.table import Table

import squads._cli._common as common
from squads._cli._common import (
    AddressDispatchGroup,
    console,
    e,
    get_service,
    print_json_clean,
    render_body_text,
    resolve_agent_addr,
)
from squads._models._extras import ExtraKey as X


class _OperatorDispatchGroup(AddressDispatchGroup):
    _ADDR_VERBS: ClassVar[str] = "show|rm"


operator_app = typer.Typer(
    no_args_is_help=True,
    help="Manage human operators.",
    epilog=(
        "Address an operator:  sq operator <slug|id|n> show|rm\n"
        "Examples:  sq operator op-pierre show   sq operator 2 rm\n"
        "Note: a slug matching a group verb (add, list) is unaddressable by slug; "
        "use the full ID or bare number instead."
    ),
    cls=_OperatorDispatchGroup,
)

# --------------------------------------------------------------------------- add


@operator_app.command("add")
@common.command
async def operator_add(
    name: str = typer.Argument(..., help='The human\'s display name, e.g. "Pierre Chat".'),
    slug: str | None = typer.Option(None, "--slug", help="Override the derived `op-<first>` slug."),
) -> None:
    """Register a human operator (assignable + can author items/comments)."""
    svc = get_service()
    item = await svc.add_operator(name, slug=slug)
    console.print(
        f"registered [bold]{e(item.extra.get(X.FULL_NAME, item.title))}[/bold] "
        f"(`{item.extra.get(X.SLUG)}`) {item.id}"
    )


# --------------------------------------------------------------------------- list


@operator_app.command("list")
@common.command
async def operator_list(json_out: bool = typer.Option(False, "--json")) -> None:
    """List the registered human operators."""
    svc = get_service()
    operators = await svc.list_operators()
    if json_out:
        print_json_clean(
            json.dumps(
                [
                    {
                        "id": op.id,
                        "slug": op.extra.get(X.SLUG, op.slug),
                        "full_name": op.extra.get(X.FULL_NAME, op.title),
                        "status": op.status,
                    }
                    for op in operators
                ]
            )
        )
        return
    table = Table(box=None, pad_edge=False)
    for col in ("Slug", "Name", "ID", "Status"):
        table.add_column(col)
    for op in operators:
        table.add_row(
            e(op.extra.get(X.SLUG, op.slug)),
            e(op.extra.get(X.FULL_NAME, op.title)),
            op.id,
            e(op.status),
        )
    console.print(table)


# ---------------------------------------------------------------- addressed subgroup (_addr)

_addr = typer.Typer(no_args_is_help=True, help="Operate on an operator by slug, ID, or number.")


@_addr.callback()
@common.command
async def _resolve_addr(
    ctx: typer.Context, addr: str = typer.Argument(..., metavar="ADDR")
) -> None:
    svc = get_service()
    ctx.ensure_object(dict)
    ctx.obj = {"id": await resolve_agent_addr(addr, "operator", svc)}


@_addr.command("show")
@common.command
async def operator_show(
    ctx: typer.Context,
    raw: bool = typer.Option(False, "--raw", help="Print plain body text (no markdown rendering)."),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Show an operator's metadata panel and body."""
    item_id: str = ctx.obj["id"]
    svc = get_service()
    it = await svc.get(item_id)
    if json_out:
        print_json_clean(
            json.dumps(
                {
                    "id": it.id,
                    "slug": it.extra.get(X.SLUG, it.slug),
                    "full_name": it.extra.get(X.FULL_NAME, it.title),
                    "status": it.status,
                    "path": it.path,
                }
            )
        )
        return
    rows = [
        f"[bold]{e(it.extra.get(X.FULL_NAME, it.title))}[/bold]",
        f"[bold]slug:[/bold] {e(it.extra.get(X.SLUG, it.slug))}",
        f"[bold]id:[/bold] {it.id}",
        f"[bold]status:[/bold] {it.status}",
        f"[bold]file:[/bold] {it.path}",
    ]
    console.print(Panel("\n".join(rows), expand=False))
    body = await svc.read_body(it.id)
    render_body_text(
        body,
        raw=raw,
        empty_hint="(empty — run `sq sync` to regenerate the operator definition)",
    )


@_addr.command("rm")
@common.command
async def operator_rm(
    ctx: typer.Context,
    purge: bool = typer.Option(False, "--purge", help="Also delete the markdown file."),
) -> None:
    """Remove an operator (--purge also deletes the markdown)."""
    item_id: str = ctx.obj["id"]
    svc = get_service()
    await svc.remove_item(item_id, purge=purge)
    await svc.refresh_managed()
    console.print(f"removed {item_id}" + (" (purged)" if purge else ""))


operator_app.add_typer(_addr, name="_addr", hidden=True)
