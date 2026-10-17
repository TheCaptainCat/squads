"""`sq skill …` — manage agent skills (add/show/regen/remove/refs/view).

Grammar:
  sq skill add <name> [options]        — create a skill item + pointer
  sq skill <slug|id|n> show             — show a skill's metadata panel
  sq skill <slug|id|n> body -m "…"      — set/append a custom skill's body
  sq skill <slug|id|n> refs             — show forward refs and backrefs
  sq skill <slug|id|n> ref add <id>     — add a forward reference
  sq skill <slug|id|n> ref rm <id>      — remove a forward reference
  sq skill <slug|id|n> link-role <role> — scope the skill to a role (+ resync that role)
  sq skill <slug|id|n> unlink-role <role> — remove that scope (+ resync that role)
  sq skill <slug|id|n> regen            — regenerate the Claude pointer
  sq skill <slug|id|n> status <S>       — transition the skill's status
  sq skill <slug|id|n> view add <name>       — place or re-enable a view tag in sq:body
  sq skill <slug|id|n> view disable <name>   — disable a view tag in sq:body (kept, not removed)
  sq skill <slug|id|n> remove --purge — delete the skill item (or set status Archived)

Address resolution order (exact match, no fuzzy):
  full-ID shape (SKILL-1) → bare number → exact slug
"""
# Commands registered via Typer decorators (side effects) read as unused to static analysis.
# pyright: reportUnusedFunction=false

import json

import typer
from rich.panel import Panel

import squads._cli._common as common
from squads import __version__
from squads import _views as views
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
    resolve_item_id_any,
    view_disable_result_message,
)
from squads._interactions import (
    ITEM_SKILL_VIEW_NAME,
    SYSTEM_SKILL_VIEW_NAMES,
    is_system_skill,
    orphaned_skill_item_type,
    resolve_operator_invocable,
)
from squads._models import _attributes as attrs
from squads._models._attributes import AttributeKey
from squads._models._item import split_ref
from squads._models._schema import version_drifted

_INVOCABLE_HELP = (
    "Offer the skill to the person at the keyboard: yes, no, or default to follow the "
    "declared default again."
)


class _SkillDispatchGroup(AddressDispatchGroup):
    """Routes an address token to the hidden addressed subgroup."""


skill_app = typer.Typer(
    no_args_is_help=True,
    help="Manage agent skills.",
    epilog=common.address_epilog(
        "skill",
        "skill",
        (
            "sq skill squads show",
            "sq skill 2 regen",
            "sq skill SKILL-2 remove --purge",
            "sq skill squads status Archived",
            "sq skill squads view disable squads_skill",
        ),
        "add",
    ),
    cls=_SkillDispatchGroup,
)

# --------------------------------------------------------------------------- add


@skill_app.command("add")
@common.command
async def skill_add(
    name: str = typer.Argument(..., help="The skill's title; its slug is made from it."),
    desc: str = common.desc_option(),
    when_to_use: str = typer.Option(
        "", "--when-to-use", help="When an agent should reach for the skill."
    ),
    allowed_tools: str = typer.Option(
        "", "--allowed-tools", help="Tools the skill may use, recorded on the skill."
    ),
    parent: str | None = common.parent_option(),
    operator_invocable: str | None = typer.Option(
        None, "--operator-invocable", help=_INVOCABLE_HELP
    ),
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
        operator_invocable=operator_invocable,
    )
    console.print(f"created skill [bold]{item.id}[/bold] → {item.path}")


# ---------------------------------------------------------------- addressed subgroup (_addr)

_addr = typer.Typer(
    no_args_is_help=True,
    cls=common.AddressedGroup,
    help="Operate on a skill by slug, ID, or number.",
)


@_addr.callback()
@common.command
async def _resolve_addr(
    ctx: typer.Context,
    addr: str = typer.Argument(
        ..., metavar=common.ADDRESS_METAVAR, help="Skill slug, ID or number."
    ),
) -> None:
    svc = get_service()
    ctx.ensure_object(dict)
    ctx.obj = {"id": await resolve_agent_addr(addr, "skill", svc)}


@_addr.command("show")
@common.command
async def skill_show(
    ctx: typer.Context,
    raw: bool = common.raw_option(),
    json_out: bool = typer.Option(False, "--json", help="Print one JSON object: the skill."),
    comments: bool = typer.Option(
        False, "--comments", help="Append the discussion as comments (text output)."
    ),
) -> None:
    """Show a skill's metadata panel and body."""
    item_id: str = ctx.obj["id"]
    svc = get_service()
    it = await svc.get(item_id)
    slug = it.slug
    system = is_system_skill(slug, svc.spec)
    invocable, invocable_set = resolve_operator_invocable(slug, it, svc.spec)
    if json_out:
        print_json_clean(
            json.dumps(
                {
                    "id": it.id,
                    "slug": slug,
                    "title": it.title,
                    "status": it.status,
                    "description": it.description,
                    "when_to_use": attrs.string_attribute(it, AttributeKey.WHEN_TO_USE) or "",
                    "allowed_tools": attrs.string_attribute(it, AttributeKey.ALLOWED_TOOLS) or "",
                    "operator_invocable": invocable,
                    "operator_invocable_set": invocable_set,
                    "path": it.path,
                    **common.origin_json(attrs.origin(it)),
                    # Tag-expanded, same as an ordinary item's `show --json` body field.
                    "body": await svc.read_body(it.id),
                }
            )
        )
        return
    await common.warn_duplicate_id(svc, it)
    rows = [
        f"[bold]{it.id}[/bold] {e(it.title)}",
        f"[bold]slug:[/bold] {slug}",
        f"[bold]origin:[/bold] {attrs.origin(it) or '—'}",
        f"[bold]status:[/bold] {it.status}",
        f"[bold]operator invocable:[/bold] {'yes' if invocable else 'no'} "
        f"({'set by this squad' if invocable_set else 'declared default'})",
        f"[bold]file:[/bold] {it.path}",
    ]
    when_to_use = attrs.string_attribute(it, AttributeKey.WHEN_TO_USE)
    if when_to_use:
        rows.append(f"[bold]when to use:[/bold] {e(when_to_use)}")
    console.print(Panel("\n".join(rows), expand=False))
    # Every skill's body reads through the same shared boundary (`read_body`, tag-expanded for
    # a system-owned body off its seeded `sq:view:<name>` tag; authored content unchanged for a
    # custom one — there is no branch on `system` here any more). Five reasons a system skill's
    # body can read empty, and they are not the same fact: its item type (or, for a per-item-type
    # skill, the type its slug documents) is no longer declared (`orphaned_skill_item_type` — the
    # same predicate `sq check`/`sync` already use for this exact question, so this hint can
    # never disagree with them about which case applies); or the type is live but the *view* this
    # slug would render — `SYSTEM_SKILL_VIEW_NAMES[slug]` for one of the three permanent slugs,
    # `ITEM_SKILL_VIEW_NAME` for every other per-type skill — is itself not declared in
    # `self.spec.views` (`views.empty_body_hint_state`'s first question, matching the same
    # condition `MaintenanceMixin._repair_body_tag`'s classifier gates the backfill on); or the
    # view is declared and a version drift is still outstanding, the one state `sq sync`
    # actually fixes; or the view is declared with no drift outstanding — `sq sync`'s trigger
    # has nothing to run, so it is a no-op against this body and the hint must name a remedy
    # that actually is one (`views.empty_body_hint_state`'s second question). A custom skill's
    # body reads empty for a sixth reason entirely — nobody has written it yet.
    dropped_type = orphaned_skill_item_type(slug, svc.spec) if system else None
    view_name = SYSTEM_SKILL_VIEW_NAMES.get(slug) or (ITEM_SKILL_VIEW_NAME if system else None)
    if dropped_type is not None:
        empty_hint = (
            f"(no definition — the item type {dropped_type!r} this skill described is no "
            "longer declared; restore the type, or retire this skill)"
        )
    elif system and view_name is not None:
        hint_state = views.empty_body_hint_state(
            view_name,
            svc.spec,
            drift_outstanding=version_drifted(__version__, svc.paths.config.squads_version),
            disabled=await svc.view_tag_state(it.id, view_name) is True,
        )
        if hint_state == "disabled":
            empty_hint = f"(disabled — `sq skill {slug} view add {view_name}` re-enables it)"
        elif hint_state == "view_undeclared":
            empty_hint = (
                f"(empty — the view {view_name!r} this skill renders is not declared in this "
                "project's spec, so `sq sync` cannot populate it; declare it to restore the "
                "generated definition — or, if this skill's body still carries this tag from "
                f"before it was dropped, disable it with `sq skill {slug} view disable "
                f"{view_name}`)"
            )
        elif hint_state == "declared_drift_outstanding":
            empty_hint = "(empty — run `sq sync` to populate it)"
        else:
            surface = views.skill_authoring_surface(view_name, slug, svc.spec, svc.playbook)
            empty_hint = (
                f"(empty — its content's real authoring surface is {surface}; author it "
                f"there instead — or run `sq skill {slug} view add {view_name}` directly)"
            )
    else:
        empty_hint = f'(empty — write it with `sq skill {slug} body -m "…"`)'
    render_body_text(
        await svc.read_body(it.id),
        raw=raw,
        empty_hint=empty_hint,
    )
    if comments:
        common.print_comments(await svc.comments(it.id))


@_addr.command("refs")
@common.command
async def skill_refs(
    ctx: typer.Context,
    out: bool = typer.Option(False, "--out", help="Show the refs this skill carries; the default."),
    incoming: bool = typer.Option(
        False, "--in", help="Show the refs other items carry to this one."
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object, with an array per direction shown."
    ),
) -> None:
    """List the skill's refs, or the refs other items carry to it."""
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

_ref_app = typer.Typer(no_args_is_help=True, help="Add or remove the skill's refs.")


@_ref_app.command("add")
@common.command
async def skill_ref_add(
    ctx: typer.Context,
    target: str = typer.Argument(
        ..., help="Item ID or number to ref; `ID:kind` also sets the kind."
    ),
    kind: str = typer.Option(
        "",
        "--kind",
        help="Ref kind (see `sq workflow ref-kinds`); without it, the default kind.",
    ),
) -> None:
    """Add a ref from this skill to TARGET."""
    item_id: str = ctx.obj["id"]
    svc = get_service()
    raw_id, embedded_kind = split_ref(target)
    resolved_id = await resolve_item_id_any(raw_id, svc)
    effective_kind = embedded_kind or kind or svc.spec.default_ref_kind()
    await svc.add_ref(item_id, resolved_id, kind=effective_kind)
    console.print(f"{item_id} → {resolved_id} ([dim]{effective_kind}[/dim])")


@_ref_app.command("rm")
@common.command
async def skill_ref_rm(
    ctx: typer.Context, target: str = typer.Argument(..., help="Item ID or number.")
) -> None:
    """Remove this skill's ref to TARGET."""
    item_id: str = ctx.obj["id"]
    svc = get_service()
    raw_id, _ = split_ref(target)
    resolved_id = await resolve_item_id_any(raw_id, svc)
    await svc.rm_ref(item_id, resolved_id)
    console.print(f"removed {item_id} → {resolved_id}")


_addr.add_typer(_ref_app, name="ref")


@_addr.command("link-role")
@common.command
async def skill_link_role(
    ctx: typer.Context, role: str = typer.Argument(..., help="Role slug, ID, or number.")
) -> None:
    """Scope this skill to ROLE and update that role's pointer at once.

    Prefer this to `ref add --kind scopes`, which writes the same ref but leaves
    the role's pointer stale until the next `sq sync`.
    """
    item_id: str = ctx.obj["id"]
    svc = get_service()
    role_id = await resolve_agent_addr(role, "role", svc)
    await svc.link_role(item_id, role_id)
    console.print(f"{item_id} scoped to {role_id} (role resynced)")


@_addr.command("unlink-role")
@common.command
async def skill_unlink_role(
    ctx: typer.Context, role: str = typer.Argument(..., help="Role slug, ID, or number.")
) -> None:
    """Unscope this skill from ROLE and update that role's pointer at once."""
    item_id: str = ctx.obj["id"]
    svc = get_service()
    role_id = await resolve_agent_addr(role, "role", svc)
    await svc.unlink_role(item_id, role_id)
    console.print(f"{item_id} unscoped from {role_id} (role resynced)")


@_addr.command("regen")
@common.command
async def skill_regen(ctx: typer.Context) -> None:
    """Regenerate the Claude pointer from the item."""
    item_id: str = ctx.obj["id"]
    svc = get_service()
    await svc.regen(item_id)
    console.print(f"regenerated pointer for {item_id}")


@_addr.command("update")
@common.command
async def skill_update(
    ctx: typer.Context,
    title: str | None = typer.Option(None, "--title", help="The skill's display title."),
    desc: str | None = common.desc_option(None),
    when_to_use: str | None = typer.Option(
        None, "--when-to-use", help="When an agent should reach for the skill."
    ),
    operator_invocable: str | None = typer.Option(
        None, "--operator-invocable", help=_INVOCABLE_HELP
    ),
) -> None:
    """Edit a skill's display fields; its slug never changes."""
    common.require_update_fields(
        title=title, desc=desc, when_to_use=when_to_use, operator_invocable=operator_invocable
    )
    item_id: str = ctx.obj["id"]
    await get_service().update(
        item_id,
        title=title,
        description=desc,
        set_attributes=(
            {AttributeKey.WHEN_TO_USE: when_to_use} if when_to_use is not None else None
        ),
        operator_invocable=operator_invocable,
    )
    console.print(f"updated {item_id}")


register_body_verb(_addr, lambda ctx: ctx.obj["id"])
register_remove_verb(_addr, lambda ctx: ctx.obj["id"])
register_comment_verbs(_addr, lambda ctx: ctx.obj["id"])
register_status_verb(_addr, lambda ctx: ctx.obj["id"])


# --------------------------------------------------------------------------- view add/disable

# Place, re-enable or disable an unpaired sq:view:<name> tag in the skill's sq:body region, via
# ServiceCore.add_view/disable_view. `view rm` is retired: a tag is disabled, never deleted.
_view_app = typer.Typer(
    no_args_is_help=True, help="Show or hide declared views in the skill's body."
)


@_view_app.command("add")
@common.command
async def skill_view_add(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Declared view name (see `sq workflow views`)."),
) -> None:
    """Show a declared view in the skill's body, or re-enable it."""
    item_id: str = ctx.obj["id"]
    placed = await get_service().add_view(item_id, name)
    if placed:
        console.print(f"{item_id}: view {e(name)} placed in sq:body")
    else:
        console.print(f"{item_id}: view {e(name)} already present, unchanged")


@_view_app.command("disable")
@common.command
async def skill_view_disable(
    ctx: typer.Context,
    name: str = typer.Argument(
        ..., help="View name; it need not be declared, so a dropped view can be turned off."
    ),
) -> None:
    """Stop showing a view in the skill's body; its tag stays, disabled."""
    item_id: str = ctx.obj["id"]
    svc = get_service()
    was_present = await svc.view_tag_present(item_id, name)
    disabled = await svc.disable_view(item_id, name)
    console.print(
        view_disable_result_message(item_id, name, was_present=was_present, changed=disabled)
    )


_addr.add_typer(_view_app, name="view")

skill_app.add_typer(_addr, name="_addr", hidden=True)

skill_app.info.epilog = (skill_app.info.epilog or "").replace(
    "{verbs}", common.addr_verbs(_addr, ", ")
)
