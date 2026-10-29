"""`sq board ...` — the team bulletin board: short, prescriptive broadcast notices.

Grammar:
  sq board post -m "<notice>" [--until DATE] [--as <slug>]  — post a notice
  sq board list [--json]                                    — current (unexpired) notices
  sq board clear <n>                                        — take the n-th listed notice down

Unlike `sq memory <role> ...`, the board is team-scoped: no role subject, one shared board. A
notice has no counter-allocated id (see squads._board); `list`'s ordinal is its position in
the live, sorted, unexpired listing, resolved fresh on every `list`/`clear` and not stable
across posts or clears.
"""
# Commands registered via Typer decorators (side effects) read as unused to static analysis.
# pyright: reportUnusedFunction=false

import typer

import squads._cli._common as common
from squads._api import _ops as ops
from squads._api._dto._board import BoardClearRequest, BoardListRequest, BoardPostRequest
from squads._cli import _calls as calls
from squads._cli._common import console, handle_errors, require_as, resolve_body
from squads._cli._render._board import render_cleared, render_notices, render_posted

board_app = typer.Typer(
    no_args_is_help=True,
    help="Post, list and take down notices on the team board.",
)


@board_app.command("post")
@handle_errors
def post_notice(
    message: list[str] = common.message_option(),
    file: str | None = common.file_option(),
    until: str | None = typer.Option(
        None, "--until", help="ISO 8601 date or time after which the notice is hidden."
    ),
    as_: str | None = common.as_option(),
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: the notice posted."
    ),
) -> None:
    """Post a notice to the board, visible to the whole team until it expires."""
    common.declare_actor(require_as(as_))
    request = BoardPostRequest(body=resolve_body(message or None, file), until=until)
    response = calls.call(ops.BOARD_POST, request)
    if json_out:
        calls.print_json(ops.BOARD_POST, response)
    else:
        calls.print_warnings(response)
        render_posted(response.data, console)


@board_app.command("list")
@handle_errors
def list_notices(
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per notice."
    ),
) -> None:
    """List the notices that have not expired, numbered for `sq board clear`.

    Exit codes: 4 partial result; what could be read is printed. See sq docs faq.
    """
    response = calls.call(ops.BOARD_LIST, BoardListRequest())
    if json_out:
        calls.print_json(ops.BOARD_LIST, response)
    else:
        calls.print_warnings(response)
        render_notices(response.data, console)
    calls.finish(response, json_out=json_out)


@board_app.command("clear")
@handle_errors
def clear_notice(
    n: int = typer.Argument(..., help="The notice's number in `sq board list`."),
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: the notice as it was taken down."
    ),
) -> None:
    """Take down a notice by its number in the current listing."""
    response = calls.call(ops.BOARD_CLEAR, BoardClearRequest(n=n))
    if json_out:
        calls.print_json(ops.BOARD_CLEAR, response)
    else:
        calls.print_warnings(response)
        render_cleared(response.data, console)
