"""`sq override` — manage project-level template and role overrides (ADR-000085).

The command group joins the 1.0 durable contract; the four subcommands are the complete
override-management surface:

- ``sq override scaffold <name>`` — copy a bundled template into ``.overrides/`` with stamp.
- ``sq override list``            — show all overrides with kind, base, and state.
- ``sq override diff [<name>]``   — two-delta view (Δ-mine + Δ-upgrade) for drifted overrides.
- ``sq override update [<name>]`` — re-stamp after a hand-merge; body untouched.

``list`` and ``diff`` support ``--json`` for machine-readable output.
"""

import json

import typer
from rich.table import Table

from squads._cli._common import console, e, get_service, handle_errors, print_json_clean
from squads._overrides._service import (
    STATE_BROKEN,
    STATE_CURRENT,
    STATE_DRIFTED,
    DiffResult,
    diff_override,
    scaffold_role,
    scaffold_template,
    scan_overrides,
    update_stamp,
)

override_app = typer.Typer(
    no_args_is_help=True,
    help=(
        "Manage project-level template and role overrides (.overrides/).\n\n"
        "Overrides are user-owned: scaffold starts from the bundled default, "
        "diff shows what changed (both your edits and what the upgrade changed), "
        "you merge by hand, then update re-stamps to clear the drift warning."
    ),
)


# ─── scaffold ──────────────────────────────────────────────────────────────────


@override_app.command("scaffold")
@handle_errors
def scaffold(
    name: str | None = typer.Argument(
        None, help="Bundled template name (e.g. 'items/task.md.j2', 'agents/role.md.j2')."
    ),
    role: str | None = typer.Option(
        None, "--role", help="Role slug to scaffold a TOML override for (e.g. architect)."
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing override."),
):
    """Copy a bundled template (or role) into .overrides/ as a starting point.

    The scaffolded file carries the ``squads:override-base:<version>`` stamp so sq check
    knows which bundled version the override was branched from.

    This is the only command that writes override bodies.  After scaffolding, edit the
    file directly to customise it, then verify with ``sq override diff``.
    """
    svc = get_service()
    squad_dir = svc.paths.squad_dir

    if role is not None:
        dest = scaffold_role(squad_dir, slug=role, force=force)
        console.print(
            f"[green]scaffolded[/green] role override: [bold]{e(str(dest))}[/bold]\n"
            f"Edit [cyan]{e(str(dest))}[/cyan] to add fields to override "
            f"(e.g. full_name, model), then verify with "
            f"[cyan]sq override diff --role {e(role)}[/cyan]."
        )
        return

    if name is None:
        raise typer.BadParameter(
            "provide a template name (e.g. 'items/task.md.j2') "
            "or --role <slug> to scaffold a role override"
        )

    dest = scaffold_template(squad_dir, template_name=name, force=force)
    console.print(
        f"[green]scaffolded[/green] template override: [bold]{e(str(dest))}[/bold]\n"
        f"Edit [cyan]{e(str(dest))}[/cyan], then verify with "
        f"[cyan]sq override diff {e(name)}[/cyan]."
    )


# ─── list ──────────────────────────────────────────────────────────────────────


@override_app.command(name="list")
@handle_errors
def list_overrides(
    json_out: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """List every present override with its kind, base version, and drift state.

    State legend: ``current`` = up to date; ``drifted`` = bundled counterpart changed
    since the base stamp; ``broken`` = missing required sq markers (error in sq check).

    ``--json`` emits an array of {name, kind, base_version, state} objects.
    """
    svc = get_service()
    entries = scan_overrides(svc.paths.squad_dir)

    if json_out:
        print_json_clean(
            json.dumps(
                [
                    {
                        "name": entry.name,
                        "kind": entry.kind,
                        "base_version": entry.base_version,
                        "state": entry.state,
                    }
                    for entry in entries
                ]
            )
        )
        return

    if not entries:
        console.print(
            "[dim]no overrides found under .overrides/[/dim]\n"
            "Run [cyan]sq override scaffold <template_name>[/cyan] to start one."
        )
        return

    table = Table(box=None, pad_edge=False)
    for col in ("Name", "Kind", "Base Version", "State"):
        table.add_column(col)

    for entry in entries:
        state_color = _state_color(entry.state)
        table.add_row(
            e(entry.name),
            entry.kind,
            e(entry.base_version or "(unstamped)"),
            f"[{state_color}]{entry.state}[/{state_color}]",
        )
    console.print(table)


def _state_color(state: str) -> str:
    if state == STATE_CURRENT:
        return "green"
    if state == STATE_DRIFTED:
        return "yellow"
    if state == STATE_BROKEN:
        return "red"
    return "white"


# ─── diff ──────────────────────────────────────────────────────────────────────


@override_app.command("diff")
@handle_errors
def diff(
    name: str | None = typer.Argument(
        None, help="Template name or role slug. Omit to diff all drifted overrides."
    ),
    role: str | None = typer.Option(None, "--role", help="Diff a role TOML override by slug."),
    json_out: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """Show two diffs for an override: your edits AND what the upgrade changed.

    Δ-mine:    your override vs the current bundled template (your customisation).
    Δ-upgrade: the base-version bundled template vs current bundled (what upgraded).

    Read Δ-upgrade to see what required markers or context variables were added since
    you last reconciled.  Merge them into your override by hand, then run
    ``sq override update <name>`` to re-stamp and clear the drift warning.

    With no name/--role, diffs every drifted override.
    ``--json`` emits an array of {name, kind, base_version, base_available, delta_mine,
    delta_upgrade}.
    """
    svc = get_service()
    squad_dir = svc.paths.squad_dir

    results: list[DiffResult] = []

    if role is not None:
        results.append(diff_override(squad_dir, name=role, kind="role"))
    elif name is not None:
        results.append(diff_override(squad_dir, name=name, kind="template"))
    else:
        # No name: diff every drifted override.
        entries = scan_overrides(squad_dir)
        drifted = [e for e in entries if e.state == STATE_DRIFTED]
        if not drifted:
            console.print("[dim]no drifted overrides found[/dim]")
            return
        results.extend(
            diff_override(squad_dir, name=entry.name, kind=entry.kind) for entry in drifted
        )

    if json_out:
        print_json_clean(
            json.dumps(
                [
                    {
                        "name": r.name,
                        "kind": r.kind,
                        "base_version": r.base_version,
                        "base_available": r.base_available,
                        "delta_mine": r.delta_mine,
                        "delta_upgrade": r.delta_upgrade,
                    }
                    for r in results
                ]
            )
        )
        return

    for result in results:
        _print_diff_result(result)


def _print_diff_result(result: DiffResult) -> None:
    label = result.name if result.kind == "template" else f"--role {result.name}"
    console.print(f"\n[bold]Override: {e(label)}[/bold]  [dim](kind: {result.kind})[/dim]")
    if result.base_version:
        console.print(f"[dim]base version: v{result.base_version}[/dim]")

    console.print("\n[yellow]Δ-mine[/yellow]  (your override vs current bundled):")
    if result.delta_mine:
        console.print(result.delta_mine, markup=False, highlight=False)
    else:
        console.print("[dim](no difference)[/dim]")

    console.print(
        "\n[yellow]Δ-upgrade[/yellow]  "
        "(base-version bundled vs current bundled — what the upgrade changed):"
    )
    if result.delta_upgrade:
        console.print(result.delta_upgrade, markup=False, highlight=False)
    else:
        console.print("[dim](no difference)[/dim]")


# ─── update ────────────────────────────────────────────────────────────────────


@override_app.command("update")
@handle_errors
def update(
    name: str | None = typer.Argument(
        None,
        help="Template name or role slug to re-stamp. Omit to re-stamp all valid overrides.",
    ),
    role: str | None = typer.Option(None, "--role", help="Re-stamp a role TOML override by slug."),
):
    """Re-stamp an override's base version after a hand-merge, clearing the drift warning.

    Only rewrites the ``squads:override-base:`` stamp — the override body is never touched.
    This is the maintainer's assertion "I have reconciled this against the current bundled default."

    The next ``sq check`` recomputes drift against the new base and the warning clears.

    With no name/--role, re-stamps every structurally-valid override (bulk acknowledge).
    Broken overrides (missing required markers) are skipped — fix them first.
    """
    svc = get_service()
    squad_dir = svc.paths.squad_dir

    if role is not None:
        stamped = update_stamp(squad_dir, name=role, kind="role")
    elif name is not None:
        stamped = update_stamp(squad_dir, name=name, kind="template")
    else:
        stamped = update_stamp(squad_dir, name=None, kind=None)

    if not stamped:
        console.print("[dim]nothing to update (no overrides found, or all are current)[/dim]")
        return

    from squads import __version__

    for n in stamped:
        console.print(f"[green]re-stamped[/green] {e(n)} → v{e(__version__)}")
    console.print("\nRun [cyan]sq check[/cyan] to confirm the drift warning is cleared.")
