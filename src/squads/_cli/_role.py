"""`sq role …` — manage agent roles (catalog/activate/show/regen/rm/status/set-default/view).

Grammar:
  sq role catalog                    — show the role catalog for the active squad
  sq role activate <slug>            — activate a bundled role
  sq role <slug|id|n> show           — show a role's card + body
  sq role <slug|id|n> regen          — regenerate the Claude pointer
  sq role <slug|id|n> status <S>     — transition the role's status
  sq role <slug|id|n> set-default    — move the default-role designation here
  sq role <slug|id|n> view add <n>   — place a view tag in sq:body
  sq role <slug|id|n> view rm <n>    — remove a view tag from sq:body
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
from squads import __version__
from squads import _views as views
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
from squads._interactions import ROLE_DEFINITION_VIEW_NAME, allowed_create_types
from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._models._schema import version_drifted
from squads._paths import resolve as resolve_squad_paths
from squads._roles._catalog import PREDEFINED, RoleDef
from squads._roles._loader import load_role_catalog
from squads._roles._models import RoleSpec
from squads._roles._resolver import resolve_role_for_item, resolve_role_with_base
from squads._workflow import ROSTER_ROLE

#: The bundled catalog's own slugs — used by ``sq role catalog`` to tell a project-declared or
#: project-overridden entry apart from an as-shipped bundled one (see :func:`role_catalog`).
_BUNDLED_SLUGS: frozenset[str] = frozenset(r.slug for r in PREDEFINED)


class _RoleDispatchGroup(AddressDispatchGroup):
    _ADDR_VERBS: ClassVar[str] = "show|regen|rm|status|set-default|view"


role_app = typer.Typer(
    no_args_is_help=True,
    help="Manage agent roles.",
    epilog=(
        "Address a role:  sq role <slug|id|n> show|regen|rm|status|set-default|view\n"
        "Examples:  sq role manager show   sq role 1 regen   sq role ROLE-1 rm\n"
        "           sq role manager status Archived   sq role qa set-default\n"
        "           sq role qa view rm role_definition   — clear a tag naming a dropped view\n"
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
    footer, and ``--json`` carries the same disclosure as ``default_role`` — the slug that
    holds it, whether or not any row is that slug, and ``null`` when no live role holds it at
    all. ``default_role_source`` says where that answer came from: ``"roster"`` for the active
    squad's designation, ``"catalog"`` for the document's own declaration outside a squad,
    where there is no roster to ask. Both repeat on every row, since this payload is a bare
    array. Without them an all-false column is ambiguous between a holder this listing cannot
    show and no holder at all, and a ``"catalog"`` answer is indistinguishable from a squad
    that designates the same slug for real. ``sq role list`` — the roster listing, which
    carries every live role — is still the surface that names a holder in its own rows.
    """
    squad_dir = _catalog_squad_dir()
    roles = load_role_catalog(squad_dir).roles
    in_squad = squad_dir is not None
    live_default = await get_service().default_role_slug() if in_squad else None

    def _is_default(r: RoleSpec) -> bool:
        return r.slug == live_default if in_squad else r.is_default

    # The holder as a slug, not as a mark on a row — the boolean column can only answer for
    # the rows that exist, and the holder need not be one of them.
    default_role = live_default if in_squad else next((r.slug for r in roles if r.is_default), None)
    default_role_source = "roster" if in_squad else "catalog"

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
                        "default_role": default_role,
                        "default_role_source": default_role_source,
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
    base_role = common.role_base_for_show(slug, it, svc.paths.squad_dir)

    if json_out:
        data = await common.build_role_json_payload(svc, slug, item_id, it, base_role, addr)
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
        preview_name = common.dev_preview_full_name(r, base_role, it)
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
        # There is no `body` verb in the `sq role` addressing group and `set_body` refuses a
        # role body unconditionally, so the default "set it with `body`" hint names an action
        # this group cannot take. `sq sync` is a real remedy for one of the three states
        # `empty_body_hint_state` distinguishes — it converges an empty role body onto its
        # placement tag, but only on an outstanding version drift, and only when the view is
        # declared; naming it in either of the other two states would send an operator in a
        # circle, so this reads the shared predicate rather than guessing.
        hint_state = views.empty_body_hint_state(
            ROLE_DEFINITION_VIEW_NAME,
            svc.spec,
            drift_outstanding=version_drifted(__version__, svc.paths.config.squads_version),
        )
        if hint_state == "declared_no_drift":
            empty_hint = (
                "(empty — `sq sync` cannot populate it: the version-drift backfill it relies "
                "on has nothing outstanding to run. Try `sq repair`, which converges an "
                "already-tagged or plain-legacy body regardless of drift — or, if this body "
                f"is genuinely untagged, `sq role <slug> view add {ROLE_DEFINITION_VIEW_NAME}`)"
            )
        elif hint_state == "declared_drift_outstanding":
            empty_hint = "(empty — run `sq sync` to populate it)"
        else:
            empty_hint = (
                f"(empty — the view {ROLE_DEFINITION_VIEW_NAME!r} is not declared in this "
                "project's spec, so `sq sync` cannot populate it; declare it in "
                "`.overrides/workflow.toml` to restore the generated definition — or, if a "
                f"role's body still carries this tag from before it was dropped, clear it "
                f"with `sq role <slug> view rm {ROLE_DEFINITION_VIEW_NAME}`)"
            )
        render_body_text(
            await svc.read_body(it.id),
            raw=raw,
            empty_hint=empty_hint,
        )
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


# --------------------------------------------------------------------------- view add/rm

# The ``sq role <addr> view add|rm <name>`` group: place or remove an unpaired
# ``sq:view:<name>`` tag in the role's ``sq:body`` region. Mirrors ``_cli._items._cmd_view``'s
# shape (the generic per-type group's own view verb) over ``ServiceCore.insert_view``/
# ``remove_view`` — the same item-type-agnostic mutation, addressed here through the role
# group's own slug/ID/number resolution rather than the generic group. This is the recovery for
# a role whose body already carries a tag naming a view the active spec no longer declares:
# `rm` removes it unconditionally — no ``spec.views`` check, deliberately, because a tag once
# placed must stay removable even for a view that no longer exists — and only an operator
# invoking it ever clears one; nothing in this codebase does it automatically.
_view_app = typer.Typer(no_args_is_help=True, help="Place or remove a view tag in sq:body.")


@_view_app.command("add")
@common.command
async def role_view_add(
    ctx: typer.Context, name: str = typer.Argument(..., help="Declared view name.")
) -> None:
    """Insert the sq:view:NAME tag at the end of sq:body (idempotent)."""
    item_id = _require_id(ctx)
    inserted = await get_service().insert_view(item_id, name)
    if inserted:
        console.print(f"{item_id}: view {e(name)} placed in sq:body")
    else:
        console.print(f"{item_id}: view {e(name)} already present, unchanged")


@_view_app.command("rm")
@common.command
async def role_view_rm(
    ctx: typer.Context, name: str = typer.Argument(..., help="Declared view name.")
) -> None:
    """Remove the sq:view:NAME tag from sq:body (safe no-op if absent)."""
    item_id = _require_id(ctx)
    removed = await get_service().remove_view(item_id, name)
    if removed:
        console.print(f"{item_id}: view {e(name)} removed from sq:body")
    else:
        console.print(f"{item_id}: view {e(name)} was not present, nothing to do")


_addr.add_typer(_view_app, name="view")

role_app.add_typer(_addr, name="_addr", hidden=True)
