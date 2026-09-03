"""`sq role …` — manage agent roles (catalog/activate/show/regen/rm/status/set-default).

Grammar:
  sq role catalog                    — show the role catalog for the active squad
  sq role activate <slug>            — activate a bundled role
  sq role <slug|id|n> show           — show a role's card + body
  sq role <slug|id|n> regen          — regenerate the Claude pointer
  sq role <slug|id|n> status <S>     — transition the role's status
  sq role <slug|id|n> set-default    — move the default-role designation here
  sq role <slug|id|n> rm [--purge]   — remove the role item

Address resolution order (exact match, no fuzzy):
  full-ID shape (ROLE-1) → bare number → exact slug
"""
# Commands registered via Typer decorators (side effects) read as unused to static analysis.
# pyright: reportUnusedFunction=false

import json
from pathlib import Path
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
    is_full_id_shape,
    print_json_clean,
    register_status_verb,
    render_body_text,
    resolve_agent_addr,
)
from squads._context import get_context
from squads._errors import RoleNotFoundError, SquadsError
from squads._interactions import allowed_create_types, is_dev_slug
from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._paths import resolve as resolve_squad_paths
from squads._roles._catalog import PREDEFINED, RoleDef
from squads._roles._loader import load_role_catalog
from squads._roles._models import RoleSpec
from squads._roles._resolver import (
    dev_base_for_slug,
    resolve_role_for_item,
    resolve_role_with_base,
    role_base_from_item,
)
from squads._services._service import Service
from squads._workflow import ROSTER_ROLE

#: The bundled catalog's own slugs — used by ``sq role catalog`` to tell a project-declared or
#: project-overridden entry apart from an as-shipped bundled one (see :func:`role_catalog`).
_BUNDLED_SLUGS: frozenset[str] = frozenset(r.slug for r in PREDEFINED)


class _RoleDispatchGroup(AddressDispatchGroup):
    _ADDR_VERBS: ClassVar[str] = "show|regen|rm|status|set-default"


role_app = typer.Typer(
    no_args_is_help=True,
    help="Manage agent roles.",
    epilog=(
        "Address a role:  sq role <slug|id|n> show|regen|rm|status|set-default\n"
        "Examples:  sq role manager show   sq role 1 regen   sq role ROLE-1 rm\n"
        "           sq role manager status Archived   sq role qa set-default\n"
        "Note: a slug matching a group verb (catalog, activate, list) is unaddressable by slug; "
        "use the full ID or bare number instead."
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
    Mirrors ``_cli._common.version_notice``'s own not-a-squad handling (resolve, treat
    ``SquadsError`` as "no squad" rather than a failure).
    """
    ctx = get_context()
    try:
        return resolve_squad_paths(ctx.active_dir, client_cwd=ctx.client_cwd).squad_dir
    except SquadsError:
        return None


@role_app.command("catalog")
@common.command
async def role_catalog(json_out: bool = typer.Option(False, "--json")) -> None:
    """Show the role catalog (slug, name, title, default indicator) for the active squad.

    This is the bundled catalog merged with a project's own ``.overrides/roles.toml``
    declarations (if any): a role the document declares that isn't in the bundled catalog
    appears here, and a bundled role the document overrides shows the project's values. The
    ``Origin``/``origin`` column tells a project-declared or project-overridden entry apart
    from an as-shipped bundled one. Outside a squad, or with no such document, this is exactly
    the bundled catalog.

    The ``Default``/``is_default`` column answers *for the active squad*, not for the catalog
    document: inside a squad it marks the role that currently holds the designation
    (``sq role <addr> set-default``), read through the same live projection the generated
    default-role line is compiled from, so the two never disagree. Outside a squad — where
    there is no roster to ask — it falls back to the catalog's own declared designation.

    Not every holder is expressible here: the catalog lists bundled and project-declared
    entries, so a developer role (``sq dev add``) that holds the designation appears in no row
    and the column is correctly blank throughout. The plain listing names that holder in its
    footer; ``sq role list`` — the roster listing, which carries every live role — is the
    surface that always can.
    """
    squad_dir = _catalog_squad_dir()
    roles = load_role_catalog(squad_dir).roles
    in_squad = squad_dir is not None
    live_default = await get_service().default_role_slug() if in_squad else None

    def _is_default(r: RoleSpec) -> bool:
        return r.slug == live_default if in_squad else r.is_default

    if json_out:
        print_json_clean(
            json.dumps(
                [
                    {
                        "slug": r.slug,
                        "full_name": r.full_name,
                        "title": r.title,
                        "is_default": _is_default(r),
                        "origin": "bundled" if r.slug in _BUNDLED_SLUGS else "project",
                    }
                    for r in roles
                ]
            )
        )
        return
    table = Table(box=None, pad_edge=False)
    for col in ("Slug", "Name", "Title", "Default", "Origin"):
        table.add_column(col)
    for r in roles:
        table.add_row(
            e(r.slug),
            e(r.full_name),
            e(r.title),
            "✓" if _is_default(r) else "",
            "bundled" if r.slug in _BUNDLED_SLUGS else "project",
        )
    console.print(table)
    if live_default is not None and all(r.slug != live_default for r in roles):
        console.print(
            f"\n[dim]The default role is [cyan]{e(live_default)}[/cyan], which this catalog "
            "does not list \u2014 run [cyan]sq role list[/cyan] to see it.[/dim]",
            soft_wrap=True,
        )
    console.print(
        "\n[dim]Need a wholly custom non-dev role (not in this catalog)? "
        "Run [cyan]sq override scaffold --new <slug>[/cyan], fill in the essentials, "
        "then [cyan]sq role activate <slug>[/cyan].[/dim]",
        soft_wrap=True,
    )


# --------------------------------------------------------------------------- list


@role_app.command("list")
@common.command
async def role_list(json_out: bool = typer.Option(False, "--json")) -> None:
    """List the active roster — activated roles, distinct from the bundled `role catalog`.

    Carries the default-role designation (``Default``/``is_default``), resolved per row the
    same way the generated default-role line is: this is the only listing that can name every
    possible holder, since a developer role or any other role added after init has a roster
    entry but no catalog row.
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
                        "title": role.title,
                        "is_default": role.is_default,
                        "status": r.status,
                    }
                    for r, role in resolved
                ]
            )
        )
        return
    live = svc.spec.live_statuses(ROSTER_ROLE)
    table = Table(box=None, pad_edge=False)
    for col in ("Slug", "Name", "Title", "Default", "Live"):
        table.add_column(col)
    for r, role in resolved:
        table.add_row(
            e(role.slug),
            e(role.full_name),
            e(role.title),
            "✓" if role.is_default else "",
            "✓" if r.status in live else "",
        )
    console.print(table)


# --------------------------------------------------------------------------- activate


@role_app.command("activate")
@common.command
async def activate_role(
    slug: str = typer.Argument(...),
    name: str | None = typer.Option(
        None, "--name", help="Full name for this agent (overrides bundled default)."
    ),
) -> None:
    """Activate a role: create its tracked item and Claude pointer.

    ``<slug>`` may be a bundled role (see ``sq role catalog``) or a custom non-dev role defined
    under ``.overrides/roles/<slug>.toml`` — scaffold one with ``sq override scaffold --new
    <slug>``, fill in the essentials, then activate it here.

    Activating an already-live role is a no-op.  A role that exists but has been retired is
    *refused*, not silently returned: bring it back with ``sq role <slug> status <live-status>``.
    """
    svc = get_service()
    item = await svc.activate_role(slug, name=name)
    await svc.refresh_managed()
    console.print(f"activated [bold]{item.title}[/bold] ({item.id})")


# ---------------------------------------------------------------- addressed subgroup (_addr)

_addr = typer.Typer(no_args_is_help=True, help="Operate on a role by slug, ID, or number.")

# Context key for the raw address token (stored alongside the resolved id).
_ADDR_KEY = "addr"
_ID_KEY = "id"


@_addr.callback()
@common.command
async def _resolve_addr(
    ctx: typer.Context, addr: str = typer.Argument(..., metavar="ADDR")
) -> None:
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
    if t.isdigit() or is_full_id_shape(t):
        # Numeric or full-ID tokens: strict DB resolution — wrong-type errors bubble up.
        ctx.obj[_ID_KEY] = await resolve_agent_addr(addr, "role", svc)
    else:
        # Slug token: try DB; if not found, store None so show() can render a bundled card.
        try:
            ctx.obj[_ID_KEY] = await resolve_agent_addr(addr, "role", svc)
        except SquadsError:
            ctx.obj[_ID_KEY] = None


def _require_id(ctx: typer.Context) -> str:
    """Return the resolved item ID, or raise SquadsError for commands that need a live DB item."""
    item_id: str | None = ctx.obj[_ID_KEY]
    if item_id is None:
        addr: str = ctx.obj[_ADDR_KEY]
        raise SquadsError(f"no role with slug, ID, or number {addr!r} — activate it first")
    return item_id


def _role_base_for_show(
    slug: str, it: Item | None, squad_dir: Path | None = None
) -> RoleDef | None:
    """The merge base for ``show``: an item in hand's own operator-settable fields
    (:func:`role_base_from_item` — a bundled role's ``full_name``, a developer role's
    tech/name/model, plus this squad's own catalog-document override merged into a bundled
    role's base) first, the ``-dev`` naming convention's generated preview only when there
    is no item to ask.
    """
    if it is not None:
        return role_base_from_item(it, squad_dir)
    return dev_base_for_slug(slug, squad_dir) if is_dev_slug(slug) else None


def _dev_preview_full_name(r: RoleDef, base_role: RoleDef | None, it: Item | None) -> str | None:
    """The full name to report for a role card — ``None`` when it is a fabricated preview
    rather than a real fact.

    A ``-dev``-shaped slug with no roster entry previews against the generated developer
    template (``dev_base_for_slug``), and that template's ``full_name`` is a pool pick ``sq dev
    add`` is not bound to honour (the pool position it will actually land on depends on how many
    developers exist *at that later point*, not now) — reporting it as the developer's name
    would state a fact activation can immediately contradict. Only the un-declared case is
    blanked: a file that itself sets ``full_name`` is the adopter's own declaration and is
    reported as-is, matching every other role.
    """
    if it is None and base_role is not None and r.full_name == base_role.full_name:
        return None
    return r.full_name


async def _role_json_payload(
    svc: Service,
    slug: str,
    item_id: str | None,
    it: Item | None,
    base_role: RoleDef | None,
    addr: str,
) -> dict[str, object]:
    """The ``--json`` payload for ``show``: the full resolved definition, or an item-field
    fallback for a slug with no bundled catalog entry, no dev base, and no override file.

    ``skills`` is resolved once, ahead of the branch below, and carried into both outcomes:
    it is a computed projection over the index (:meth:`Service.resolved_skills_for_role`),
    never a field of the resolved ``RoleDef`` or the stored item, so neither branch's own
    resolution touches it. Live-only by the same method's own design — an activated role
    resolves its full preload set (system membership plus every ``preload``-scoped skill), a
    bundled-only or retired slug resolves to the system-only fallback.
    """
    data: dict[str, object] = {"slug": slug, "id": item_id, "activated": item_id is not None}
    skills = await svc.resolved_skills_for_role(slug)
    try:
        r = resolve_role_with_base(slug, svc.paths.squad_dir, base=base_role)
        data.update(
            {
                "full_name": _dev_preview_full_name(r, base_role, it),
                "title": r.title,
                "mission": r.mission,
                "model": r.model,
                "is_default": r.is_default,
                "can_spawn": r.can_spawn,
                "create_lane": sorted(allowed_create_types(slug, svc.spec, svc.playbook)),
                "responsibilities": list(r.responsibilities),
                "skills": skills,
            }
        )
    except RoleNotFoundError:
        # Narrow deliberately: this fallback exists for a slug with no bundled catalog entry,
        # no dev base, and no override file — and only that. A broader catch also swallowed an
        # *invalid* project role override — the refusal disappeared and the card rendered from
        # the stored item, so a squad answered as though the broken override were not there.
        # Nothing resolves for this shape, so what can be rebuilt comes from the uniform
        # record (`item.title`/`item.description`) where one exists, and from whatever the
        # item's own `extra` still carries for the rest — a corpus written before the
        # definition stopped being mirrored there answers these; one written since reports the
        # absence honestly rather than inventing a catalog answer there is none of.
        if it is None:
            raise SquadsError(f"no role with slug, ID, or number {addr!r}") from None
        data.update(
            {
                "full_name": it.title,
                "title": it.extra.get(X.TITLE, ""),
                "mission": it.description,
                "model": it.extra.get(X.MODEL),
                "is_default": it.extra.get(X.IS_DEFAULT, False),
                "can_spawn": it.extra.get(X.CAN_SPAWN, False),
                "create_lane": sorted(allowed_create_types(slug, svc.spec, svc.playbook)),
                "responsibilities": it.extra.get(X.RESPONSIBILITIES, []),
                "skills": skills,
            }
        )
    return data


@_addr.command("show")
@common.command
async def show_role(
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

    it: Item | None = None
    if item_id is not None:
        # Activated role: resolve slug from the item.
        it = await svc.get(item_id)
        slug: str = it.extra.get(X.SLUG, it.slug)
    else:
        # Bundled-only role: the addr IS the slug (slug resolution fell through without finding it).
        slug = addr

    # A role's base is never a function of the slug alone: an activated role (dev or
    # bundled) inherits its own operator-settable fields from the live item
    # (`role_base_from_item`); an unactivated developer slug falls back to the generated pool
    # name. Every other unactivated slug keeps `resolve_role`'s ordinary bundled/new-slug base
    # (``None`` here).
    base_role = _role_base_for_show(slug, it, svc.paths.squad_dir)

    if json_out:
        data = await _role_json_payload(svc, slug, item_id, it, base_role, addr)
        print_json_clean(json.dumps(data))
        return

    # Build the catalog card from the resolved role definition (project override → bundled).
    # `r` is kept past the try/except (`None` when resolution fails) — the rendered
    # definition below reuses this exact resolution rather than resolving a second time.
    r: RoleDef | None = None
    try:
        r = resolve_role_with_base(slug, svc.paths.squad_dir, base=base_role)
        lane_types = sorted(allowed_create_types(slug, svc.spec, svc.playbook))
        creates_display = ", ".join(lane_types) if lane_types else "— (out-of-lane creates warn)"
        # A computed projection over the index, not a field of `r` — resolved live for both
        # an activated role and a bundled-only one (falls back to system membership; see
        # `Service.resolved_skills_for_role`).
        skills = await svc.resolved_skills_for_role(slug)
        skills_display = ", ".join(skills) if skills else "—"
        preview_name = _dev_preview_full_name(r, base_role, it)
        display_name = (
            preview_name
            if preview_name is not None
            else f"(unassigned — run `sq dev add --tech {r.slug.removesuffix('-dev')}`)"
        )
        # Mission/responsibilities are deliberately absent: the resolved definition printed
        # below carries them once, in the form an agent is meant to read, rather than the
        # card repeating what it does not need to.
        rows = [
            f"[bold]{e(display_name)}[/bold] (`{e(r.slug)}`)",
            f"[bold]title:[/bold] {e(r.title)}",
            f"[bold]model:[/bold] {e(r.model or 'inherit')}",
            f"[bold]can spawn:[/bold] {'yes' if r.can_spawn else 'no'}",
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
                f"[bold]status:[/bold] {it.status}",
            ]
        else:
            raise SquadsError(f"no role with slug, ID, or number {addr!r}") from None
    console.print(Panel("\n".join(rows), expand=False))

    # The definition — styled markdown on a TTY, plain with --raw or when piped — rendered
    # fresh from `r` on this call, never read from any stored region. Keyed on the item's own
    # existence (`it`), not on a stored region's presence or on `r` alone: every activated
    # role's `sq:body` region is present-but-empty now that nothing writes it, so a branch
    # keyed on the region would misreport an active role as unactivated — and a bundled-only
    # slug with no item resolves `r` just fine (the catalog needs no item), so a branch keyed
    # on `r` alone would show the definition for a role nobody has activated.
    if it is not None and r is not None:
        render_body_text(svc.role_definition_text(r), raw=raw)
    elif it is None:
        console.print()
        console.print(
            f"[dim](no active item for {e(slug)} — run `sq role activate {e(slug)}`"
            " then `sq sync` to populate the full definition)[/dim]",
            soft_wrap=True,
        )
    else:
        # An activated role whose resolution itself failed (e.g. an invalid project
        # override) — nothing to render; `sq check` is where that failure is reported.
        console.print()
        console.print(
            f"[dim](the definition for {e(slug)} could not be resolved — "
            "run `sq check` to see why)[/dim]",
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


@_addr.command("rm")
@common.command
async def rm_role(
    ctx: typer.Context,
    purge: bool = typer.Option(False, "--purge", help="Also delete the markdown file."),
) -> None:
    """Remove a role (and its pointer; --purge also deletes the markdown)."""
    item_id = _require_id(ctx)
    svc = get_service()
    await svc.remove_item(item_id, purge=purge)
    await svc.refresh_managed()
    console.print(f"removed {item_id}" + (" (purged)" if purge else ""))


@_addr.command("set-default")
@common.command
async def set_default_role(ctx: typer.Context) -> None:
    """Move the default-role designation onto this role, clearing every other holder.

    A move, not a set: the previous holder(s) are cleared in the same transaction, so the
    roster never ends up with two roles carrying the designation. Refuses a non-live role
    (a designation the generated config cannot present is not a designation), and reports
    designating the current holder as a no-op rather than an error. This is also the way
    back after a squad has lost its default-role guidance to a retirement — see
    `sq role <addr> status`.
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


register_status_verb(_addr, _require_id)

role_app.add_typer(_addr, name="_addr", hidden=True)
