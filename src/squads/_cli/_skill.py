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

import typer

import squads._cli._common as common
from squads._api import _ops as ops
from squads._api._dto._roster import RosterAddress, ViewRequest
from squads._api._dto._skills import (
    SkillAddRequest,
    SkillRefRemoveRequest,
    SkillRefRequest,
    SkillRefsRequest,
    SkillRoleRequest,
    SkillUpdateRequest,
)
from squads._cli import _calls as calls
from squads._cli._common import (
    AddressDispatchGroup,
    console,
    register_comment_verbs,
)
from squads._cli._render._roster import (
    render_ref_change,
    render_regenerated,
    render_role_link,
    render_skill_added,
    render_skill_refs,
    render_skill_show,
    render_updated,
    render_view_change,
)
from squads._cli._roster import (
    address_of,
    finish_write,
    json_option,
    parse_address,
    register_roster_status_verb,
    register_write_verbs,
)

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
            "sq skill squads status <status>",
            "sq skill squads view disable squads_skill",
        ),
        "add",
    ),
    cls=_SkillDispatchGroup,
)

# --------------------------------------------------------------------------- add


@skill_app.command("add")
@common.handle_errors
def skill_add(
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
    as_: str | None = common.edit_as_option(),
    json_out: bool = json_option("Print one JSON object: the skill created."),
) -> None:
    """Create a skill item and its Claude pointer."""
    common.declare_actor(as_)
    request = SkillAddRequest(
        name=name,
        description=desc,
        when_to_use=when_to_use,
        allowed_tools=allowed_tools,
        parent=parent,
        operator_invocable=operator_invocable,
    )
    response = calls.call(ops.SKILLS_ADD, request)
    finish_write(
        ops.SKILLS_ADD, response, json_out, lambda write: render_skill_added(write.entry, console)
    )


# ---------------------------------------------------------------- addressed subgroup (_addr)

_addr = typer.Typer(
    no_args_is_help=True,
    cls=common.AddressedGroup,
    help="Operate on a skill by slug, ID, or number.",
)


@_addr.callback()
@common.handle_errors
def _resolve_addr(
    ctx: typer.Context,
    addr: str = typer.Argument(
        ..., metavar=common.ADDRESS_METAVAR, help="Skill slug, ID or number."
    ),
) -> None:
    """Keep the address for the verb's operation, which resolves it."""
    parse_address(ctx, addr)


@_addr.command("show")
@common.handle_errors
def skill_show(
    ctx: typer.Context,
    raw: bool = common.raw_option(),
    json_out: bool = typer.Option(False, "--json", help="Print one JSON object: the skill."),
    comments: bool = typer.Option(
        False, "--comments", help="Append the discussion as comments (text output)."
    ),
) -> None:
    """Show a skill's metadata panel and body."""
    response = calls.call(ops.SKILL_SHOW, RosterAddress(addr=address_of(ctx)))
    if json_out:
        calls.print_json(ops.SKILL_SHOW, response)
        return
    calls.print_warnings(response)
    render_skill_show(response.data, console, raw=raw, comments=comments)


@_addr.command("refs")
@common.handle_errors
def skill_refs(
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
    request = SkillRefsRequest(addr=address_of(ctx), out=out, incoming=incoming)
    response = calls.call(ops.SKILL_REFS, request)
    if json_out:
        calls.print_json(ops.SKILL_REFS, response)
        return
    calls.print_warnings(response)
    render_skill_refs(response.data, console)


# ---------------------------------------------------------------- ref add / rm

_ref_app = typer.Typer(no_args_is_help=True, help="Add or remove the skill's refs.")


@_ref_app.command("add")
@common.handle_errors
def skill_ref_add(
    ctx: typer.Context,
    target: str = typer.Argument(
        ..., help="Item ID or number to ref; `ID:kind` also sets the kind."
    ),
    kind: str = typer.Option(
        "",
        "--kind",
        help="Ref kind (see `sq workflow ref-kinds`); without it, the default kind.",
    ),
    as_: str | None = common.edit_as_option(),
    json_out: bool = json_option("Print one JSON object: the skill, the ref's target and kind."),
) -> None:
    """Add a ref from this skill to TARGET."""
    common.declare_actor(as_)
    request = SkillRefRequest(addr=address_of(ctx), target=target, kind=kind)
    response = calls.call(ops.SKILL_REF_ADD, request)
    finish_write(
        ops.SKILL_REF_ADD, response, json_out, lambda change: render_ref_change(change, console)
    )


@_ref_app.command("rm")
@common.handle_errors
def skill_ref_rm(
    ctx: typer.Context,
    target: str = typer.Argument(..., help="Item ID or number."),
    as_: str | None = common.edit_as_option(),
    json_out: bool = json_option("Print one JSON object: the skill and the ref's target."),
) -> None:
    """Remove this skill's ref to TARGET."""
    common.declare_actor(as_)
    request = SkillRefRemoveRequest(addr=address_of(ctx), target=target)
    response = calls.call(ops.SKILL_REF_RM, request)
    finish_write(
        ops.SKILL_REF_RM, response, json_out, lambda change: render_ref_change(change, console)
    )


_addr.add_typer(_ref_app, name="ref")


@_addr.command("link-role")
@common.handle_errors
def skill_link_role(
    ctx: typer.Context,
    role: str = typer.Argument(..., help="Role slug, ID, or number."),
    as_: str | None = common.edit_as_option(),
    json_out: bool = json_option("Print one JSON object: the skill and the role's id."),
) -> None:
    """Scope this skill to ROLE and update that role's pointer at once.

    Prefer this to adding the scoping ref by hand, which writes the same ref but
    leaves the role's pointer stale until the next `sq sync`.
    """
    common.declare_actor(as_)
    request = SkillRoleRequest(addr=address_of(ctx), role=role)
    response = calls.call(ops.SKILL_LINK_ROLE, request)
    finish_write(
        ops.SKILL_LINK_ROLE,
        response,
        json_out,
        lambda link: render_role_link(link, console, linked=True),
    )


@_addr.command("unlink-role")
@common.handle_errors
def skill_unlink_role(
    ctx: typer.Context,
    role: str = typer.Argument(..., help="Role slug, ID, or number."),
    as_: str | None = common.edit_as_option(),
    json_out: bool = json_option("Print one JSON object: the skill and the role's id."),
) -> None:
    """Unscope this skill from ROLE and update that role's pointer at once."""
    common.declare_actor(as_)
    request = SkillRoleRequest(addr=address_of(ctx), role=role)
    response = calls.call(ops.SKILL_UNLINK_ROLE, request)
    finish_write(
        ops.SKILL_UNLINK_ROLE,
        response,
        json_out,
        lambda link: render_role_link(link, console, linked=False),
    )


@_addr.command("regen")
@common.handle_errors
def skill_regen(
    ctx: typer.Context,
    json_out: bool = json_option("Print one JSON object: the skill."),
) -> None:
    """Regenerate the Claude pointer from the item."""
    response = calls.call(ops.SKILL_REGEN, RosterAddress(addr=address_of(ctx)))
    finish_write(
        ops.SKILL_REGEN,
        response,
        json_out,
        lambda write: render_regenerated(write.entry.id, console),
    )


@_addr.command("update")
@common.handle_errors
def skill_update(
    ctx: typer.Context,
    title: str | None = typer.Option(None, "--title", help="The skill's display title."),
    desc: str | None = common.desc_option(None),
    when_to_use: str | None = typer.Option(
        None, "--when-to-use", help="When an agent should reach for the skill."
    ),
    operator_invocable: str | None = typer.Option(
        None, "--operator-invocable", help=_INVOCABLE_HELP
    ),
    as_: str | None = common.edit_as_option(),
    json_out: bool = json_option("Print one JSON object: the skill after the update."),
) -> None:
    """Edit a skill's display fields; its slug never changes."""
    common.require_update_fields(
        title=title, desc=desc, when_to_use=when_to_use, operator_invocable=operator_invocable
    )
    common.declare_actor(as_)
    request = SkillUpdateRequest(
        addr=address_of(ctx),
        title=title,
        description=desc,
        when_to_use=when_to_use,
        operator_invocable=operator_invocable,
    )
    response = calls.call(ops.SKILL_UPDATE, request)
    finish_write(
        ops.SKILL_UPDATE, response, json_out, lambda write: render_updated(write.entry.id, console)
    )


register_write_verbs(_addr, body=ops.SKILL_BODY, remove=ops.SKILL_REMOVE)
register_comment_verbs(
    _addr,
    common.roster_comments(
        (
            ops.SKILL_COMMENTS,
            ops.SKILL_COMMENT_ADD,
            ops.SKILL_COMMENT_SHOW,
            ops.SKILL_COMMENT_EDIT,
            ops.SKILL_COMMENT_REMOVAL,
            ops.SKILL_COMMENT_REMOVE,
        ),
        address_of,
    ),
)
register_roster_status_verb(_addr, status=ops.SKILL_STATUS)


# --------------------------------------------------------------------------- view add/disable

# Place, re-enable or disable an unpaired sq:view:<name> tag in the skill's sq:body region. There
# is no `view rm`: a tag is disabled, never deleted.
_view_app = typer.Typer(
    no_args_is_help=True, help="Show or hide declared views in the skill's body."
)


def _view_change(
    ctx: typer.Context, name: str, as_: str | None, *, enable: bool, json_out: bool
) -> None:
    op = ops.SKILL_VIEW_ADD if enable else ops.SKILL_VIEW_DISABLE
    common.declare_actor(as_)
    response = calls.call(op, ViewRequest(addr=address_of(ctx), name=name))
    finish_write(
        op,
        response,
        json_out,
        lambda change: render_view_change(
            change.entry.id,
            change.view,
            console,
            enable=enable,
            changed=change.changed,
            was_present=change.was_present,
        ),
    )


@_view_app.command("add")
@common.handle_errors
def skill_view_add(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Declared view name (see `sq workflow views`)."),
    as_: str | None = common.edit_as_option(),
    json_out: bool = json_option("Print one JSON object: the skill and what the tag change did."),
) -> None:
    """Show a declared view in the skill's body, or re-enable it."""
    _view_change(ctx, name, as_, enable=True, json_out=json_out)


@_view_app.command("disable")
@common.handle_errors
def skill_view_disable(
    ctx: typer.Context,
    name: str = typer.Argument(
        ..., help="View name; it need not be declared, so a dropped view can be turned off."
    ),
    as_: str | None = common.edit_as_option(),
    json_out: bool = json_option("Print one JSON object: the skill and what the tag change did."),
) -> None:
    """Stop showing a view in the skill's body; its tag stays, disabled."""
    _view_change(ctx, name, as_, enable=False, json_out=json_out)


_addr.add_typer(_view_app, name="view")

skill_app.add_typer(_addr, name="_addr", hidden=True)

skill_app.info.epilog = (skill_app.info.epilog or "").replace(
    "{verbs}", common.addr_verbs(_addr, ", ")
)
