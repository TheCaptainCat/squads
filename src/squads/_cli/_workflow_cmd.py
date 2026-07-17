"""`sq workflow` — workflow cheatsheet + spec validation surface.

Sub-commands:
- ``sq workflow`` / ``sq workflow show``  — print the team cheatsheet.
- ``sq workflow lint``                   — verbose collect-all-errors spec validation.

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

import json
import math
from typing import TYPE_CHECKING

import typer
from rich.markdown import Markdown
from rich.table import Table

from squads._cli._common import console, e, handle_errors
from squads._errors import SquadsError

if TYPE_CHECKING:
    from squads._workflow._models import WorkflowSpec

workflow_app = typer.Typer(
    no_args_is_help=False,
    invoke_without_command=True,
    help=(
        "Workflow cheatsheet and spec validation.\n\n"
        "Run `sq workflow` (or `sq workflow show`) for the team cheatsheet. "
        "Run `sq workflow lint` to validate your workflow override spec. "
        "Run `sq workflow types` for the machine-readable type catalog."
    ),
)


# ─── show (default — bare `sq workflow`) ───────────────────────────────────────


_RAW_HELP = "Plain markdown output (opt out of Rich markdown render)."


@workflow_app.callback()
def workflow_default(
    ctx: typer.Context,
    raw: bool = typer.Option(False, "--raw", help=_RAW_HELP),
) -> None:
    """Print the team workflow cheatsheet when no sub-command is given."""
    if ctx.invoked_subcommand is None:
        _print_cheatsheet(raw=raw)


@workflow_app.command("show")
def workflow_show(raw: bool = typer.Option(False, "--raw", help=_RAW_HELP)) -> None:
    """Print the team workflow cheatsheet (who writes what, how items link)."""
    _print_cheatsheet(raw=raw)


def _print_cheatsheet(*, raw: bool) -> None:
    """Render the cheatsheet — Rich markdown by default, clean markdown text with ``--raw``.

    ``--raw`` prints the ``workflow.md.j2`` render verbatim (markdown tables + fenced
    ```mermaid``` blocks, no box-drawing/ANSI), mirroring the ``sq show --raw`` / ``sq docs``
    precedent: opt out of ``rich.Markdown`` rendering, print the source text as-is.
    """
    from squads._cli._common import get_active_spec
    from squads._rendering._engine import render

    content = render("workflow.md.j2", spec=get_active_spec())
    if raw:
        console.print(content, markup=False, highlight=False, soft_wrap=True)
    else:
        console.print(Markdown(content))


# ─── types ────────────────────────────────────────────────────────────────────

#: Frozen field set for the ``sq workflow types --json`` catalog. Kept as a module-level
#: tuple so a test can assert the CLI never drifts from the declared contract.
TYPE_CATALOG_FIELDS: tuple[str, str, str, str] = ("type", "order", "prefix", "reserved")


def _type_catalog(spec: WorkflowSpec) -> list[dict[str, object]]:
    """The frozen type-catalog rows, ascending resolved ``order`` (type-name string
    tiebreak — the same ordering the CLI uses to register per-type commands).

    Includes every declared type (work AND reserved: role/skill/operator). ``order`` is
    ``None`` when ``ItemSpec.order`` is unset (``+inf``) — present-but-null, never
    omitted, so the key set stays stable across every row.
    """
    types = sorted(spec.items, key=lambda t: (spec.items[t].order, t))
    return [
        {
            "type": t,
            "order": None if math.isinf(spec.items[t].order) else spec.items[t].order,
            "prefix": spec.items[t].prefix,
            "reserved": spec.items[t].is_meta,
        }
        for t in types
    ]


@workflow_app.command("types")
@handle_errors
def workflow_types(
    json_out: bool = typer.Option(False, "--json", help="Emit the machine type catalog."),
) -> None:
    """List every declared type in the active workflow spec.

    Default: a human Rich table. ``--json`` emits a bare JSON array — one object per
    declared type (work AND reserved), in ascending resolved ``order`` (type-name
    string breaks ties): ``{type, order, prefix, reserved}``. ``order`` is ``null``
    when the type has no explicit order (``+inf``) — present, never omitted, so the
    key set is stable across every object.
    """
    from squads._cli._common import get_active_spec, print_json_clean

    spec = get_active_spec()
    rows = _type_catalog(spec)

    if json_out:
        print_json_clean(json.dumps(rows))
        return

    table = Table(box=None, pad_edge=False)
    for col in ("Type", "Order", "Prefix", "Reserved"):
        table.add_column(col)
    for row in rows:
        table.add_row(
            e(str(row["type"])),
            "" if row["order"] is None else str(row["order"]),
            e(str(row["prefix"])),
            "yes" if row["reserved"] else "",
        )
    console.print(table)


# ─── lint ─────────────────────────────────────────────────────────────────────


@workflow_app.command("lint")
@handle_errors
def workflow_lint() -> None:
    """Validate the workflow override spec — collect ALL errors and exit 0/1.

    Prints every error with the offending config key and a fix hint.
    Exits 0 with "workflow spec OK" on a clean spec; exits 1 when any error is
    present.  Warnings alone (if any) still exit 0.

    This command intentionally does NOT go through ``open_service``, so it can
    diagnose a spec that would cause normal commands to hard-stop.
    """
    import squads._cli._common as common
    from squads._paths import resolve
    from squads._workflow._loader import WORKFLOW_OVERRIDE_FILENAME, lint_workflow_spec

    try:
        sp = resolve(common._active_dir)  # pyright: ignore[reportPrivateUsage]
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
