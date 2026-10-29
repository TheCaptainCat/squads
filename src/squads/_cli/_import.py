"""`sq import <file>` — thin CLI wrapper over the bulk event-import operation.

It reads the file (or stdin for ``-``) as text, sends it in the request unchanged, renders the
returned report as human text or ``--json`` and picks the exit code; every validate/apply
decision lives in the operation. The default ``at`` of events that omit their own is the global
``--at``, not a local option: the root callback's ``_hoist_global_options`` routes a bare
``--at`` to the root command, so a local one could never receive it.
"""

import typer

import squads._cli._common as common
from squads._api import _ops as ops
from squads._api._dto._squad import ImportRequest
from squads._cli import _calls as calls
from squads._cli import app
from squads._cli._render._squad import render_import, render_import_refusal


@app.command(name="import")
@common.handle_errors
def import_events(
    file: str = typer.Argument(..., help="JSONL event file to import; `-` reads stdin."),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Check the file and print the plan of IDs it would create; write nothing.",
    ),
    as_: str | None = common.as_option(
        "Slug to attribute events with no `as` of their own and none to inherit; "
        "without it such an event is refused."
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: the plan and, once applied, the outcome."
    ),
) -> None:
    """Apply a JSONL file of events to the squad in one transaction.

    Every event is checked first, and every problem is listed with its line
    number; only a fully clean file is applied, so a refused file writes nothing.
    The global `--at` sets the time for events with no `at` of their own, as in
    `sq --at 2024-01-15T09:00:00Z import history.jsonl`; without it they get now.

    Exit codes: 3 applied, with error-level issues found. See sq docs faq.
    Exit 3 means the events are on disk: do not retry on a non-zero exit; read
    `applied` from `--json` instead.
    """
    text = common.read_client_text(file, what="import file")
    request = ImportRequest(text=text, dry_run=dry_run, default_as=as_)
    response = calls.call(ops.IMPORT, request)
    report = response.data
    if json_out:
        calls.print_json(ops.IMPORT, response)
    else:
        calls.print_warnings(response)
        if not report.applied and not report.ok:
            render_import_refusal(report, common.err_console)
        else:
            render_import(report, common.console)
    # A refused file wrote nothing (exit 1); an applied one with an error-level finding is on
    # disk, so it exits 3 as `sq check` does for those findings, not 1.
    if not report.ok:
        raise typer.Exit(3 if report.applied else 1)
