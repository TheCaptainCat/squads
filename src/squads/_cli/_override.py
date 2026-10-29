"""`sq override` — manage project-level template and role overrides.

The four subcommands are the complete override-management surface:

- ``sq override scaffold <name>`` — copy a bundled template into ``.overrides/`` with stamp.
- ``sq override list``            — show all overrides with kind, base, and state.
- ``sq override diff [<name>]``   — two-delta view (Δ-mine + Δ-upgrade) for drifted overrides.
- ``sq override update [<name>]`` — re-stamp after a hand-merge; body untouched.

Each prints what it read or wrote as JSON with ``--json``.
"""

import typer

from squads._api import _ops as ops
from squads._api._dto._overrides import (
    OverrideDiffRequest,
    OverrideListRequest,
    OverrideScaffoldRequest,
    OverrideUpdateRequest,
)
from squads._cli import _calls as calls
from squads._cli._common import (
    Ground,
    console,
    err_console,
    gate_group_command,
    handle_errors,
    past_the_gate,
)
from squads._cli._render._overrides import (
    print_errors,
    render_diffs,
    render_overrides,
    render_scaffolded,
    render_stamped,
)
from squads._errors import SquadsError

override_app = typer.Typer(
    no_args_is_help=True,
    help="Manage project-level template and role overrides.",
)


@override_app.callback()
def override_gate(ctx: typer.Context) -> None:
    """Gate each ``sq override`` command by the grant it declares."""
    gate_group_command(ctx, override_app)


def _address(
    name: str | None, role: str | None, workflow: bool, playbook: bool, roles_catalog: bool
) -> tuple[str, str] | None:
    """The ``(kind, name)`` of the override the arguments name, or ``None`` when they name
    none; a document's name and its flag are the same address."""
    if role is not None:
        return "role", role
    if workflow or name == "workflow":
        return "workflow", "workflow"
    if playbook or name == "playbook":
        return "playbook", "playbook"
    if roles_catalog or name == "roles":
        return "roles", "roles"
    if name is not None:
        return "template", name
    return None


# ─── scaffold ──────────────────────────────────────────────────────────────────


@override_app.command("scaffold")
@handle_errors
def scaffold(
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
        hidden=True,
        help="Retired: create a new role with `sq role add`.",
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
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: the override written."
    ),
):
    """Copy a bundled default into `.overrides/` to start an override from.

    Pick one: a template by `NAME`; one role (`--role`); or a whole document, the
    workflow spec, the playbook or the role catalog. Each document has two
    spellings, a name or a flag: `workflow` or `--workflow`, `playbook` or
    `--playbook`, `roles` or `--roles-catalog`. Edit the file, then check it with
    `sq override diff`. A new role is created with `sq role add`, not an override.
    """
    if new is not None:
        raise SquadsError(
            f"`sq override scaffold --new` is retired: create the role with "
            f"`sq role add {new} --name … --job-title … --desc … --mission …`"
        )
    address = _address(name, role, workflow, playbook, roles_catalog)
    if address is None:
        raise typer.BadParameter(
            "provide a template name (e.g. 'items/<type>.md.j2'), 'workflow', 'playbook', "
            "'roles', or --role <slug> / --workflow / --playbook / --roles-catalog to "
            "scaffold a role, workflow, playbook, or role-catalog override"
        )
    kind, target = address
    request = OverrideScaffoldRequest(kind=kind, name=target, force=force)
    response = calls.call(ops.OVERRIDES_SCAFFOLD, request)
    if json_out:
        calls.print_json(ops.OVERRIDES_SCAFFOLD, response)
        return
    calls.print_warnings(response)
    render_scaffolded(response.data, console)


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
    response = calls.call(ops.OVERRIDES_LIST, OverrideListRequest())
    if json_out:
        calls.print_json(ops.OVERRIDES_LIST, response)
    else:
        calls.print_warnings(response)
        render_overrides(response.data, console, err_console)
    if response.data.failed:
        raise typer.Exit(1)


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
    diffed; a broken one is named (with its cause when it cannot be read) and the
    command exits 1 after the rest.
    """
    address = _address(name, role, workflow, playbook, roles_catalog)
    kind, target = address if address is not None else (None, None)
    response = calls.call(ops.OVERRIDES_DIFF, OverrideDiffRequest(kind=kind, name=target))
    if json_out:
        calls.print_json(ops.OVERRIDES_DIFF, response)
        print_errors(response.data.errors, err_console)
    else:
        calls.print_warnings(response)
        render_diffs(response.data, console, err_console)
    if response.data.failed:
        raise typer.Exit(1)


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
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: the overrides re-stamped."
    ),
):
    """Mark an override as merged with the current default, clearing its drift.

    Only the base-version stamp is rewritten, never the override's content. With
    no name or flag, every valid override is re-stamped; a broken one is skipped
    until it is fixed, which is named with its cause and exits 1.
    """
    address = _address(name, role, workflow, playbook, roles_catalog)
    kind, target = address if address is not None else (None, None)
    response = calls.call(ops.OVERRIDES_UPDATE, OverrideUpdateRequest(kind=kind, name=target))
    if json_out:
        calls.print_json(ops.OVERRIDES_UPDATE, response)
        print_errors(response.data.errors, err_console)
    else:
        calls.print_warnings(response)
        render_stamped(response.data, console, err_console)
    if response.data.errors:
        raise typer.Exit(1)
