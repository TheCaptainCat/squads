"""`sq board ...` — the team bulletin board: short, prescriptive broadcast notices.

Grammar:
  sq board post -m "<notice>" [--until DATE] [--as <slug>]  — post a notice
  sq board list [--json]                                    — current (unexpired) notices
  sq board clear <n>                                        — take the n-th listed notice down

Unlike `sq memory <role> ...`, the board is **team-scoped** — there is no positional role
subject; every command operates on the one shared board. A notice has no counter-allocated id
(see squads._board): `list`'s ordinal is a display affordance — the notice's entry-line
position in the live, sorted, unexpired listing — resolved fresh on every `list`/`clear` call,
never persisted or stable across posts/clears.
"""
# Commands registered via Typer decorators (side effects) read as unused to static analysis.
# pyright: reportUnusedFunction=false

import json

import typer

import squads._actor as actor
from squads._cli._common import (
    command,
    console,
    e,
    get_service,
    print_json_clean,
    resolve_body,
    resolve_slug_or_raise,
)

board_app = typer.Typer(
    no_args_is_help=True,
    help="The team bulletin board: broadcast notices with an optional expiry.",
)


@board_app.command("post")
@command
async def post_notice(
    message: list[str] = typer.Option(None, "-m", "--message", help="The notice text."),
    file: str | None = typer.Option(None, "--file", help="Notice body from a file ('-' = stdin)."),
    until: str | None = typer.Option(
        None, "--until", help="Expiry (ISO 8601 date/datetime); the notice hides once past."
    ),
    as_: str = typer.Option("operator", "--as", help="Author: a role slug or 'op-<slug>'."),
) -> None:
    """Post a notice to the board, visible to the whole team until it expires."""
    svc = get_service()
    slug = await resolve_slug_or_raise(as_, svc)
    actor.set_actor(slug)
    text = resolve_body(message or None, file)
    notice = await svc.board_post(slug, text, until=until)
    console.print(f"posted [bold]{e(notice.id)}[/bold] as {e(slug)}")


@board_app.command("list")
@command
async def list_notices(json_out: bool = typer.Option(False, "--json")) -> None:
    """List current (unexpired) notices with their positional ordinal."""
    svc = get_service()
    notices = await svc.board_list()
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
        return
    if not notices:
        console.print("[dim]no current notices[/dim]")
        return
    for i, n in enumerate(notices, start=1):
        until_part = f"  [dim]until {e(n.until)}[/dim]" if n.until else ""
        console.print(
            f"[bold]{i}.[/bold] {e(n.body)}  [dim]({e(n.author)} @ {e(n.posted_at)})[/dim]"
            f"{until_part}"
        )


@board_app.command("clear")
@command
async def clear_notice(
    n: int = typer.Argument(..., help="Positional ordinal from `sq board list`."),
) -> None:
    """Take down the n-th listed notice (resolved against the live listing)."""
    svc = get_service()
    notice = await svc.board_clear(n)
    console.print(f"cleared [bold]{e(notice.id)}[/bold]")
