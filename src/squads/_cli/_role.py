"""`sq role …` — manage agent roles (catalog/activate/show/regen/remove/status/set-default/view).

Grammar:
  sq role catalog                    — show the role catalog for the active squad
  sq role activate <slug>            — activate a bundled role
  sq role <slug|id|n> show           — show a role's card + body
  sq role <slug|id|n> regen          — regenerate the Claude pointer
  sq role <slug|id|n> status <S>     — transition the role's status
  sq role <slug|id|n> set-default    — move the default-role designation here
  sq role <slug|id|n> view add <n>       — place or re-enable a view tag in sq:body
  sq role <slug|id|n> view disable <n>   — disable a view tag in sq:body (kept, not removed)
  sq role <slug|id|n> remove --purge — delete the role item (or set status Archived)

Address resolution order (exact match, no fuzzy):
  full-ID shape (ROLE-1) → bare number → exact slug
"""
# Commands registered via Typer decorators (side effects) read as unused to static analysis.
# pyright: reportUnusedFunction=false

import json
from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

import squads._cli._common as common
from squads import _pronouns
from squads import _views as views
from squads._cli._common import (
    AddressDispatchGroup,
    console,
    e,
    get_service,
    is_full_id_shape,
    print_json_clean,
    register_body_verb,
    register_comment_verbs,
    register_remove_verb,
    register_status_verb,
    render_body_text,
    resolve_agent_addr,
    view_disable_result_message,
)
from squads._context import get_context
from squads._errors import RoleNotFoundError, SquadsError
from squads._interactions import ROLE_DEFINITION_VIEW_NAME, role_origin
from squads._interactions._role_guidance import allowed_create_types
from squads._models import _attributes as attrs
from squads._models._item import Item
from squads._paths import resolve as resolve_squad_paths
from squads._roles._catalog import RoleDef
from squads._roles._loader import ROLES_OVERRIDE_FILENAME, load_role_catalog
from squads._roles._resolver import (
    pinned_name_of,
    resolve_pronouns,
    resolve_role_for_item,
    resolve_role_with_base,
)
from squads._workflow import ROSTER_ROLE


class _RoleDispatchGroup(AddressDispatchGroup):
    """Routes an address token to the hidden addressed subgroup."""


role_app = typer.Typer(
    no_args_is_help=True,
    help="Manage agent roles.",
    epilog=common.address_epilog(
        "role",
        "role",
        (
            "sq role manager show",
            "sq role 1 regen",
            "sq role ROLE-1 remove --purge",
            "sq role manager status Archived",
            "sq role qa set-default",
            "sq role qa view disable role_definition",
        ),
        "catalog, activate, list",
    ),
    cls=_RoleDispatchGroup,
)

# --------------------------------------------------------------------------- catalog


def _catalog_squad_dir() -> Path | None:
    """The active squad directory for ``sq role catalog``, or ``None`` outside a squad.

    This command has never required an initialized squad — the bundled catalog alone was
    always a valid answer to "what could I activate". Outside a squad there is no
    ``.overrides/roles.toml`` to read, so the bundled catalog stays the honest answer; inside
    one, resolving it lets the listing merge in a project's own catalog-document declarations.
    Mirrors ``_cli._common.working_language_notice``'s own not-a-squad handling (resolve, treat
    ``SquadsError`` as "no squad" rather than a failure).
    """
    ctx = get_context()
    try:
        return resolve_squad_paths(client_cwd=ctx.client_cwd).squad_dir
    except SquadsError:
        return None


@role_app.command("catalog")
@common.command
async def role_catalog(
    json_out: bool = typer.Option(False, "--json", help="Print a JSON array, one object per role."),
) -> None:
    """Show the roles you can activate, with the project's overrides merged in.

    Outside a squad this is the bundled catalog. Inside one it also lists every
    activated role, and the default column marks the role holding the designation
    now (`sq role <addr> set-default`). Name, title and capabilities are the
    catalog's values; `sq role list` shows each live role's resolved ones.
    Fields: sq docs roles

    \f
    The default column reads the same live projection as the generated default-role line, so the
    two never disagree. `default_role` and `default_role_source` repeat on every row because the
    payload is a bare array.
    """
    squad_dir = _catalog_squad_dir()
    roles = load_role_catalog(squad_dir).roles
    in_squad = squad_dir is not None
    live_default = await get_service().default_role_slug() if in_squad else None
    items = {it.slug: it for it in await get_service().list_roles()} if in_squad else {}

    def _is_default(slug: str, declared: bool) -> bool:
        return slug == live_default if in_squad else declared

    def _origin(slug: str) -> str:
        return (attrs.origin(items[slug]) if slug in items else role_origin(slug)) or ""

    # One row per catalog entry, then one per activated role the catalog does not declare.
    rows = [
        (r.slug, r.full_name, r.title, _is_default(r.slug, r.is_default), r.capabilities)
        for r in roles
    ]
    declared = {r.slug for r in roles}
    for it in items.values():
        if it.slug not in declared:
            role = resolve_role_for_item(it, squad_dir)
            rows.append(
                (
                    role.slug,
                    role.full_name,
                    role.title,
                    _is_default(role.slug, False),
                    list(role.capabilities),
                )
            )

    # The holder as a slug, not as a mark on a row — the boolean column can only answer for
    # the rows that exist, and the holder need not be one of them.
    default_role = live_default if in_squad else next((r.slug for r in roles if r.is_default), None)
    default_role_source = "roster" if in_squad else "catalog"

    if json_out:
        print_json_clean(
            json.dumps(
                [
                    {
                        "slug": slug,
                        "full_name": full_name,
                        "title": title,
                        "is_default": is_default,
                        "origin": _origin(slug),
                        "capabilities": list(dict.fromkeys(capabilities)),
                        "default_role": default_role,
                        "default_role_source": default_role_source,
                    }
                    for slug, full_name, title, is_default, capabilities in rows
                ]
            )
        )
        return
    table = Table(box=None, pad_edge=False)
    for col in ("Slug", "Name", "Title", "Default", "Origin"):
        table.add_column(col)
    for slug, full_name, title, is_default, _capabilities in rows:
        table.add_row(e(slug), e(full_name), e(title), "✓" if is_default else "", _origin(slug))
    console.print(table)
    console.print(
        "\n[dim]Need a wholly custom non-dev role (not in this catalog)? "
        "Run [cyan]sq override scaffold --new <slug>[/cyan], fill in the essentials, "
        "then [cyan]sq role activate <slug>[/cyan].[/dim]",
        soft_wrap=True,
    )


# --------------------------------------------------------------------------- list


@role_app.command("list")
@common.command
async def role_list(
    json_out: bool = typer.Option(False, "--json", help="Print a JSON array, one object per role."),
) -> None:
    """List the activated roles, with the default-role holder marked.

    \f
    The only listing that can name every possible default holder: a developer role, or any role
    added after init, has a roster entry but no catalog row.
    """
    svc = get_service()
    roles = await svc.list_roles()
    # Resolved through the catalog (`sq role <slug> show`'s own seam) so the two never
    # disagree — a project override or catalog change reaches this list without a prior
    # `sq sync` having to heal the item's own stored mirror first.
    resolved = [(r, resolve_role_for_item(r, svc.paths.squad_dir)) for r in roles]
    if json_out:
        print_json_clean(
            json.dumps(
                [
                    {
                        "id": r.id,
                        "slug": role.slug,
                        "full_name": role.full_name,
                        "pronouns": role.pronouns,
                        "title": role.title,
                        "is_default": role.is_default,
                        "capabilities": list(role.capabilities),
                        "status": r.status,
                        **common.origin_json(attrs.origin(r)),
                    }
                    for r, role in resolved
                ]
            )
        )
        return
    live = svc.spec.live_statuses(ROSTER_ROLE)
    table = Table(box=None, pad_edge=False)
    for col in ("Slug", "Name", "Title", "Capabilities", "Default", "Origin", "Live"):
        table.add_column(col)
    for r, role in resolved:
        table.add_row(
            e(role.slug),
            _pronouns.named(
                role.full_name, role.pronouns, enabled=svc.paths.config.display.pronouns
            ),
            e(role.title),
            e(", ".join(role.capabilities)),
            "✓" if role.is_default else "",
            attrs.origin(r) or "",
            "✓" if r.status in live else "",
        )
    console.print(table)


# --------------------------------------------------------------------------- activate


@role_app.command("activate")
@common.command
async def activate_role(
    slug: str = typer.Argument(
        ..., help="A role from `sq role catalog`, or one declared in `.overrides/roles/`."
    ),
    name: str | None = typer.Option(
        None, "--name", help="Full name for this agent instead of the bundled one."
    ),
    pronouns: str | None = common.pronouns_option(),
) -> None:
    """Activate a role: create its tracked item and Claude pointer.

    Scaffold a custom role first with `sq override scaffold --new <slug>`.
    Activating a live role does nothing. A retired role is refused; bring it back
    with `sq role <slug> status <status>`.
    """
    svc = get_service()
    item = await svc.activate_role(slug, name=name, pronouns=pronouns)
    await svc.refresh_managed()
    name = common.named_markup(
        svc, item.title, resolve_pronouns(_pronouns.pronouns(item), svc.paths.squad_dir)
    )
    console.print(f"activated [bold]{name}[/bold] ({item.id})")


# ---------------------------------------------------------------- addressed subgroup (_addr)

_addr = typer.Typer(
    no_args_is_help=True,
    cls=common.AddressedGroup,
    help="Operate on a role by slug, ID, or number.",
)

# Context key for the raw address token (stored alongside the resolved id).
_ADDR_KEY = "addr"
_ID_KEY = "id"


@_addr.callback()
@common.command
async def _resolve_addr(
    ctx: typer.Context,
    addr: str = typer.Argument(
        ..., metavar=common.ADDRESS_METAVAR, help="Role slug, ID or number."
    ),
) -> None:
    """Resolve the address token; for ``show`` also allow bundled-only slugs (graceful fallback).

    Stores ``{"addr": <raw>, "id": <resolved_or_None>}`` in ctx.obj.  The resolved id is None
    when the token is a slug that exists only in the bundled catalog (not yet activated).  Commands
    that require a live DB item (``regen``, ``remove``) call ``_require_id()``; ``show`` handles
    the None case by rendering a bundled catalog card with an activation hint.
    """
    svc = get_service()
    ctx.ensure_object(dict)
    obj: dict[str, str | None] = {_ADDR_KEY: addr}
    ctx.obj = obj
    t = addr.strip()
    # Detect numeric or full-ID-shaped tokens (TYPE-NNNNNN).
    if t.isdigit() or is_full_id_shape(t):
        # Numeric or full-ID tokens: strict DB resolution — wrong-type errors bubble up.
        obj[_ID_KEY] = await resolve_agent_addr(addr, "role", svc)
    else:
        # Slug token: try DB; if not found, store None so show() can render a bundled card.
        try:
            obj[_ID_KEY] = await resolve_agent_addr(addr, "role", svc)
        except SquadsError:
            obj[_ID_KEY] = None


def _require_id(ctx: typer.Context) -> str:
    """Return the resolved item ID, or raise SquadsError for commands that need a live DB item."""
    item_id: str | None = ctx.obj[_ID_KEY]
    if item_id is None:
        addr: str = ctx.obj[_ADDR_KEY]
        raise SquadsError(f"no role with slug, ID, or number {addr!r} — activate it first")
    return item_id


def _role_empty_body_hint(hint_state: views.EmptyBodyHintState, slug: str) -> str:
    """The ``sq role <slug> show`` empty-body hint for *hint_state*. ``body`` is refused while
    the role's view is declared (``--force`` does not lift it), so the default "set it with
    `body`" hint is replaced by the remedy the state calls for; ``sq sync`` is named only where
    it converges an empty body onto its tag. *slug* fills in the real command."""
    name = ROLE_DEFINITION_VIEW_NAME
    if hint_state == "disabled":
        return f"(disabled — `sq role {slug} view add {name}` re-enables it)"
    if hint_state == "declared":
        return (
            "(empty — run `sq sync`; if it stays empty, declare the definition in "
            f"`{ROLES_OVERRIDE_FILENAME}`, or `.overrides/roles/<slug>.toml` for a "
            f"project-defined role, or run `sq role {slug} view add {name}`)"
        )
    return (
        f"(empty — the view {name!r} is not declared in this project's spec, so `sq sync` "
        "cannot populate it; declare it in `.overrides/workflow.toml` to restore the "
        f'generated definition — or write the body with `sq role {slug} body -m "…"` and, '
        f"if it still carries this tag from before the view was dropped, disable the tag with "
        f"`sq role {slug} view disable {name}`)"
    )


@_addr.command("show")
@common.command
async def show_role(
    ctx: typer.Context,
    raw: bool = common.raw_option(),
    json_out: bool = typer.Option(False, "--json", help="Print one JSON object: the role."),
    comments: bool = typer.Option(
        False, "--comments", help="Append the discussion as comments (text output)."
    ),
) -> None:
    """Show a role's catalog card plus active item body.

    A role that is not activated shows its catalog card and how to activate it.
    """
    item_id: str | None = ctx.obj[_ID_KEY]
    addr: str = ctx.obj[_ADDR_KEY]
    svc = get_service()

    it: Item | None = None
    if item_id is not None:
        # Activated role: resolve slug from the item.
        it = await svc.get(item_id)
        slug: str = it.slug
    else:
        # Bundled-only role: the addr IS the slug (slug resolution fell through without finding it).
        slug = addr

    # A role's base is never a function of the slug alone: an activated role (dev or
    # bundled) inherits its own operator-settable fields from the live item
    # (`role_base_from_item`); an unactivated developer slug falls back to the generated pool
    # name. Every other unactivated slug keeps `resolve_role`'s ordinary bundled/new-slug base
    # (``None`` here).
    base_role = common.role_base_for_show(slug, it, svc.paths.squad_dir)
    shown_origin = role_origin(slug) if it is None else attrs.origin(it)
    shown_pronouns = resolve_pronouns(
        _pronouns.pronouns(it) if it is not None else None, svc.paths.squad_dir
    )

    if json_out:
        data = await common.build_role_json_payload(svc, slug, item_id, it, base_role, addr)
        print_json_clean(json.dumps(data))
        return

    if it is not None:
        await common.warn_duplicate_id(svc, it)
    # Build the catalog card from the resolved role definition (project override → bundled).
    # `r` is kept past the try/except (`None` when resolution fails) — the rendered
    # definition below reuses this exact resolution rather than resolving a second time.
    r: RoleDef | None = None
    try:
        r = resolve_role_with_base(
            slug, svc.paths.squad_dir, base=base_role, pinned_name=pinned_name_of(it)
        )
        lane_types = sorted(allowed_create_types(r, svc.spec, svc.playbook))
        creates_display = ", ".join(lane_types) if lane_types else "— (out-of-lane creates warn)"
        # A computed projection over the index, not a field of `r` — resolved live for both
        # an activated role and a bundled-only one (falls back to system membership; see
        # `Service.resolved_skills_for_role`).
        skills = await svc.resolved_skills_for_role(slug)
        skills_display = ", ".join(skills) if skills else "—"
        # Mission/responsibilities are deliberately absent: the resolved definition printed
        # below carries them once, in the form an agent is meant to read, rather than the
        # card repeating what it does not need to.
        shown_name = common.named_markup(svc, r.full_name, shown_pronouns, style="bold")
        rows = [
            f"{shown_name} (`{e(r.slug)}`)",
            f"[bold]title:[/bold] {e(r.title)}",
            f"[bold]origin:[/bold] {shown_origin or '—'}",
            f"[bold]model:[/bold] {e(r.model or 'inherit')}",
            f"[bold]color:[/bold] {e(r.color or '—')}",
            f"[bold]can spawn:[/bold] {'yes' if r.can_spawn else 'no'}",
            f"[bold]capabilities:[/bold] {e(', '.join(r.capabilities) or '—')}",
            f"[bold]creates:[/bold] {e(creates_display)}",
            f"[bold]skills:[/bold] {e(skills_display)}",
        ]
    except RoleNotFoundError:
        # No bundled catalog entry, no dev base, no override file — fall back to the item
        # fields. Narrow for the same reason as the --json branch above: an invalid override
        # must be reported, never quietly replaced by the stored item's own copy of the fields.
        if it is not None:
            rows = [
                f"[bold]{e(it.title)}[/bold] (`{e(slug)}`)",
                f"[bold]id:[/bold] {it.id}",
                f"[bold]origin:[/bold] {shown_origin or '—'}",
                f"[bold]status:[/bold] {it.status}",
            ]
        else:
            raise SquadsError(f"no role with slug, ID, or number {addr!r}") from None
    console.print(Panel("\n".join(rows), expand=False))

    # The definition — styled markdown on a TTY, plain with --raw or when piped — read the
    # same way any other item's body is (`read_body`, tag-expanded), not rendered from `r`
    # directly: the item's own `sq:body` carries the `sq:view:role_definition` tag seeded at
    # activation, and reading it resolves and renders fresh on every call.
    # Keyed on the item's own existence (`it`) alone, not on `r`: `resolve_role_for_item` (the
    # seam the tag's own source resolves through) degrades a broken project override to
    # `RoleDef.from_extra_or_item` rather than raising, so the definition still renders even
    # on the one path where the catalog card above could not resolve `r` — the same graceful
    # degrade every other consumer of a live role item already gets. That degrade is a feature,
    # not a bug to undo — but it must not be a *silent* one: `r is None` here means the catalog
    # card above already fell back to the item's own fields, and the definition pane rendering
    # something plausible-looking must not be the only signal, or an operator has no way to
    # tell a genuinely resolved role from a broken `.overrides/roles.toml` degrading quietly.
    if it is not None:
        if r is None:
            console.print()
            console.print(
                f"[dim](the definition for {e(slug)} could not be resolved — "
                "run `sq check` to see why)[/dim]",
                soft_wrap=True,
            )
        # `body` is refused while the view is declared, so the default hint would name an
        # action that cannot run; the hint names the real remedy for the view's state.
        hint_state = views.empty_body_hint_state(
            ROLE_DEFINITION_VIEW_NAME,
            svc.spec,
            disabled=await svc.view_tag_state(it.id, ROLE_DEFINITION_VIEW_NAME) is True,
        )
        empty_hint = _role_empty_body_hint(hint_state, slug)
        render_body_text(
            await svc.read_body(it.id),
            raw=raw,
            empty_hint=empty_hint,
        )
        if comments:
            common.print_comments(await svc.comments(it.id))
    else:
        console.print()
        console.print(
            f"[dim](no active item for {e(slug)} — run `sq role activate {e(slug)}`"
            " then `sq sync` to populate the full definition)[/dim]",
            soft_wrap=True,
        )


@_addr.command("regen")
@common.command
async def regen_role(ctx: typer.Context) -> None:
    """Regenerate a role's Claude pointer from its item."""
    item_id = _require_id(ctx)
    svc = get_service()
    await svc.regen(item_id)
    console.print(f"regenerated pointer for {item_id}")


@_addr.command("set-default")
@common.command
async def set_default_role(ctx: typer.Context) -> None:
    """Make this role the default role, clearing every other holder.

    A role that is not live is refused, and naming the current holder changes
    nothing. It also restores default-role guidance that a retirement removed.

    \f
    A designation the generated config cannot present is not a designation, hence the refusal of
    a role that is not live.
    """
    item_id = _require_id(ctx)
    svc = get_service()
    result = await svc.set_default_role(item_id)
    if not result.changed:
        console.print(f"{result.item.id} already the default — no change")
        return
    console.print(f"{result.item.id} is now the default")
    for cleared_id in result.cleared:
        console.print(f"  cleared {e(cleared_id)}")


@_addr.command("update")
@common.command
async def update_role(
    ctx: typer.Context,
    title: str | None = typer.Option(None, "--title", help="The role's name."),
    pronouns: str | None = typer.Option(
        None, "--pronouns", help="The role's pronouns; a blank value clears them."
    ),
) -> None:
    """Rename a role or set its pronouns; its slug never changes."""
    common.require_update_fields(title=title, pronouns=pronouns)
    item_id = _require_id(ctx)
    svc = get_service()
    await svc.update(item_id, title=title, pronouns=pronouns)
    await svc.refresh_managed()
    console.print(f"updated {item_id}")


register_body_verb(_addr, _require_id)
register_remove_verb(_addr, _require_id, refresh_managed=True)
register_comment_verbs(_addr, _require_id)
register_status_verb(_addr, _require_id)


# --------------------------------------------------------------------------- view add/disable

# The ``sq role <addr> view add|disable <name>`` group: place, re-enable or disable an unpaired
# ``sq:view:<name>`` tag in the role's ``sq:body`` region.
# Mirrors ``_cli._items._cmd_view``'s shape (the generic per-type group's own view verb) over
# ``ServiceCore.add_view``/``disable_view`` — the same item-type-agnostic mutation, addressed
# here through the role group's own slug/ID/number resolution rather than the generic group.
# ``view disable`` is the recovery for a role whose body already carries a tag naming a view
# the active spec no longer declares: it is ungated — no ``spec.views`` check, deliberately,
# because a tag once placed must stay recoverable even for a view that no longer exists — and
# only an operator invoking it ever clears one; nothing in this codebase does it automatically.
# ``view rm`` is retired outright, with no alias: a tag is disabled, never deleted.
_view_app = typer.Typer(
    no_args_is_help=True, help="Show or hide declared views in the role's body."
)


@_view_app.command("add")
@common.command
async def role_view_add(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Declared view name (see `sq workflow views`)."),
) -> None:
    """Show a declared view in the role's body, or re-enable it."""
    item_id = _require_id(ctx)
    placed = await get_service().add_view(item_id, name)
    if placed:
        console.print(f"{item_id}: view {e(name)} placed in sq:body")
    else:
        console.print(f"{item_id}: view {e(name)} already present, unchanged")


@_view_app.command("disable")
@common.command
async def role_view_disable(
    ctx: typer.Context,
    name: str = typer.Argument(
        ..., help="View name; it need not be declared, so a dropped view can be turned off."
    ),
) -> None:
    """Stop showing a view in the role's body; its tag stays, disabled."""
    item_id = _require_id(ctx)
    svc = get_service()
    was_present = await svc.view_tag_present(item_id, name)
    disabled = await svc.disable_view(item_id, name)
    console.print(
        view_disable_result_message(item_id, name, was_present=was_present, changed=disabled)
    )


_addr.add_typer(_view_app, name="view")

role_app.add_typer(_addr, name="_addr", hidden=True)

role_app.info.epilog = (role_app.info.epilog or "").replace(
    "{verbs}", common.addr_verbs(_addr, ", ")
)
