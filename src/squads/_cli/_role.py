"""`sq role …` — manage agent roles (catalog/activate/show/regen/remove/status/set-default/view).

Grammar:
  sq role catalog                    — show the role catalog for the active squad
  sq role activate <slug>            — activate a catalog role
  sq role activate [<slug>] --from <template> [--tech <t>] — build a role from a role template
  sq role add <slug> …               — create a role that defines itself
  sq role <slug|id|n> show           — show a role's card + body
  sq role <slug|id|n> regen          — regenerate the Claude pointer
  sq role <slug|id|n> status <status>     — transition the role's status
  sq role <slug|id|n> set-default    — move the default-role designation here
  sq role <slug|id|n> update …       — edit the name, pronouns, model or (own definition) fields
  sq role <slug|id|n> view add <n>       — place or re-enable a view tag in sq:body
  sq role <slug|id|n> view disable <n>   — disable a view tag in sq:body (kept, not removed)
  sq role <slug|id|n> remove --purge — delete the role item (or set status Archived)

Address resolution order (exact match, no fuzzy):
  full-ID shape (ROLE-1) → bare number → exact slug
"""
# Commands registered via Typer decorators (side effects) read as unused to static analysis.
# pyright: reportUnusedFunction=false

import typer

import squads._cli._common as common
from squads._api import _ops as ops
from squads._api._dto._roles import (
    RoleActivateRequest,
    RoleAddRequest,
    RoleCatalogRequest,
    RoleListRequest,
    RoleUpdateRequest,
)
from squads._api._dto._roster import RosterAddress, ViewRequest
from squads._api._response import Response
from squads._cli import _calls as calls
from squads._cli._common import (
    AddressDispatchGroup,
    console,
    register_comment_verbs,
)
from squads._cli._render._roster import (
    render_default_move,
    render_named_entry,
    render_regenerated,
    render_role_catalog,
    render_role_list,
    render_role_show,
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
from squads._errors import NotInitializedError, SquadsError
from squads._models._participants import ROLE_GROUP_VERBS
from squads._roles._listing import bundled_catalog


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
            "sq role manager status <status>",
            "sq role qa set-default",
            "sq role qa view disable role_definition",
        ),
        ", ".join(sorted(ROLE_GROUP_VERBS)),
    ),
    cls=_RoleDispatchGroup,
)

# --------------------------------------------------------------------------- catalog


@role_app.command("catalog")
@common.handle_errors
def role_catalog(
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
    payload is a bare array. Outside a squad no operation can run, and the packaged catalog is the
    answer.
    """
    try:
        response = calls.call(ops.ROLES_CATALOG, RoleCatalogRequest())
    except NotInitializedError:
        response = Response(data=bundled_catalog())
    if json_out:
        calls.print_json(ops.ROLES_CATALOG, response)
        return
    calls.print_warnings(response)
    render_role_catalog(response.data, console)


# --------------------------------------------------------------------------- list


@role_app.command("list")
@common.handle_errors
def role_list(
    json_out: bool = typer.Option(False, "--json", help="Print a JSON array, one object per role."),
) -> None:
    """List the activated roles, with the default-role holder marked.

    \f
    The only listing that can name every possible default holder: a developer role, or any role
    added after init, has a roster entry but no catalog row.
    """
    response = calls.call(ops.ROLES_LIST, RoleListRequest())
    if json_out:
        calls.print_json(ops.ROLES_LIST, response)
        return
    calls.print_warnings(response)
    render_role_list(response.data, console)


# --------------------------------------------------------------------------- activate


def activate(request: RoleActivateRequest, as_: str | None, *, json_out: bool) -> None:
    """Activate a role and print it: the one command body `sq role activate` and `sq dev add`
    share."""
    common.declare_actor(as_)
    response = calls.call(ops.ROLES_ACTIVATE, request)
    verb = "activated" if request.from_template is None else "added"
    finish_write(
        ops.ROLES_ACTIVATE,
        response,
        json_out,
        lambda write: render_named_entry(verb, write.entry, console),
    )


@role_app.command("activate")
@common.handle_errors
def activate_role(
    slug: str | None = typer.Argument(
        None,
        help=(
            "A role from `sq role catalog`. With `--from`, the slug to file the role under; "
            "optional when the template declares a slug pattern."
        ),
    ),
    name: str | None = typer.Option(
        None, "--name", help="Full name for this agent instead of the catalog's or the template's."
    ),
    from_template: str | None = typer.Option(
        None, "--from", help="Build the role from a role template, such as `dev`."
    ),
    tech: str | None = common.tech_option(),
    model: str | None = common.model_option(),
    pronouns: str | None = common.pronouns_option(),
    as_: str | None = common.edit_as_option(),
    json_out: bool = json_option("Print one JSON object: the role activated."),
) -> None:
    """Activate a catalog role, or build one from a template with `--from`.

    A role that defines itself is created with `sq role add`. Activating a live
    role does nothing. A retired role is refused; bring it back with
    `sq role <slug> status <status>`.
    """
    request = RoleActivateRequest(
        slug=slug,
        name=name,
        model=model,
        pronouns=pronouns,
        from_template=from_template,
        tech=tech,
    )
    activate(request, as_, json_out=json_out)


def _read_definition(file: str | None) -> str | None:
    """The text of the role definition a ``--file`` names, read as the request's other files
    are: under the name the command line wrote, ``-`` being stdin."""
    if file is None:
        return None
    return common.read_client_text(file, what="role file")


@role_app.command("add")
@common.handle_errors
def add_role(  # noqa: PLR0913 — a flag per definition field
    slug: str = typer.Argument(..., help="Slug to file the new role under."),
    name: str | None = typer.Option(None, "--name", help="Full name of the agent."),
    file: str | None = common.file_option(common.ROLE_DEFINITION_FILE_HELP, metavar="path"),
    job_title: str | None = typer.Option(None, "--job-title", help="The role's job title."),
    desc: str | None = common.desc_option(None),
    mission: str | None = typer.Option(None, "--mission", help="What the role is there to do."),
    capabilities: str | None = typer.Option(
        None, "--capabilities", help="Comma-separated capability names a playbook guide can use."
    ),
    model: str | None = common.model_option(),
    pronouns: str | None = common.pronouns_option(),
    as_: str | None = common.edit_as_option(),
    json_out: bool = json_option("Print one JSON object: the role created."),
) -> None:
    """Create a role that defines itself: its definition is stored on the role.

    Give `--name`, `--job-title`, `--desc` and `--mission`, or a `--file` that
    sets them. A role from the catalog or a template is made with `sq role
    activate`.
    """
    common.declare_actor(as_)
    request = RoleAddRequest(
        slug=slug,
        name=name,
        job_title=job_title,
        description=desc,
        mission=mission,
        capabilities=_split_capabilities(capabilities),
        model=model,
        pronouns=pronouns,
        definition=_read_definition(file),
        source=file,
    )
    response = calls.call(ops.ROLES_ADD, request)
    finish_write(
        ops.ROLES_ADD,
        response,
        json_out,
        lambda write: render_named_entry("added", write.entry, console),
    )


def _split_capabilities(raw: str | None) -> list[str] | None:
    """The capability names in a comma-separated flag; ``None`` when the flag is absent."""
    if raw is None:
        return None
    return [part.strip() for part in raw.split(",") if part.strip()]


# ---------------------------------------------------------------- addressed subgroup (_addr)

_addr = typer.Typer(
    no_args_is_help=True,
    cls=common.AddressedGroup,
    help="Operate on a role by slug, ID, or number.",
)


@_addr.callback()
@common.handle_errors
def _resolve_addr(
    ctx: typer.Context,
    addr: str = typer.Argument(
        ..., metavar=common.ADDRESS_METAVAR, help="Role slug, ID or number."
    ),
) -> None:
    """Keep the address for the verb's operation, which resolves it."""
    parse_address(ctx, addr)


@_addr.command("show")
@common.handle_errors
def show_role(
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
    response = calls.call(ops.ROLE_SHOW, RosterAddress(addr=address_of(ctx)))
    if json_out:
        calls.print_json(ops.ROLE_SHOW, response)
        return
    calls.print_warnings(response)
    render_role_show(response.data, console, raw=raw, comments=comments)


@_addr.command("regen")
@common.handle_errors
def regen_role(
    ctx: typer.Context,
    json_out: bool = json_option("Print one JSON object: the role."),
) -> None:
    """Regenerate a role's Claude pointer from its item."""
    response = calls.call(ops.ROLE_REGEN, RosterAddress(addr=address_of(ctx)))
    finish_write(
        ops.ROLE_REGEN,
        response,
        json_out,
        lambda write: render_regenerated(write.entry.id, console),
    )


@_addr.command("set-default")
@common.handle_errors
def set_default_role(
    ctx: typer.Context,
    as_: str | None = common.edit_as_option(),
    json_out: bool = json_option(
        "Print one JSON object: the role, whether the designation moved and the roles it left."
    ),
) -> None:
    """Make this role the default role, clearing every other holder.

    A role that is not live is refused, and naming the current holder changes
    nothing. It also restores default-role guidance that a retirement removed.

    \f
    A designation the generated config cannot present is not a designation, hence the refusal of
    a role that is not live.
    """
    common.declare_actor(as_)
    response = calls.call(ops.ROLE_SET_DEFAULT, RosterAddress(addr=address_of(ctx)))
    finish_write(
        ops.ROLE_SET_DEFAULT, response, json_out, lambda move: render_default_move(move, console)
    )


@_addr.command("update")
@common.handle_errors
def update_role(  # noqa: PLR0913 — a flag per role field
    ctx: typer.Context,
    title: str | None = typer.Option(None, "--title", help="The role's name."),
    pronouns: str | None = typer.Option(
        None, "--pronouns", help="The role's pronouns; a blank value clears them."
    ),
    model: str | None = typer.Option(
        None, "--model", help="The model the agent runs on; a blank value clears it."
    ),
    job_title: str | None = typer.Option(
        None, "--job-title", help="The job title (a role that defines itself only)."
    ),
    desc: str | None = common.desc_option(None),
    mission: str | None = typer.Option(
        None, "--mission", help="The mission (a role that defines itself only)."
    ),
    capabilities: str | None = typer.Option(
        None,
        "--capabilities",
        help="Comma-separated capability names; blank clears (a role that defines itself only).",
    ),
    color: str | None = typer.Option(
        None, "--color", help="The colour; blank clears (a role that defines itself only)."
    ),
    can_spawn: str | None = typer.Option(
        None,
        "--can-spawn",
        help="`yes` or `no`: may the role spawn agents (a role that defines itself only).",
    ),
    file: str | None = common.file_option(common.ROLE_DELTA_FILE_HELP, metavar="path"),
    as_: str | None = common.edit_as_option(),
    json_out: bool = json_option("Print one JSON object: the role after the update."),
) -> None:
    """Edit a role's name, pronouns, model, or a definition it holds itself.

    The name, pronouns and model are editable on every role. The definition
    flags (`--job-title`, `--desc`, `--mission`, `--capabilities`, `--color`,
    `--can-spawn`, `--file`) apply to a role created with `sq role add`. A role
    from the catalog or a template takes them from the file that defines it, and
    the refusal names it. The slug never changes.
    """
    common.require_update_fields(
        title=title,
        pronouns=pronouns,
        model=model,
        job_title=job_title,
        desc=desc,
        mission=mission,
        capabilities=capabilities,
        color=color,
        can_spawn=can_spawn,
        file=file,
    )
    common.declare_actor(as_)
    request = RoleUpdateRequest(
        addr=address_of(ctx),
        title=title,
        pronouns=pronouns,
        model=model,
        job_title=job_title,
        description=desc,
        mission=mission,
        capabilities=_split_capabilities(capabilities),
        color=color,
        can_spawn=_parse_yes_no("--can-spawn", can_spawn),
        definition=_read_definition(file),
        source=file,
    )
    response = calls.call(ops.ROLE_UPDATE, request)
    finish_write(
        ops.ROLE_UPDATE, response, json_out, lambda write: render_updated(write.entry.id, console)
    )


def _parse_yes_no(flag: str, raw: str | None) -> bool | None:
    """`yes` / `no` as a bool; ``None`` when the flag is absent."""
    if raw is None:
        return None
    if raw not in ("yes", "no"):
        raise SquadsError(f"{flag} takes yes or no, not {raw!r}")
    return raw == "yes"


register_write_verbs(_addr, body=ops.ROLE_BODY, remove=ops.ROLE_REMOVE)
register_comment_verbs(
    _addr,
    common.roster_comments(
        (
            ops.ROLE_COMMENTS,
            ops.ROLE_COMMENT_ADD,
            ops.ROLE_COMMENT_SHOW,
            ops.ROLE_COMMENT_EDIT,
            ops.ROLE_COMMENT_REMOVAL,
            ops.ROLE_COMMENT_REMOVE,
        ),
        address_of,
    ),
)
register_roster_status_verb(_addr, status=ops.ROLE_STATUS)


# --------------------------------------------------------------------------- view add/disable

# ``sq role <addr> view add|disable <name>``, as ``_cli._items._cmd_view`` but addressed by the
# role's slug/ID/number. ``view disable`` is ungated (no ``spec.views`` check) so a tag naming
# a view the spec no longer declares stays recoverable.
_view_app = typer.Typer(
    no_args_is_help=True, help="Show or hide declared views in the role's body."
)


def _view_change(
    ctx: typer.Context, name: str, as_: str | None, *, enable: bool, json_out: bool
) -> None:
    op = ops.ROLE_VIEW_ADD if enable else ops.ROLE_VIEW_DISABLE
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
def role_view_add(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Declared view name (see `sq workflow views`)."),
    as_: str | None = common.edit_as_option(),
    json_out: bool = json_option("Print one JSON object: the role and what the tag change did."),
) -> None:
    """Show a declared view in the role's body, or re-enable it."""
    _view_change(ctx, name, as_, enable=True, json_out=json_out)


@_view_app.command("disable")
@common.handle_errors
def role_view_disable(
    ctx: typer.Context,
    name: str = typer.Argument(
        ..., help="View name; it need not be declared, so a dropped view can be turned off."
    ),
    as_: str | None = common.edit_as_option(),
    json_out: bool = json_option("Print one JSON object: the role and what the tag change did."),
) -> None:
    """Stop showing a view in the role's body; its tag stays, disabled."""
    _view_change(ctx, name, as_, enable=False, json_out=json_out)


_addr.add_typer(_view_app, name="view")

role_app.add_typer(_addr, name="_addr", hidden=True)

role_app.info.epilog = (role_app.info.epilog or "").replace(
    "{verbs}", common.addr_verbs(_addr, ", ")
)
