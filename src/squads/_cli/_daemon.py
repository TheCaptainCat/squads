"""`sq daemon ...` — the long-lived process that serves a squad over HTTP.

Grammar:
  sq daemon status [--json]   — who is running for this squad, or that none is
  sq daemon stop [--json]     — ask it to exit and wait until its files are gone
  sq daemon run               — (hidden) serve in this process until stopped or idle

The group talks to the daemon itself and never goes through one.
"""
# Commands registered via Typer decorators (side effects) read as unused to static analysis.
# pyright: reportUnusedFunction=false

import json

import typer

import squads._cli._common as common
from squads._context import get_context
from squads._daemon_link import ask_to_stop, daemon_identity, wait_until_gone
from squads._endpoint import Endpoint, endpoint_for
from squads._errors import NotInitializedError, SquadsError
from squads._paths import process_dir

daemon_app = typer.Typer(
    no_args_is_help=True,
    help="See and stop the daemon that serves this squad.",
)

#: Seconds `sq daemon stop` waits for the daemon's files to go.
STOP_WAIT = 15.0


def _endpoint() -> Endpoint:
    """The endpoint of the squad this command addresses."""
    start = get_context().client_cwd or process_dir()
    endpoint = endpoint_for(start)
    if endpoint is None:
        raise NotInitializedError(start)
    return endpoint


def _print_json(document: dict[str, object]) -> None:
    common.print_json_clean(json.dumps(document))


@daemon_app.command("status")
@common.handle_errors
def status(
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: whether a daemon runs and who it is."
    ),
) -> None:
    """Show the daemon serving this squad, or that none is running."""
    identity = daemon_identity(_endpoint())
    if json_out:
        _print_json({"running": identity is not None, "daemon": identity})
        return
    if identity is None:
        common.console.print("no daemon is running for this squad")
        return
    out = common.console
    out.print(f"daemon running (pid {identity['pid']})")
    for label, key in (
        ("version", "version"),
        ("squad", "squad_dir"),
        ("started", "started_at"),
        ("exits idle at", "idle_deadline"),
    ):
        out.print(f"  {label}: {common.e(identity.get(key) or 'never')}", soft_wrap=True)
    for listener in identity["listeners"]:
        out.print(
            f"  listening: {common.e(listener['address'])} ({listener['transport']}, "
            f"{listener['kind']})",
            soft_wrap=True,
        )
    out.print(f"  vocabulary: {common.e(identity['vocabulary']['hash'])}", soft_wrap=True)


@daemon_app.command("stop")
@common.handle_errors
def stop(
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: whether a daemon was running."
    ),
) -> None:
    """Stop the daemon serving this squad, and wait until it is gone.

    With none running it does nothing and exits 0. The next command
    starts a fresh daemon.
    """
    endpoint = _endpoint()
    was_running = daemon_identity(endpoint) is not None
    if was_running:
        if not ask_to_stop(endpoint):
            raise SquadsError("the daemon did not accept the request to stop")
        if not wait_until_gone(endpoint, STOP_WAIT):
            raise SquadsError(f"the daemon is still running after {STOP_WAIT:g} seconds")
    if json_out:
        _print_json({"was_running": was_running})
    elif was_running:
        common.console.print("daemon stopped")
    else:
        common.console.print("no daemon is running for this squad")


@daemon_app.command("run", hidden=True)
def run(
    report_fd: int | None = typer.Option(
        None, "--report-fd", hidden=True, help="The pipe the start report goes to."
    ),
) -> None:
    """Serve this squad in this process until it is stopped, retired or idle."""
    from squads._daemon._lifecycle import run_daemon

    try:
        endpoint = _endpoint()
    except SquadsError as exc:
        common.err_console.print(f"[red]error:[/red] {common.e(exc)}", soft_wrap=True)
        raise typer.Exit(1) from None
    code, failure = run_daemon(endpoint, report_fd)
    if failure is not None:
        common.err_console.print(f"[red]error:[/red] {common.e(failure)}", soft_wrap=True)
    raise typer.Exit(code)
