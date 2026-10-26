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

import json

import typer

import squads._actor as actor
import squads._cli._common as common
from squads._cli._common import (
    command,
    console,
    e,
    get_service,
    print_json_clean,
    report_omissions,
    require_as,
    resolve_actor_or_raise,
    resolve_body,
)

board_app = typer.Typer(
    no_args_is_help=True,
    help="Post, list and take down notices on the team board.",
)


@board_app.command("post")
@command
async def post_notice(
    message: list[str] = common.message_option(),
    file: str | None = common.file_option(),
    until: str | None = typer.Option(
        None, "--until", help="ISO 8601 date or time after which the notice is hidden."
    ),
    as_: str | None = common.as_option(),
) -> None:
    """Post a notice to the board, visible to the whole team until it expires."""
    svc = get_service()
    slug = await resolve_actor_or_raise(require_as(as_), svc)
    actor.set_actor(slug)
    text = resolve_body(message or None, file)
    notice = await svc.board_post(slug, text, until=until)
    console.print(f"posted [bold]{e(notice.id)}[/bold] as {e(slug)}")


@board_app.command("list")
@command
async def list_notices(
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per notice."
    ),
) -> None:
    """List the notices that have not expired, numbered for `sq board clear`.

    Exit codes: 4 partial result; what could be read is printed. See sq docs faq.
    """
    svc = get_service()
    notices, unreadable = await svc.board_list()
    if json_out:
        print_json_clean(
            json.dumps(
                [
                    {
                        "n": i,
                        "id": n.id,
                        "author": n.author,
                        "posted_at": n.posted_at,
                        "until": n.until,
                        "body": n.body,
                    }
                    for i, n in enumerate(notices, start=1)
                ]
            )
        )
        report_omissions(unreadable, json_out=True)
        return
    if not notices:
        console.print("[dim]no current notices[/dim]")
    else:
        for i, n in enumerate(notices, start=1):
            until_part = f"  [dim]until {e(n.until)}[/dim]" if n.until else ""
            console.print(
                f"[bold]{i}.[/bold] {e(n.body)}  [dim]({e(n.author)} @ {e(n.posted_at)})[/dim]"
                f"{until_part}"
            )
    report_omissions(unreadable, json_out=False)


@board_app.command("clear")
@command
async def clear_notice(
    n: int = typer.Argument(..., help="The notice's number in `sq board list`."),
) -> None:
    """Take down a notice by its number in the current listing."""
    svc = get_service()
    notice = await svc.board_clear(n)
    console.print(f"cleared [bold]{e(notice.id)}[/bold]")
