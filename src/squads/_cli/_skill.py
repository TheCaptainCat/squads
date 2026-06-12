"""`sq skill …` — manage agent skills (add/show/regen/rm).

Grammar:
  sq skill add <name> [options]      — create a skill item + pointer
  sq skill <slug|id|n> show          — show a skill's metadata panel
  sq skill <slug|id|n> regen         — regenerate the Claude pointer
  sq skill <slug|id|n> rm [--purge]  — remove the skill item

Address resolution order (exact match, no fuzzy):
  full-ID shape (SKIL-000001) → bare number → exact slug
"""
# Commands registered via Typer decorators (side effects) read as unused to static analysis.
# pyright: reportUnusedFunction=false

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
    resolve_item_id_any,
)
from squads._models._enums import ItemType
from squads._models._extras import ExtraKey as X

skill_app = typer.Typer(
    no_args_is_help=True,
    help="Manage agent skills.",
    epilog=(
        "Address a skill:  sq skill <slug|id|n> show|regen|rm\n"
        "Examples:  sq skill squads show   sq skill 2 regen   sq skill SKILL-000002 rm\n"
        "Note: a slug matching a group verb (add) is unaddressable by slug; "
        "use the full ID or bare number instead."
    ),
    cls=AddressDispatchGroup,
)

# --------------------------------------------------------------------------- add


@skill_app.command("add")
@handle_errors
def skill_add(
    name: str = typer.Argument(...),
    desc: str = typer.Option("", "--desc"),
    when_to_use: str = typer.Option("", "--when-to-use"),
    allowed_tools: str = typer.Option("", "--allowed-tools"),
    parent: str | None = typer.Option(None, "--parent"),
) -> None:
    """Create a skill item and its Claude pointer."""
    svc = get_service()
    resolved_parent = resolve_item_id_any(parent, svc) if parent else None
    item = svc.add_skill(
        name,
        description=desc,
        when_to_use=when_to_use,
        allowed_tools=allowed_tools,
        parent=resolved_parent,
    )
    console.print(f"created skill [bold]{item.id}[/bold] → {item.path}")


# ---------------------------------------------------------------- addressed subgroup (_addr)

_addr = typer.Typer(no_args_is_help=True, help="Operate on a skill by slug, ID, or number.")


@_addr.callback()
@handle_errors
def _resolve_addr(ctx: typer.Context, addr: str = typer.Argument(..., metavar="ADDR")) -> None:
    svc = get_service()
    ctx.ensure_object(dict)
    ctx.obj = {"id": resolve_agent_addr(addr, ItemType.SKILL, svc)}


@_addr.command("show")
@handle_errors
def skill_show(
    ctx: typer.Context,
    raw: bool = typer.Option(False, "--raw", help="Print plain body text (no markdown rendering)."),
) -> None:
    """Show a skill's metadata panel and body."""
    item_id: str = ctx.obj["id"]
    svc = get_service()
    it = svc.get(item_id)
    rows = [
        f"[bold]{it.id}[/bold] {e(it.title)}",
        f"[bold]slug:[/bold] {it.extra.get(X.SLUG, it.slug)}",
        f"[bold]status:[/bold] {it.status.value}",
        f"[bold]file:[/bold] {it.path}",
    ]
    if it.extra.get(X.WHEN_TO_USE):
        rows.append(f"[bold]when to use:[/bold] {e(it.extra[X.WHEN_TO_USE])}")
    console.print(Panel("\n".join(rows), expand=False))
    body = svc.read_body(it.id)
    render_body_text(
        body,
        raw=raw,
        empty_hint="(empty — run `sq sync` to regenerate the skill definition)",
    )


@_addr.command("regen")
@handle_errors
def skill_regen(ctx: typer.Context) -> None:
    """Regenerate the Claude pointer from the item."""
    item_id: str = ctx.obj["id"]
    svc = get_service()
    svc.regen(item_id)
    console.print(f"regenerated pointer for {item_id}")


@_addr.command("rm")
@handle_errors
def skill_rm(
    ctx: typer.Context,
    purge: bool = typer.Option(False, "--purge", help="Also delete the markdown file."),
) -> None:
    """Remove a skill (and its pointer; --purge also deletes the markdown)."""
    item_id: str = ctx.obj["id"]
    svc = get_service()
    svc.remove_item(item_id, purge=purge)
    console.print(f"removed {item_id}" + (" (purged)" if purge else ""))


skill_app.add_typer(_addr, name="_addr", hidden=True)
