"""`sq operator …` — register the humans (operators) who work on the project.

Grammar:
  sq operator add <name> [--slug SLUG]  — register a human operator
  sq operator <slug|id|n> show           — show an operator's metadata panel
  sq operator <slug|id|n> status <S>     — transition the operator's status
  sq operator <slug|id|n> remove --purge — delete an operator (or set status Archived)

Address resolution order (exact match, no fuzzy):
  full-ID shape (OPER-000001) → bare number → exact slug (op-<first>)
"""
# Commands registered via Typer decorators (side effects) read as unused to static analysis.
# pyright: reportUnusedFunction=false

import json

import typer
from rich.panel import Panel
from rich.table import Table

import squads._cli._common as common
from squads import _pronouns
from squads._cli._common import (
    AddressDispatchGroup,
    console,
    e,
    get_service,
    print_json_clean,
    register_body_verb,
    register_comment_verbs,
    register_remove_verb,
    register_status_verb,
    render_body_text,
    resolve_agent_addr,
)


class _OperatorDispatchGroup(AddressDispatchGroup):
    """Routes an address token to the hidden addressed subgroup."""


operator_app = typer.Typer(
    no_args_is_help=True,
    help="Manage human operators.",
    epilog=common.address_epilog(
        "operator",
        "operator",
        (
            "sq operator op-alice show",
            "sq operator 2 remove --purge",
            "sq operator op-alice status Archived",
        ),
        "add, list",
    ),
    cls=_OperatorDispatchGroup,
)

# --------------------------------------------------------------------------- add


@operator_app.command("add")
@common.command
async def operator_add(
    name: str = typer.Argument(..., help='The person\'s display name, such as "Alice Tester".'),
    slug: str | None = typer.Option(
        None, "--slug", help="Slug to use instead of `op-<first name>`."
    ),
    pronouns: str | None = common.pronouns_option(),
) -> None:
    """Register a person who can be assigned work and write items and comments."""
    svc = get_service()
    item = await svc.add_operator(name, slug=slug, pronouns=pronouns)
    name = common.named_markup(svc, item.title, _pronouns.pronouns(item))
    console.print(f"registered [bold]{name}[/bold] (`{item.slug}`) {item.id}")


# --------------------------------------------------------------------------- list


@operator_app.command("list")
@common.command
async def operator_list(
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per operator."
    ),
) -> None:
    """List the registered human operators."""
    svc = get_service()
    operators = await svc.list_operators()
    if json_out:
        print_json_clean(
            json.dumps(
                [
                    {
                        "id": op.id,
                        "slug": op.slug,
                        "full_name": op.title,
                        "pronouns": _pronouns.pronouns(op),
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
            e(op.slug),
            _pronouns.named(
                op.title, _pronouns.pronouns(op), enabled=svc.paths.config.display.pronouns
            ),
            op.id,
            e(op.status),
        )
    console.print(table)


# ---------------------------------------------------------------- addressed subgroup (_addr)

_addr = typer.Typer(
    no_args_is_help=True,
    cls=common.AddressedGroup,
    help="Operate on an operator by slug, ID, or number.",
)


@_addr.callback()
@common.command
async def _resolve_addr(
    ctx: typer.Context,
    addr: str = typer.Argument(
        ..., metavar=common.ADDRESS_METAVAR, help="Operator slug, ID or number."
    ),
) -> None:
    svc = get_service()
    ctx.obj = await common.address_obj(ctx, lambda: resolve_agent_addr(addr, "operator", svc))


@_addr.command("show")
@common.command
async def operator_show(
    ctx: typer.Context,
    raw: bool = common.raw_option(),
    json_out: bool = typer.Option(False, "--json", help="Print one JSON object: the operator."),
    comments: bool = typer.Option(
        False, "--comments", help="Append the discussion as comments (text output)."
    ),
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
                    "slug": it.slug,
                    "full_name": it.title,
                    "pronouns": _pronouns.pronouns(it),
                    "status": it.status,
                    "path": it.path,
                }
            )
        )
        return
    await common.warn_duplicate_id(svc, it)
    rows = [
        common.named_markup(svc, it.title, _pronouns.pronouns(it), style="bold"),
        f"[bold]slug:[/bold] {e(it.slug)}",
        f"[bold]id:[/bold] {it.id}",
        f"[bold]status:[/bold] {it.status}",
        f"[bold]file:[/bold] {it.path}",
    ]
    console.print(Panel("\n".join(rows), expand=False))
    body = await svc.read_body(it.id)
    render_body_text(
        body,
        raw=raw,
        empty_hint=f'(empty — write their profile with `sq operator {it.slug} body -m "…"`)',
    )
    if comments:
        common.print_comments(await svc.comments(it.id))


@_addr.command("update")
@common.command
async def operator_update(
    ctx: typer.Context,
    title: str | None = typer.Option(None, "--title", help="The operator's display name."),
    pronouns: str | None = typer.Option(
        None, "--pronouns", help="The operator's pronouns; a blank value clears them."
    ),
) -> None:
    """Rename an operator or set their pronouns; the slug never changes."""
    common.require_update_fields(title=title, pronouns=pronouns)
    item_id: str = ctx.obj["id"]
    svc = get_service()
    await svc.update(item_id, title=title, pronouns=pronouns)
    await svc.refresh_managed()
    console.print(f"updated {item_id}")


register_body_verb(_addr, lambda ctx: ctx.obj["id"])
register_remove_verb(_addr, lambda ctx: ctx.obj["id"], refresh_managed=True)
register_comment_verbs(_addr, lambda ctx: ctx.obj["id"])
register_status_verb(_addr, lambda ctx: ctx.obj["id"])

operator_app.add_typer(_addr, name="_addr", hidden=True)

operator_app.info.epilog = (operator_app.info.epilog or "").replace(
    "{verbs}", common.addr_verbs(_addr, ", ")
)
