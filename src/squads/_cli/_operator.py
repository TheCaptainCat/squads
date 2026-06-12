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

from squads._cli._common import (
    AddressDispatchGroup,
    console,
    e,
    get_service,
    handle_errors,
    render_body_text,
    resolve_agent_addr,
)
from squads._models._enums import ItemType
from squads._models._extras import ExtraKey as X


class _OperatorDispatchGroup(AddressDispatchGroup):
    _ADDR_VERBS: ClassVar[str] = "show|rm"


operator_app = typer.Typer(
    no_args_is_help=True,
    help="Manage human operators.",
    epilog=(
        "Address an operator:  sq operator <slug|id|n> show|rm\n"
        "Examples:  sq operator op-pierre show   sq operator 2 rm\n"
        "Note: a slug matching a group verb (add) is unaddressable by slug; "
        "use the full ID or bare number instead."
    ),
    cls=_OperatorDispatchGroup,
)

# --------------------------------------------------------------------------- add


@operator_app.command("add")
@handle_errors
def operator_add(
    name: str = typer.Argument(..., help='The human\'s display name, e.g. "Pierre Chat".'),
    slug: str | None = typer.Option(None, "--slug", help="Override the derived `op-<first>` slug."),
) -> None:
    """Register a human operator (assignable + can author items/comments)."""
    svc = get_service()
    item = svc.add_operator(name, slug=slug)
    console.print(
        f"registered [bold]{e(item.extra.get(X.FULL_NAME, item.title))}[/bold] "
        f"(`{item.extra.get(X.SLUG)}`) {item.id}"
    )


# ---------------------------------------------------------------- addressed subgroup (_addr)

_addr = typer.Typer(no_args_is_help=True, help="Operate on an operator by slug, ID, or number.")


@_addr.callback()
@handle_errors
def _resolve_addr(ctx: typer.Context, addr: str = typer.Argument(..., metavar="ADDR")) -> None:
    svc = get_service()
    ctx.ensure_object(dict)
    ctx.obj = {"id": resolve_agent_addr(addr, ItemType.OPERATOR, svc)}


@_addr.command("show")
@handle_errors
def operator_show(
    ctx: typer.Context,
    raw: bool = typer.Option(False, "--raw", help="Print plain body text (no markdown rendering)."),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Show an operator's metadata panel and body."""
    item_id: str = ctx.obj["id"]
    svc = get_service()
    it = svc.get(item_id)
    if json_out:
        console.print_json(
            json.dumps(
                {
                    "id": it.id,
                    "slug": it.extra.get(X.SLUG, it.slug),
                    "full_name": it.extra.get(X.FULL_NAME, it.title),
                    "status": it.status.value,
                    "path": it.path,
                }
            )
        )
        return
    rows = [
        f"[bold]{e(it.extra.get(X.FULL_NAME, it.title))}[/bold]",
        f"[bold]slug:[/bold] {e(it.extra.get(X.SLUG, it.slug))}",
        f"[bold]id:[/bold] {it.id}",
        f"[bold]status:[/bold] {it.status.value}",
        f"[bold]file:[/bold] {it.path}",
    ]
    console.print(Panel("\n".join(rows), expand=False))
    body = svc.read_body(it.id)
    render_body_text(
        body,
        raw=raw,
        empty_hint="(empty — run `sq sync` to regenerate the operator definition)",
    )


@_addr.command("rm")
@handle_errors
def operator_rm(
    ctx: typer.Context,
    purge: bool = typer.Option(False, "--purge", help="Also delete the markdown file."),
) -> None:
    """Remove an operator (--purge also deletes the markdown)."""
    item_id: str = ctx.obj["id"]
    svc = get_service()
    svc.remove_item(item_id, purge=purge)
    svc.refresh_managed()
    console.print(f"removed {item_id}" + (" (purged)" if purge else ""))


operator_app.add_typer(_addr, name="_addr", hidden=True)
