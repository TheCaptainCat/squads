"""`sq workflow` — workflow cheatsheet + spec validation surface (FEAT-000209 TASK-000242).

Sub-commands:
- ``sq workflow`` / ``sq workflow show``  — print the team cheatsheet (unchanged behaviour).
- ``sq workflow lint``                   — verbose collect-all-errors spec validation (AC #3 / US2).

``lint`` is the author-facing diagnostic: it runs the same checks that ``open_service`` runs
fail-closed (pure-spec validation + live-index cross-check), but prints EVERY error and
warning with the offending config key and a fix hint instead of aborting on the first problem.
Exit code 0 on a clean spec, 1 when any error is present.

Design: ``lint`` calls ``lint_workflow_spec`` directly — it does NOT go through
``open_service``.  This is intentional: a spec that causes ``open_service`` to hard-stop (e.g.
it drops a status still in use) is precisely what an author runs ``sq workflow lint`` to
diagnose.  Bypassing ``open_service`` means lint is never self-blocked by the same check it is
trying to report.
"""

import typer
from rich.markdown import Markdown
from rich.table import Table

from squads._cli._common import console, e, handle_errors
from squads._errors import SquadsError

workflow_app = typer.Typer(
    no_args_is_help=False,
    invoke_without_command=True,
    help=(
        "Workflow cheatsheet and spec validation.\n\n"
        "Run `sq workflow` (or `sq workflow show`) for the team cheatsheet. "
        "Run `sq workflow lint` to validate your workflow override spec."
    ),
)


# ─── show (default — bare `sq workflow`) ───────────────────────────────────────


@workflow_app.callback()
def workflow_default(ctx: typer.Context) -> None:
    """Print the team workflow cheatsheet when no sub-command is given."""
    if ctx.invoked_subcommand is None:
        _print_cheatsheet()


@workflow_app.command("show")
def workflow_show() -> None:
    """Print the team workflow cheatsheet (who writes what, how items link)."""
    _print_cheatsheet()


def _print_cheatsheet() -> None:
    from squads._cli._common import get_active_spec
    from squads._rendering._engine import render

    console.print(Markdown(render("workflow.md.j2", spec=get_active_spec())))


# ─── lint ─────────────────────────────────────────────────────────────────────


@workflow_app.command("lint")
@handle_errors
def workflow_lint() -> None:
    """Validate the workflow override spec — collect ALL errors and exit 0/1.

    Prints every error with the offending config key and a fix hint.
    Exits 0 with "workflow spec OK" on a clean spec; exits 1 when any error is
    present.  Warnings alone (if any) still exit 0.

    This command intentionally does NOT go through ``open_service``, so it can
    diagnose a spec that would cause normal commands to hard-stop (AC #5 / US2).
    """
    import squads._cli._common as _common
    from squads._paths import resolve
    from squads._workflow._loader import WORKFLOW_OVERRIDE_FILENAME, lint_workflow_spec

    try:
        sp = resolve(_common._active_dir)  # pyright: ignore[reportPrivateUsage]
    except SquadsError as exc:
        console.print(f"[red]error[/red]: {e(str(exc))}")
        raise typer.Exit(1) from exc

    squad_dir = sp.squad_dir
    override_path = squad_dir / WORKFLOW_OVERRIDE_FILENAME

    if not override_path.is_file():
        console.print(
            "[green]workflow spec OK[/green] — no override file found; using the bundled default."
        )
        return

    findings = lint_workflow_spec(squad_dir)

    errors = [f for f in findings if f[0] == "error"]
    warnings = [f for f in findings if f[0] == "warn"]

    if not findings:
        console.print("[green]workflow spec OK[/green] — no errors or warnings.")
        return

    # Print errors.
    if errors:
        table = Table(title="workflow spec errors", show_header=True, header_style="red")
        table.add_column("location", style="dim")
        table.add_column("error")
        table.add_column("fix hint", style="dim")
        for _level, location, message, fix_hint in errors:
            table.add_row(e(location), e(message), e(fix_hint))
        console.print(table)

    # Print warnings.
    if warnings:
        table = Table(title="workflow spec warnings", show_header=True, header_style="yellow")
        table.add_column("location", style="dim")
        table.add_column("warning")
        table.add_column("fix hint", style="dim")
        for _level, location, message, fix_hint in warnings:
            table.add_row(e(location), e(message), e(fix_hint))
        console.print(table)

    if errors:
        console.print(
            f"[red]{len(errors)} error(s)[/red]"
            + (f", {len(warnings)} warning(s)" if warnings else "")
            + " — fix the errors above then re-run `sq workflow lint`."
        )
        raise typer.Exit(1)
    else:
        # Warnings only — exit 0.
        console.print(f"[green]workflow spec OK[/green] — {len(warnings)} warning(s); no errors.")
