"""`sq import <file>` — thin CLI wrapper over the bulk event-import engine
(:meth:`squads._services._import.ImportMixin.import_events`).

It reads the file (or stdin for ``-``) as text, hands it to the engine unchanged, renders the
returned :class:`~squads._services._results.ImportResult` as human text or ``--json`` and
picks the exit code; every validate/apply decision lives in the engine. The default ``at`` of
events that omit their own is the global ``--at``, not a local option: the root callback's
``_hoist_global_options`` routes a bare ``--at`` to the root command, so a local one could
never receive it.
"""

import json
from typing import Any

import typer

import squads._cli._common as common
from squads._cli import app
from squads._context import get_context
from squads._services._results import ImportApplyResult, ImportPlan, ImportResult


def _read_import_text(file: str) -> str:
    """The JSONL text for *file* (``-`` reads stdin)."""
    return common.read_client_text(file, what="import file")


def _plan_json(plan: ImportPlan) -> dict[str, Any]:
    return {
        "op_counts": dict(plan.op_counts.counts),
        "handle_to_id": dict(plan.handle_to_id),
        "handle_to_sub": {h: list(v) for h, v in plan.handle_to_sub.items()},
        "issues": [{"line": i.line, "message": i.message} for i in plan.issues],
    }


def _result_json(result: ImportResult, *, dry_run: bool) -> dict[str, Any]:
    """The ``--json`` envelope: the pre-pass plan plus, when applied, the real outcome.

    ``op_counts``/``handle_to_id``/``handle_to_sub`` come from the real apply once one happened;
    a dry run or a failed pre-pass reports the pre-pass's projected values, since nothing was
    applied. ``issues`` holds one of two fillings, because a run is refused or applied, never
    both: pre-pass refusals (``line``/``message``, nothing written) or every validator finding on
    a touched item, each with its ``level``. ``warnings`` holds the warn-level lines as the human
    output words them. ``ok`` is false when the pre-pass refused or an applied finding is
    error-level; a warn-only run stays ``ok``. ``applied`` stays true alongside an error-level
    finding, because the write happened.
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
            {"level": f.level, "item": f.item, "message": f.message, "rule": f.rule}
            for f in applied.findings
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
    """Exit 3 when an applied run's touched items carry an error-level finding.

    That is the code the integrity check uses for these findings, so the two doors agree. It is
    not exit 1, which means squads could not do what was asked; here the transaction committed
    and the write stands. ``applied`` is ``None`` for a dry run and after a pre-pass refusal,
    which gain no non-zero path from here.
    """
    if applied is not None and applied.error_findings:
        raise typer.Exit(3)


@app.command(name="import")
@common.command
async def import_events(
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
