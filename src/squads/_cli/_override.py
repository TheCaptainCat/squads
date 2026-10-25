"""`sq override` — manage project-level template and role overrides.

The four subcommands are the complete override-management surface:

- ``sq override scaffold <name>`` — copy a bundled template into ``.overrides/`` with stamp.
- ``sq override scaffold --new <slug>`` — start a brand-new, non-bundled role TOML.
- ``sq override list``            — show all overrides with kind, base, and state.
- ``sq override diff [<name>]``   — two-delta view (Δ-mine + Δ-upgrade) for drifted overrides.
- ``sq override update [<name>]`` — re-stamp after a hand-merge; body untouched.

``list`` and ``diff`` support ``--json`` for machine-readable output.
"""

import json

import typer
from rich.table import Table

from squads._cli._common import (
    Ground,
    command,
    console,
    e,
    err_console,
    gate_group_command,
    get_service,
    get_squad_paths,
    handle_errors,
    past_the_gate,
    print_json_clean,
)
from squads._overrides._service import (
    STATE_BROKEN,
    STATE_CURRENT,
    STATE_DRIFTED,
    DiffResult,
    OverrideEntry,
    diff_override,
    scaffold_new_role,
    scaffold_playbook,
    scaffold_role,
    scaffold_roles_catalog,
    scaffold_template,
    scaffold_workflow,
    scan_overrides,
    update_stamp,
)
from squads._roles._catalog import PREDEFINED
from squads._roles._resolver import role_base_from_item
from squads._workflow import ROSTER_ROLE

override_app = typer.Typer(
    no_args_is_help=True,
    help="Manage project-level template and role overrides.",
)


@override_app.callback()
def override_gate(ctx: typer.Context) -> None:
    """Gate each ``sq override`` command by the grant it declares."""
    gate_group_command(ctx, override_app)


# ─── scaffold ──────────────────────────────────────────────────────────────────


@override_app.command("scaffold")
@command
async def scaffold(
    name: str | None = typer.Argument(
        None,
        help="Template name, such as `items/<type>.md.j2`, or `workflow`, `playbook`, `roles`.",
    ),
    role: str | None = typer.Option(
        None, "--role", help="Bundled role to override in a file of its own, such as `architect`."
    ),
    new: str | None = typer.Option(
        None,
        "--new",
        help="Slug for a new role that is not in the catalog, such as `security-analyst`.",
    ),
    can_spawn: bool = typer.Option(
        False,
        "--can-spawn",
        help="With `--new`, let the new role spawn other agents.",
    ),
    workflow: bool = typer.Option(
        False, "--workflow", help="Scaffold the workflow spec override, `workflow.toml`."
    ),
    playbook: bool = typer.Option(
        False, "--playbook", help="Scaffold the playbook override, `playbook.toml`."
    ),
    roles_catalog: bool = typer.Option(
        False,
        "--roles-catalog",
        help="Scaffold the override of the whole role catalog, `roles.toml`.",
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite an override that exists."),
):
    """Copy a bundled default into `.overrides/` to start an override from.

    Pick one: a template by `NAME`; one role, bundled (`--role`) or new (`--new`);
    or a whole document, the workflow spec, the playbook or the role catalog. Each
    document has two spellings, a name or a flag: `workflow` or `--workflow`,
    `playbook` or `--playbook`, `roles` or `--roles-catalog`. Edit the file, then
    check it with `sq override diff`; a new role is created with `sq role
    activate`.
    """
    svc = get_service()
    squad_dir = svc.paths.squad_dir

    if role is not None and new is not None:
        raise typer.BadParameter("--role and --new are mutually exclusive")

    if new is not None:
        dest = scaffold_new_role(squad_dir, slug=new, force=force, can_spawn=can_spawn)
        console.print(
            f"[green]scaffolded[/green] new role override: [bold]{e(str(dest))}[/bold]\n"
            f"Edit [cyan]{e(str(dest))}[/cyan] to fill in the stubbed essentials, then activate "
            f"with [cyan]sq role activate {e(new)}[/cyan].",
            soft_wrap=True,
        )
        return

    if role is not None:
        item = await svc.roster_item(ROSTER_ROLE, role)
        base = role_base_from_item(item, svc.catalog) if item is not None else None
        dest = scaffold_role(squad_dir, slug=role, force=force, base=base)
        scaffolded = base is not None or role in {r.slug for r in PREDEFINED}
        action = (
            "uncomment the fields to override"
            if scaffolded
            else "add fields to override (e.g. full_name, model)"
        )
        console.print(
            f"[green]scaffolded[/green] role override: [bold]{e(str(dest))}[/bold]\n"
            f"Edit [cyan]{e(str(dest))}[/cyan] to {action}, then verify with "
            f"[cyan]sq override diff --role {e(role)}[/cyan].",
            soft_wrap=True,
        )
        return

    # Accept 'workflow' as a positional name OR --workflow flag.
    if workflow or name == "workflow":
        dest = scaffold_workflow(squad_dir, force=force)
        console.print(
            f"[green]scaffolded[/green] workflow override: [bold]{e(str(dest))}[/bold]\n"
            f"Edit [cyan]{e(str(dest))}[/cyan] to add custom types, statuses, and lifecycles,\n"
            f"then validate with [cyan]sq workflow lint[/cyan] and "
            f"inspect with [cyan]sq override diff workflow[/cyan].",
            soft_wrap=True,
        )
        return

    # Accept 'playbook' as a positional name OR --playbook flag.
    if playbook or name == "playbook":
        dest = scaffold_playbook(squad_dir, force=force)
        console.print(
            f"[green]scaffolded[/green] playbook override: [bold]{e(str(dest))}[/bold]\n"
            f"Edit [cyan]{e(str(dest))}[/cyan] to add a role's guidance to a type "
            f"(the '$(*self)' append idiom), then "
            f"inspect with [cyan]sq override diff playbook[/cyan].",
            soft_wrap=True,
        )
        return

    # Accept 'roles' as a positional name OR --roles-catalog flag.
    if roles_catalog or name == "roles":
        dest = scaffold_roles_catalog(squad_dir, force=force)
        console.print(
            f"[green]scaffolded[/green] role catalog override: [bold]{e(str(dest))}[/bold]\n"
            f"Edit [cyan]{e(str(dest))}[/cyan] to override \\[\\[roles]], \\[bundles], or "
            f"\\[dev], then inspect with [cyan]sq override diff roles[/cyan].",
            soft_wrap=True,
        )
        return

    if name is None:
        raise typer.BadParameter(
            "provide a template name (e.g. 'items/<type>.md.j2'), 'workflow', 'playbook', "
            "'roles', or --role <slug> / --workflow / --playbook / --roles-catalog to "
            "scaffold a role, workflow, playbook, or role-catalog override"
        )

    dest = scaffold_template(squad_dir, template_name=name, force=force)
    console.print(
        f"[green]scaffolded[/green] template override: [bold]{e(str(dest))}[/bold]\n"
        f"Edit [cyan]{e(str(dest))}[/cyan], then verify with "
        f"[cyan]sq override diff {e(name)}[/cyan].",
        soft_wrap=True,
    )


# ─── list ──────────────────────────────────────────────────────────────────────


@override_app.command(name="list")
@past_the_gate(Ground.NO_SQUAD_STATE, behind=True)
@handle_errors
def list_overrides(
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per override."
    ),
):
    """List every override with its kind, base version and drift state.

    `current` is up to date; `drifted` means the bundled default changed since the
    base version; `broken` means required sq markers are missing or the file
    cannot be read, an error in `sq check`; the command then exits 1.
    """
    entries = scan_overrides(get_squad_paths().squad_dir)

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
        if any(entry.state == STATE_BROKEN for entry in entries):
            raise typer.Exit(1)
        return

    if not entries:
        console.print(
            "[dim]no overrides found under .overrides/[/dim]\n"
            "Run [cyan]sq override scaffold <template_name>[/cyan] to start one.",
            soft_wrap=True,
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
    broken = [entry for entry in entries if entry.state == STATE_BROKEN]
    for entry in broken:
        if entry.cause:
            err_console.print(f"error: {e(entry.cause)}", soft_wrap=True)
    if broken:
        raise typer.Exit(1)


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
@past_the_gate(Ground.NO_SQUAD_STATE, behind=True)
@handle_errors
def diff(
    name: str | None = typer.Argument(
        None,
        help="Template name, role slug, `workflow`, `playbook` or `roles`; omit for all drifted.",
    ),
    role: str | None = typer.Option(None, "--role", help="Diff the override of this role."),
    workflow: bool = typer.Option(
        False, "--workflow", help="Diff the workflow spec override, `workflow.toml`."
    ),
    playbook: bool = typer.Option(
        False, "--playbook", help="Diff the playbook override, `playbook.toml`."
    ),
    roles_catalog: bool = typer.Option(
        False,
        "--roles-catalog",
        help="Diff the override of the whole role catalog, `roles.toml`.",
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per override diffed."
    ),
):
    """Show your edits to an override and what an upgrade changed beneath it.

    Δ-mine:    your override against the current bundled default.
    Δ-upgrade: the bundled default at your base version against the current one.

    Merge what Δ-upgrade added into your override by hand, then run
    `sq override update <name>`. With no name or flag, every drifted override is
    diffed; one that cannot be read is named with its cause and the command
    exits 1 after the rest.
    """
    squad_dir = get_squad_paths().squad_dir

    results: list[DiffResult] = []
    entries: list[OverrideEntry] = []

    if role is not None:
        results.append(diff_override(squad_dir, name=role, kind="role"))
    elif workflow or name == "workflow":
        results.append(diff_override(squad_dir, name="workflow", kind="workflow"))
    elif playbook or name == "playbook":
        results.append(diff_override(squad_dir, name="playbook", kind="playbook"))
    elif roles_catalog or name == "roles":
        results.append(diff_override(squad_dir, name="roles", kind="roles"))
    elif name is not None:
        results.append(diff_override(squad_dir, name=name, kind="template"))
    else:
        # No name: diff every drifted override.
        entries = scan_overrides(squad_dir)
        drifted = [e for e in entries if e.state == STATE_DRIFTED]
        if not drifted and not json_out:
            if not any(entry.cause for entry in entries):
                console.print("[dim]no drifted overrides found[/dim]")
            _fail_on_unreadable(entries)
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
        _fail_on_unreadable(entries)
        return

    for result in results:
        _print_diff_result(result)
    _fail_on_unreadable(entries)


def _fail_on_unreadable(entries: list[OverrideEntry]) -> None:
    """Name each override that cannot be read, with its cause, and exit 1 when there is one; the
    readable overrides have already been handled."""
    unreadable = [entry for entry in entries if entry.cause]
    for entry in unreadable:
        err_console.print(f"error: {e(entry.cause or '')}", soft_wrap=True)
    if unreadable:
        raise typer.Exit(1)


def _print_diff_result(result: DiffResult) -> None:
    if result.kind == "template":
        label = result.name
    elif result.kind == "role":
        label = f"--role {result.name}"
    elif result.kind == "playbook":
        label = "playbook"
    elif result.kind == "roles":
        label = "roles"
    else:
        label = "workflow"
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
@past_the_gate(Ground.NO_SQUAD_STATE, behind=True)
@handle_errors
def update(
    name: str | None = typer.Argument(
        None,
        help="Template name, role slug, `workflow`, `playbook` or `roles`; omit for all valid.",
    ),
    role: str | None = typer.Option(None, "--role", help="Re-stamp the override of this role."),
    workflow: bool = typer.Option(
        False, "--workflow", help="Re-stamp the workflow spec override, `workflow.toml`."
    ),
    playbook: bool = typer.Option(
        False, "--playbook", help="Re-stamp the playbook override, `playbook.toml`."
    ),
    roles_catalog: bool = typer.Option(
        False,
        "--roles-catalog",
        help="Re-stamp the override of the whole role catalog, `roles.toml`.",
    ),
):
    """Mark an override as merged with the current default, clearing its drift.

    Only the base-version stamp is rewritten, never the override's content. With
    no name or flag, every valid override is re-stamped; a broken one is skipped
    until it is fixed, which is named with its cause and exits 1.
    """
    squad_dir = get_squad_paths().squad_dir
    entries: list[OverrideEntry] = []

    if role is not None:
        stamped = update_stamp(squad_dir, name=role, kind="role")
    elif workflow or name == "workflow":
        stamped = update_stamp(squad_dir, name="workflow", kind="workflow")
    elif playbook or name == "playbook":
        stamped = update_stamp(squad_dir, name="playbook", kind="playbook")
    elif roles_catalog or name == "roles":
        stamped = update_stamp(squad_dir, name="roles", kind="roles")
    elif name is not None:
        stamped = update_stamp(squad_dir, name=name, kind="template")
    else:
        entries = scan_overrides(squad_dir)
        stamped = update_stamp(squad_dir, name=None, kind=None)

    if not stamped:
        if not any(entry.cause for entry in entries):
            console.print("[dim]nothing to update (no overrides found, or all are current)[/dim]")
        _fail_on_unreadable(entries)
        return

    from squads import __version__

    for n in stamped:
        console.print(f"[green]re-stamped[/green] {e(n)} → v{e(__version__)}")
    console.print(
        "\nRun [cyan]sq check[/cyan] to confirm the drift warning is cleared.", soft_wrap=True
    )
    _fail_on_unreadable(entries)
