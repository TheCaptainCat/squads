"""`sq skill …` — manage agent skills (add/show/regen/rm/refs).

Grammar:
  sq skill add <name> [options]      — create a skill item + pointer
  sq skill <slug|id|n> show          — show a skill's metadata panel
  sq skill <slug|id|n> refs          — show forward refs and backrefs
  sq skill <slug|id|n> ref add <id>  — add a forward reference
  sq skill <slug|id|n> ref rm <id>   — remove a forward reference
  sq skill <slug|id|n> regen         — regenerate the Claude pointer
  sq skill <slug|id|n> rm [--purge]  — remove the skill item

Address resolution order (exact match, no fuzzy):
  full-ID shape (SKILL-000001) → bare number → exact slug
"""
# Commands registered via Typer decorators (side effects) read as unused to static analysis.
# pyright: reportUnusedFunction=false

import json

import typer
from rich.panel import Panel

import squads._cli._common as common
from squads._cli._common import (
    AddressDispatchGroup,
    console,
    e,
    get_service,
    print_json_clean,
    render_body_text,
    resolve_agent_addr,
    resolve_item_id_any,
)
from squads._models._enums import ItemType
from squads._models._extras import ExtraKey as X
from squads._models._item import DEFAULT_KIND, split_ref

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
@common.command
async def skill_add(
    name: str = typer.Argument(...),
    desc: str = typer.Option("", "--desc"),
    when_to_use: str = typer.Option("", "--when-to-use"),
    allowed_tools: str = typer.Option("", "--allowed-tools"),
    parent: str | None = typer.Option(None, "--parent"),
) -> None:
    """Create a skill item and its Claude pointer."""
    svc = get_service()
    resolved_parent = await resolve_item_id_any(parent, svc) if parent else None
    item = await svc.add_skill(
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
@common.command
async def _resolve_addr(
    ctx: typer.Context, addr: str = typer.Argument(..., metavar="ADDR")
) -> None:
    svc = get_service()
    ctx.ensure_object(dict)
    ctx.obj = {"id": await resolve_agent_addr(addr, ItemType.SKILL, svc)}


@_addr.command("show")
@common.command
async def skill_show(
    ctx: typer.Context,
    raw: bool = typer.Option(False, "--raw", help="Print plain body text (no markdown rendering)."),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Show a skill's metadata panel and body."""
    item_id: str = ctx.obj["id"]
    svc = get_service()
    it = await svc.get(item_id)
    if json_out:
        print_json_clean(
            json.dumps(
                {
                    "id": it.id,
                    "slug": it.extra.get(X.SLUG, it.slug),
                    "title": it.title,
                    "status": it.status,
                    "description": it.extra.get(X.DESCRIPTION, ""),
                    "when_to_use": it.extra.get(X.WHEN_TO_USE, ""),
                    "allowed_tools": it.extra.get(X.ALLOWED_TOOLS, ""),
                    "path": it.path,
                }
            )
        )
        return
    rows = [
        f"[bold]{it.id}[/bold] {e(it.title)}",
        f"[bold]slug:[/bold] {it.extra.get(X.SLUG, it.slug)}",
        f"[bold]status:[/bold] {it.status}",
        f"[bold]file:[/bold] {it.path}",
    ]
    if it.extra.get(X.WHEN_TO_USE):
        rows.append(f"[bold]when to use:[/bold] {e(it.extra[X.WHEN_TO_USE])}")
    console.print(Panel("\n".join(rows), expand=False))
    body = await svc.read_body(it.id)
    render_body_text(
        body,
        raw=raw,
        empty_hint="(empty — run `sq sync` to regenerate the skill definition)",
    )


@_addr.command("refs")
@common.command
async def skill_refs(
    ctx: typer.Context,
    out: bool = typer.Option(False, "--out", help="Forward refs (default)."),
    incoming: bool = typer.Option(False, "--in", help="Backrefs (computed)."),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Show the skill's references (forward stored; backrefs computed)."""
    item_id: str = ctx.obj["id"]
    svc = get_service()
    show_out = out or not incoming
    show_in = incoming
    data: dict[str, list[dict[str, str]]] = {}
    if show_out:
        data["out"] = [{"id": i, "kind": k} for i, k in await svc.refs_out(item_id)]
    if show_in:
        data["in"] = [{"id": i, "kind": k} for i, k in await svc.refs_in(item_id)]
    if json_out:
        print_json_clean(json.dumps(data))
        return
    for direction, label in (("out", "→ refs"), ("in", "← backrefs")):
        if direction not in data:
            continue
        for entry in data[direction]:
            console.print(f"{label}  {e(entry['id'])}  [dim]{entry['kind']}[/dim]")


# ---------------------------------------------------------------- ref add / rm

_ref_app = typer.Typer(no_args_is_help=True, help="Manage forward reference edges.")


@_ref_app.command("add")
@common.command
async def skill_ref_add(
    ctx: typer.Context,
    target: str = typer.Argument(..., help="Target item ID."),
    kind: str = typer.Option("related", "--kind", help="Edge kind (related, implements, …)."),
) -> None:
    """Add a forward reference from this skill to TARGET."""
    item_id: str = ctx.obj["id"]
    svc = get_service()
    raw_id, embedded_kind = split_ref(target)
    resolved_id = await resolve_item_id_any(raw_id, svc)
    effective_kind = embedded_kind if embedded_kind != DEFAULT_KIND else kind
    await svc.add_ref(item_id, resolved_id, kind=effective_kind)
    console.print(f"{item_id} → {resolved_id} ([dim]{effective_kind}[/dim])")


@_ref_app.command("rm")
@common.command
async def skill_ref_rm(
    ctx: typer.Context, target: str = typer.Argument(..., help="Target item ID.")
) -> None:
    """Remove a forward reference from this skill to TARGET."""
    item_id: str = ctx.obj["id"]
    svc = get_service()
    raw_id, _ = split_ref(target)
    resolved_id = await resolve_item_id_any(raw_id, svc)
    await svc.rm_ref(item_id, resolved_id)
    console.print(f"removed {item_id} → {resolved_id}")


_addr.add_typer(_ref_app, name="ref")


@_addr.command("regen")
@common.command
async def skill_regen(ctx: typer.Context) -> None:
    """Regenerate the Claude pointer from the item."""
    item_id: str = ctx.obj["id"]
    svc = get_service()
    await svc.regen(item_id)
    console.print(f"regenerated pointer for {item_id}")


@_addr.command("rm")
@common.command
async def skill_rm(
    ctx: typer.Context,
    purge: bool = typer.Option(False, "--purge", help="Also delete the markdown file."),
) -> None:
    """Remove a skill (and its pointer; --purge also deletes the markdown)."""
    item_id: str = ctx.obj["id"]
    svc = get_service()
    await svc.remove_item(item_id, purge=purge)
    console.print(f"removed {item_id}" + (" (purged)" if purge else ""))


skill_app.add_typer(_addr, name="_addr", hidden=True)
