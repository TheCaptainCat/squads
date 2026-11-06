"""`sq source ...` — the trackers a squad pulls issues from.

Grammar:
  sq source list [--json]                        — the declared sources and their state
  sq source check [<source>] [--json]            — probe each source; exit 1 on a blocking failure
  sq source pull [<source>] [--dry-run] [--full] [--json] — pull the issues of a source
  sq source credential set <source> [--json]     — store the credential of a source
  sq source credential remove <source> [--json]  — delete it

A credential is asked for on a hidden prompt, or read from a piped standard input, and is stored
where the squad is served, never in the squad.
"""
# Commands registered via Typer decorators (side effects) read as unused to static analysis.
# pyright: reportUnusedFunction=false

import typer

from squads._api import (
    CredentialFieldsRequest,
    CredentialRemoveRequest,
    CredentialSetRequest,
    SourceCheckRequest,
    SourceListRequest,
    SourcePullRequest,
    ops,
)
from squads._cli import _calls as calls
from squads._cli._common import console, handle_errors, prompt_secret
from squads._cli._render import (
    render_checked,
    render_credential_removed,
    render_credential_written,
    render_listed,
    render_pulled,
)

source_app = typer.Typer(
    no_args_is_help=True,
    help="Manage the trackers this squad pulls issues from.",
)

_credential_app = typer.Typer(
    no_args_is_help=True,
    help="Store and delete the credential of a source.",
)
source_app.add_typer(_credential_app, name="credential")


@_credential_app.command("set")
@handle_errors
def set_credential(
    source: str = typer.Argument(..., help="Name of the source, as declared in `sources.toml`."),
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: where the credential was stored."
    ),
) -> None:
    """Store the credential of a source, asking for each value without echo.

    The value is read from a hidden prompt, or from standard input when
    that is not a terminal, one line per value. It is kept in the
    credentials file of the user that serves the squad and never shown.
    """
    asked = calls.call(ops.SOURCE_CREDENTIAL_FIELDS, CredentialFieldsRequest(source=source))
    values = {field: prompt_secret(f"{source} {field}") for field in asked.data.fields}
    response = calls.call(
        ops.SOURCE_CREDENTIAL_SET, CredentialSetRequest(source=source, values=values)
    )
    if json_out:
        calls.print_json(ops.SOURCE_CREDENTIAL_SET, response)
        return
    calls.print_warnings(response)
    render_credential_written(response.data, console)


@_credential_app.command("remove")
@handle_errors
def remove_credential(
    source: str = typer.Argument(..., help="Name of the source, as declared in `sources.toml`."),
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: whether a credential was removed."
    ),
) -> None:
    """Delete the stored credential of a source."""
    response = calls.call(ops.SOURCE_CREDENTIAL_REMOVE, CredentialRemoveRequest(source=source))
    if json_out:
        calls.print_json(ops.SOURCE_CREDENTIAL_REMOVE, response)
        return
    calls.print_warnings(response)
    render_credential_removed(response.data, console)


@source_app.command("pull")
@handle_errors
def pull(
    source: str | None = typer.Argument(
        None, help="Name of the source to pull; every enabled source when omitted."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Check what the pull would write, and write nothing."
    ),
    full: bool = typer.Option(
        False,
        "--full",
        help="Read every held issue the source selects in detail, not only the changed ones, "
        "and apply the status map to it.",
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: each source's counts and report lines."
    ),
) -> None:
    """Pull the issues a source opts in, as items the tracker owns.

    Each issue becomes an item whose title, description, mapped fields and
    comments follow the tracker; a second pull writes only what changed.
    """
    response = calls.call(
        ops.SOURCE_PULL, SourcePullRequest(name=source, dry_run=dry_run, full=full)
    )
    if json_out:
        calls.print_json(ops.SOURCE_PULL, response)
    else:
        calls.print_warnings(response)
        render_pulled(response.data, console)
    if any(report.failed for report in response.data.sources):
        raise typer.Exit(1)


@source_app.command("list")
@handle_errors
def list_sources(
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: each declared source and its state."
    ),
) -> None:
    """List the declared sources and their state.

    Each row shows the connector, whether the source is enabled, whether
    a credential is stored (never its value) and how many items it holds.
    """
    response = calls.call(ops.SOURCE_LIST, SourceListRequest())
    if json_out:
        calls.print_json(ops.SOURCE_LIST, response)
        return
    calls.print_warnings(response)
    render_listed(response.data, console)


@source_app.command("check")
@handle_errors
def check(
    source: str | None = typer.Argument(
        None, help="Name of the source to check; every declared source when omitted."
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: each source's checklist."
    ),
) -> None:
    """Probe each source and print a checklist, disabled ones included.

    The probes run where the squad is served, with the credential the pull
    reads: access first, then every value the maps name, then what no map
    covers. Each failure is followed by its fix; the exit code is 1 when any
    probe fails, and warnings leave it at 0.
    """
    response = calls.call(ops.SOURCE_CHECK, SourceCheckRequest(name=source))
    if json_out:
        calls.print_json(ops.SOURCE_CHECK, response)
    else:
        calls.print_warnings(response)
        render_checked(response.data, console)
    if not response.data.ok:
        raise typer.Exit(1)
