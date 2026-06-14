"""`sq role …` — manage agent roles (catalog/activate/show/regen/rm).

Grammar:
  sq role catalog                    — show the bundled role catalog
  sq role activate <slug>            — activate a bundled role
  sq role <slug|id|n> show           — show a role's card + body
  sq role <slug|id|n> regen          — regenerate the Claude pointer
  sq role <slug|id|n> rm [--purge]   — remove the role item

Address resolution order (exact match, no fuzzy):
  full-ID shape (ROLE-000001) → bare number → exact slug
"""
# Commands registered via Typer decorators (side effects) read as unused to static analysis.
# pyright: reportUnusedFunction=false

import json

import typer
from rich.panel import Panel
from rich.table import Table

from squads._cli._common import (
    AddressDispatchGroup,
    _is_full_id_shape,  # pyright: ignore[reportPrivateUsage]
    console,
    e,
    get_service,
    handle_errors,
    render_body_text,
    resolve_agent_addr,
)
from squads._errors import SquadsError
from squads._models._enums import ItemType
from squads._models._extras import ExtraKey as X
from squads._roles._catalog import PREDEFINED
from squads._roles._resolver import resolve_role

role_app = typer.Typer(
    no_args_is_help=True,
    help="Manage agent roles.",
    epilog=(
        "Address a role:  sq role <slug|id|n> show|regen|rm\n"
        "Examples:  sq role manager show   sq role 1 regen   sq role ROLE-000001 rm\n"
        "Note: a slug matching a group verb (catalog, activate) is unaddressable by slug; "
        "use the full ID or bare number instead."
    ),
    cls=AddressDispatchGroup,
)

# --------------------------------------------------------------------------- catalog


@role_app.command("catalog")
@handle_errors
def role_catalog(json_out: bool = typer.Option(False, "--json")) -> None:
    """Show the bundled role catalog (slug, name, title, default indicator)."""
    if json_out:
        console.print_json(
            json.dumps(
                [
                    {
                        "slug": r.slug,
                        "full_name": r.full_name,
                        "title": r.title,
                        "is_default": r.is_default,
                    }
                    for r in PREDEFINED
                ]
            )
        )
        return
    table = Table(box=None, pad_edge=False)
    for col in ("Slug", "Name", "Title", "Default"):
        table.add_column(col)
    for r in PREDEFINED:
        table.add_row(r.slug, r.full_name, r.title, "✓" if r.is_default else "")
    console.print(table)


# --------------------------------------------------------------------------- activate


@role_app.command("activate")
@handle_errors
def activate_role(
    slug: str = typer.Argument(...),
    name: str | None = typer.Option(
        None, "--name", help="Full name for this agent (overrides bundled default)."
    ),
) -> None:
    """Activate a bundled role: create its tracked item and Claude pointer."""
    svc = get_service()
    item = svc.activate_role(slug, name=name)
    svc.refresh_managed()
    console.print(f"activated [bold]{item.extra.get(X.FULL_NAME, item.title)}[/bold] ({item.id})")


# ---------------------------------------------------------------- addressed subgroup (_addr)

_addr = typer.Typer(no_args_is_help=True, help="Operate on a role by slug, ID, or number.")

# Context key for the raw address token (stored alongside the resolved id).
_ADDR_KEY = "addr"
_ID_KEY = "id"


@_addr.callback()
@handle_errors
def _resolve_addr(ctx: typer.Context, addr: str = typer.Argument(..., metavar="ADDR")) -> None:
    """Resolve the address token; for ``show`` also allow bundled-only slugs (graceful fallback).

    Stores ``{"addr": <raw>, "id": <resolved_or_None>}`` in ctx.obj.  The resolved id is None
    when the token is a slug that exists only in the bundled catalog (not yet activated).  Commands
    that require a live DB item (``regen``, ``rm``) must call ``_require_id()``; ``show`` handles
    the None case by rendering a bundled catalog card with an activation hint.
    """
    svc = get_service()
    ctx.ensure_object(dict)
    ctx.obj = {_ADDR_KEY: addr}
    t = addr.strip()
    # Detect numeric or full-ID-shaped tokens (TYPE-NNNNNN).
    if t.isdigit() or _is_full_id_shape(t):
        # Numeric or full-ID tokens: strict DB resolution — wrong-type errors bubble up.
        ctx.obj[_ID_KEY] = resolve_agent_addr(addr, ItemType.ROLE, svc)
    else:
        # Slug token: try DB; if not found, store None so show() can render a bundled card.
        try:
            ctx.obj[_ID_KEY] = resolve_agent_addr(addr, ItemType.ROLE, svc)
        except SquadsError:
            ctx.obj[_ID_KEY] = None


def _require_id(ctx: typer.Context) -> str:
    """Return the resolved item ID, or raise SquadsError for commands that need a live DB item."""
    item_id: str | None = ctx.obj[_ID_KEY]
    if item_id is None:
        addr: str = ctx.obj[_ADDR_KEY]
        raise SquadsError(f"no role with slug, ID, or number {addr!r} — activate it first")
    return item_id


@_addr.command("show")
@handle_errors
def show_role(
    ctx: typer.Context,
    raw: bool = typer.Option(False, "--raw", help="Print plain body text (no markdown rendering)."),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Show a role's catalog card plus active item body.

    Works for both activated roles (resolves via DB) and bundled-only roles (catalog card +
    activation hint).
    """
    item_id: str | None = ctx.obj[_ID_KEY]
    addr: str = ctx.obj[_ADDR_KEY]
    svc = get_service()

    if item_id is not None:
        # Activated role: resolve slug from the item.
        it = svc.get(item_id)
        slug: str = it.extra.get(X.SLUG, it.slug)
    else:
        # Bundled-only role: the addr IS the slug (slug resolution fell through without finding it).
        slug = addr

    if json_out:
        data: dict[str, object] = {"slug": slug, "id": item_id, "activated": item_id is not None}
        try:
            r = resolve_role(slug, svc.paths.squad_dir)
            data.update(
                {
                    "full_name": r.full_name,
                    "title": r.title,
                    "mission": r.mission,
                    "model": r.model,
                    "is_default": r.is_default,
                    "responsibilities": list(r.responsibilities),
                }
            )
        except SquadsError:
            if item_id is not None:
                it3 = svc.get(item_id)
                data.update(
                    {
                        "full_name": it3.extra.get(X.FULL_NAME, it3.title),
                        "title": it3.extra.get(X.TITLE, ""),
                        "mission": it3.extra.get(X.MISSION, ""),
                        "model": it3.extra.get(X.MODEL),
                        "is_default": it3.extra.get(X.IS_DEFAULT, False),
                        "responsibilities": it3.extra.get(X.RESPONSIBILITIES, []),
                    }
                )
            else:
                raise SquadsError(f"no role with slug, ID, or number {addr!r}") from None
        console.print_json(json.dumps(data))
        return

    # Build the catalog card from the resolved role definition (project override → bundled).
    try:
        r = resolve_role(slug, svc.paths.squad_dir)
        rows = [
            f"[bold]{e(r.full_name)}[/bold] (`{e(r.slug)}`)",
            f"[bold]title:[/bold] {e(r.title)}",
            f"[bold]model:[/bold] {e(r.model or 'inherit')}",
            f"[bold]mission:[/bold] {e(r.mission)}",
            "[bold]responsibilities:[/bold]",
            *(f"  - {e(x)}" for x in r.responsibilities),
        ]
    except SquadsError:
        # Custom role not in the bundled catalog — fall back to the item fields.
        if item_id is not None:
            it2 = svc.get(item_id)
            rows = [
                f"[bold]{e(it2.extra.get(X.FULL_NAME, it2.title))}[/bold] (`{e(slug)}`)",
                f"[bold]id:[/bold] {it2.id}",
                f"[bold]status:[/bold] {it2.status.value}",
            ]
        else:
            raise SquadsError(f"no role with slug, ID, or number {addr!r}") from None
    console.print(Panel("\n".join(rows), expand=False))

    # Active item body — styled markdown on a TTY, plain with --raw or when piped.
    body: str | None = None
    try:
        body = svc.role_body(slug)
    except SquadsError:
        body = None

    if body is not None:
        render_body_text(
            body,
            raw=raw,
            empty_hint="(empty — run `sq sync` to regenerate the role definition)",
        )
    else:
        console.print()
        console.print(
            f"[dim](no active item for {e(slug)} — run `sq role activate {e(slug)}`"
            " then `sq sync` to populate the full definition)[/dim]"
        )


@_addr.command("regen")
@handle_errors
def regen_role(ctx: typer.Context) -> None:
    """Regenerate a role's Claude pointer from its item."""
    item_id = _require_id(ctx)
    svc = get_service()
    svc.regen(item_id)
    console.print(f"regenerated pointer for {item_id}")


@_addr.command("rm")
@handle_errors
def rm_role(
    ctx: typer.Context,
    purge: bool = typer.Option(False, "--purge", help="Also delete the markdown file."),
) -> None:
    """Remove a role (and its pointer; --purge also deletes the markdown)."""
    item_id = _require_id(ctx)
    svc = get_service()
    svc.remove_item(item_id, purge=purge)
    svc.refresh_managed()
    console.print(f"removed {item_id}" + (" (purged)" if purge else ""))


role_app.add_typer(_addr, name="_addr", hidden=True)
