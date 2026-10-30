"""`sq operator …` — register the humans (operators) who work on the project.

Grammar:
  sq operator add <name> [--slug slug]  — register a human operator
  sq operator <slug|id|n> show           — show an operator's metadata panel
  sq operator <slug|id|n> status <S>     — transition the operator's status
  sq operator <slug|id|n> remove --purge — delete an operator (or set status Archived)

Address resolution order (exact match, no fuzzy):
  full-ID shape (OPER-000001) → bare number → exact slug (op-<first>)
"""
# Commands registered via Typer decorators (side effects) read as unused to static analysis.
# pyright: reportUnusedFunction=false

import typer

import squads._cli._common as common
from squads._api import _ops as ops
from squads._api._dto._operators import (
    OperatorAddRequest,
    OperatorListRequest,
    OperatorUpdateRequest,
)
from squads._api._dto._roster import RosterAddress
from squads._cli import _calls as calls
from squads._cli._common import (
    AddressDispatchGroup,
    console,
    register_comment_verbs,
)
from squads._cli._render._roster import (
    render_named_entry,
    render_operator_list,
    render_operator_show,
    render_updated,
)
from squads._cli._roster import (
    address_of,
    finish_write,
    json_option,
    parse_address,
    register_roster_status_verb,
    register_write_verbs,
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
            "sq operator op-alice status <status>",
        ),
        "add, list",
    ),
    cls=_OperatorDispatchGroup,
)

# --------------------------------------------------------------------------- add


@operator_app.command("add")
@common.handle_errors
def operator_add(
    name: str = typer.Argument(..., help='The person\'s display name, such as "Alice Tester".'),
    slug: str | None = typer.Option(
        None, "--slug", help="Slug to use instead of `op-<first name>`."
    ),
    pronouns: str | None = common.pronouns_option(),
    as_: str | None = common.edit_as_option(),
    json_out: bool = json_option("Print one JSON object: the operator registered."),
) -> None:
    """Register a person who can be assigned work and write items and comments."""
    common.declare_actor(as_)
    request = OperatorAddRequest(name=name, slug=slug, pronouns=pronouns)
    response = calls.call(ops.OPERATORS_ADD, request)
    finish_write(
        ops.OPERATORS_ADD,
        response,
        json_out,
        lambda write: render_named_entry("registered", write.entry, console),
    )


# --------------------------------------------------------------------------- list


@operator_app.command("list")
@common.handle_errors
def operator_list(
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per operator."
    ),
) -> None:
    """List the registered human operators."""
    response = calls.call(ops.OPERATORS_LIST, OperatorListRequest())
    if json_out:
        calls.print_json(ops.OPERATORS_LIST, response)
        return
    calls.print_warnings(response)
    render_operator_list(response.data, console)


# ---------------------------------------------------------------- addressed subgroup (_addr)

_addr = typer.Typer(
    no_args_is_help=True,
    cls=common.AddressedGroup,
    help="Operate on an operator by slug, ID, or number.",
)


@_addr.callback()
@common.handle_errors
def _resolve_addr(
    ctx: typer.Context,
    addr: str = typer.Argument(
        ..., metavar=common.ADDRESS_METAVAR, help="Operator slug, ID or number."
    ),
) -> None:
    """Keep the address for the verb's operation, which resolves it."""
    parse_address(ctx, addr)


@_addr.command("show")
@common.handle_errors
def operator_show(
    ctx: typer.Context,
    raw: bool = common.raw_option(),
    json_out: bool = typer.Option(False, "--json", help="Print one JSON object: the operator."),
    comments: bool = typer.Option(
        False, "--comments", help="Append the discussion as comments (text output)."
    ),
) -> None:
    """Show an operator's metadata panel and body."""
    response = calls.call(ops.OPERATOR_SHOW, RosterAddress(addr=address_of(ctx)))
    if json_out:
        calls.print_json(ops.OPERATOR_SHOW, response)
        return
    calls.print_warnings(response)
    render_operator_show(response.data, console, raw=raw, comments=comments)


@_addr.command("update")
@common.handle_errors
def operator_update(
    ctx: typer.Context,
    title: str | None = typer.Option(None, "--title", help="The operator's display name."),
    pronouns: str | None = typer.Option(
        None, "--pronouns", help="The operator's pronouns; a blank value clears them."
    ),
    as_: str | None = common.edit_as_option(),
    json_out: bool = json_option("Print one JSON object: the operator after the update."),
) -> None:
    """Rename an operator or set their pronouns; the slug never changes."""
    common.require_update_fields(title=title, pronouns=pronouns)
    common.declare_actor(as_)
    request = OperatorUpdateRequest(addr=address_of(ctx), title=title, pronouns=pronouns)
    response = calls.call(ops.OPERATOR_UPDATE, request)
    finish_write(
        ops.OPERATOR_UPDATE,
        response,
        json_out,
        lambda write: render_updated(write.entry.id, console),
    )


register_write_verbs(_addr, body=ops.OPERATOR_BODY, remove=ops.OPERATOR_REMOVE)
register_comment_verbs(
    _addr,
    common.roster_comments(
        (
            ops.OPERATOR_COMMENTS,
            ops.OPERATOR_COMMENT_ADD,
            ops.OPERATOR_COMMENT_SHOW,
            ops.OPERATOR_COMMENT_EDIT,
            ops.OPERATOR_COMMENT_REMOVAL,
            ops.OPERATOR_COMMENT_REMOVE,
        ),
        address_of,
    ),
)
register_roster_status_verb(_addr, status=ops.OPERATOR_STATUS)

operator_app.add_typer(_addr, name="_addr", hidden=True)

operator_app.info.epilog = (operator_app.info.epilog or "").replace(
    "{verbs}", common.addr_verbs(_addr, ", ")
)
