"""`sq import <file>` — thin CLI wrapper over the bulk event-import engine
(:meth:`squads._services._import.ImportMixin.import_events`).

This module reads the file (or stdin for ``-``) as text and hands it to the engine
unchanged — every validate/apply decision lives there (the pre-pass/apply tasks). This module
only turns the returned :class:`~squads._services._results.ImportResult` into a human or
``--json`` rendering and picks the process exit code; it recomputes nothing.

The file-level ``at`` default events inherit when they omit their own is the existing global
``--at`` (``sq --at <when> import file.jsonl``) — the same clock-forging flag every other
command already shares — rather than a second, locally-scoped ``--at``: the root callback's
arg-hoisting (``_hoist_global_options``) always routes a bare ``--at`` token to the root
command, so a subcommand-local option of the same name could never actually receive it.
"""

import json
import sys
from pathlib import Path
from typing import Any

import typer

import squads._cli._common as common
from squads._cli import app
from squads._context import get_context
from squads._errors import SquadsError
from squads._services._results import ImportApplyResult, ImportPlan, ImportResult


def _read_import_text(file: str) -> str:
    """The JSONL text for *file* (``-`` reads stdin)."""
    if file == "-":
        return sys.stdin.read()
    try:
        return Path(file).read_text(encoding="utf-8")
    except OSError as exc:
        raise SquadsError(f"cannot read import file {file!r}: {exc.strerror or exc}") from exc


def _plan_json(plan: ImportPlan) -> dict[str, Any]:
    return {
        "op_counts": dict(plan.op_counts.counts),
        "handle_to_id": dict(plan.handle_to_id),
        "handle_to_sub": {h: list(v) for h, v in plan.handle_to_sub.items()},
        "issues": [{"line": i.line, "message": i.message} for i in plan.issues],
    }


def _result_json(result: ImportResult, *, dry_run: bool) -> dict[str, Any]:
    """The ``--json`` envelope: the pre-pass plan plus (when applied) the real outcome.

    ``op_counts``/``handle_to_id``/``handle_to_sub`` reflect the real apply once one
    happened (the projected pre-pass values are simulated against a throwaway copy and are
    superseded); a dry run or a failed pre-pass reports the pre-pass's own (projected/partial)
    values instead, since nothing was applied.

    ``issues`` is one list with two mutually exclusive fillings, because a run is either
    refused or applied and never both: pre-pass refusals (``line``/``message``, nothing
    written) or, once the events were applied, every validator finding on a touched item
    carrying its own ``level``. ``warnings`` holds the warn-level lines in the human wording,
    unchanged. ``ok`` is false when the pre-pass refused the file or an applied finding is
    error-level — a warn-only run fills ``issues`` and stays ``ok``. ``applied`` says which of
    the two a caller is looking at, and stays **true** alongside an error-level finding,
    because the write did happen.
    """
    payload = _plan_json(result.plan)
    applied = result.applied
    payload["ok"] = result.plan.ok
    payload["applied"] = applied is not None
    payload["dry_run"] = dry_run
    payload["created_ids"] = list(applied.created_ids) if applied else []
    payload["warnings"] = list(applied.warnings) if applied else []
    if applied is not None:
        payload["op_counts"] = dict(applied.op_counts.counts)
        payload["handle_to_id"] = dict(applied.handle_to_id)
        payload["handle_to_sub"] = {h: list(v) for h, v in applied.handle_to_sub.items()}
        payload["issues"] = [
            {"level": f.level, "item": f.item, "message": f.message} for f in applied.findings
        ]
        payload["ok"] = not applied.error_findings
    return payload


def _print_issues(plan: ImportPlan) -> None:
    """Every collected pre-pass problem, line-numbered and in order — never a stack trace."""
    for issue in plan.issues:
        common.err_console.print(
            f"[red]line {issue.line}:[/red] {common.e(issue.message)}", soft_wrap=True
        )
    common.err_console.print(f"[red]{len(plan.issues)} issue(s) found — nothing written.[/red]")


def _print_op_counts(plan: ImportPlan) -> None:
    for op, count in plan.op_counts.counts.items():
        common.console.print(f"  {common.e(op)}: {count}")


def _print_handle_plan(plan: ImportPlan) -> None:
    if not plan.handle_to_id and not plan.handle_to_sub:
        return
    common.console.print("[bold]handles:[/bold]")
    for handle, item_id in plan.handle_to_id.items():
        common.console.print(f"  {common.e(handle)} -> {common.e(item_id)}")
    for handle, (parent_id, local_id) in plan.handle_to_sub.items():
        common.console.print(f"  {common.e(handle)} -> {common.e(parent_id)} {common.e(local_id)}")


def _print_applied(applied: ImportApplyResult) -> None:
    """The applied run's findings, error-level first and prefixed by their level the way the
    integrity check prefixes its own, then the count. Both levels are printed here: a reader
    has to be able to tell, from this output alone, which lines a gated door would have
    refused."""
    for finding in applied.error_findings:
        common.console.print(
            f"[red]error:[/red] {common.e(finding.item)}: {common.e(finding.message)}",
            soft_wrap=True,
        )
    for warning in applied.warnings:
        common.console.print(f"[yellow]warning:[/yellow] {common.e(warning)}", soft_wrap=True)
    total = sum(applied.op_counts.counts.values())
    common.console.print(f"[green]imported[/green] {total} event(s)")


def _exit_on_error_findings(applied: ImportApplyResult | None) -> None:
    """Exit 3 when an applied run's touched items carry an error-level finding — the code the
    integrity check already uses for exactly these findings, so the two doors agree.

    Deliberately *not* exit 1: 1 means squads could not do what was asked, which on this door
    would say nothing was written. Here the transaction committed and the write stands, so the
    only honest non-zero is the one that means "reported, not refused". ``applied`` is ``None``
    for a dry run (nothing written, no touched corpus to report on) and after a pre-pass
    refusal, and neither gains a non-zero path from here.
    """
    if applied is not None and applied.error_findings:
        raise typer.Exit(3)


@app.command(name="import")
@common.command
async def import_events(
    file: str = typer.Argument(..., help="JSONL event file to import ('-' reads stdin)."),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Validate only; write nothing; print the projected handle -> id plan.",
    ),
    as_: str | None = typer.Option(
        None,
        "--as",
        help="Default acting slug events inherit when they omit their own. No fallback: an "
        "event with no 'as' of its own, no prior event's, and no --as fails validation.",
    ),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Bulk-import a JSONL event stream in one process.

    Every event is validated first — type/status vocabulary, transition legality, actor
    registration, marker-safety — collecting ALL problems before writing anything; only a
    fully clean file is applied, in one transaction. On any validation error, nothing is
    written and every problem is listed with its line number.

    Prefix with the global ``--at`` to set the file-level default timestamp events without
    their own ``at`` inherit, e.g. ``sq --at 2024-01-15T09:00:00Z import history.jsonl``;
    omit it and an event without its own ``at`` (and no prior event's ``at`` to inherit)
    uses "now". ``--dry-run`` stops after validation and prints the projected plan instead
    of applying.

    Attribution has no equivalent silent fallback: an event without its own ``as``, with no
    prior event's to inherit, and no ``--as`` given fails validation naming the missing actor,
    rather than attributing to whatever role this squad happens to be configured to default to.

    Exit codes: 0 when the events applied cleanly, 1 when the pre-pass refused the file and
    nothing was written, 3 when the events were applied and the integrity catalog reported an
    error-level issue on an item this import touched — the same 3 ``sq check`` uses for the same
    findings. Warn-level findings alone still exit 0, and ``--dry-run`` writes nothing, so it
    never exits 3.

    Exit 3 from this command means applied-and-flagged. The events are on disk. A retry loop
    keyed on "non-zero means nothing happened" will replay them; branch on ``--json``'s
    ``applied`` instead, which is true at exit 3 and false at exit 1.
    """
    text = _read_import_text(file)
    svc = common.get_service()
    default_at = get_context().clock_override
    result = await svc.import_events(text, default_at=default_at, default_as=as_, dry_run=dry_run)

    if json_out:
        common.print_json_clean(json.dumps(_result_json(result, dry_run=dry_run)))
        if not result.plan.ok:
            raise typer.Exit(1)
        _exit_on_error_findings(result.applied)
        return

    if not result.plan.ok:
        _print_issues(result.plan)
        raise typer.Exit(1)

    _print_op_counts(result.plan)
    _print_handle_plan(result.plan)
    if result.applied is None:
        common.console.print("[dim]dry run — nothing written[/dim]")
        return
    _print_applied(result.applied)
    _exit_on_error_findings(result.applied)
