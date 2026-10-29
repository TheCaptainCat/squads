"""The override renderers: the listing, the two-delta diffs, a scaffolded override and the
re-stamped ones. An override's ``kind`` and ``state`` are the fixed sets the override commands
define, not workflow vocabulary."""

from rich.console import Console
from rich.table import Table

from squads._api._dto._overrides import (
    OverrideDiff,
    OverrideDiffRow,
    OverrideList,
    ScaffoldedOverride,
    StampedOverrides,
)
from squads._cli._render._style import e


def _state_color(state: str) -> str:
    """The colour an override state is shown in."""
    match state:
        case "current":
            return "green"
        case "drifted":
            return "yellow"
        case "broken":
            return "red"
        case _:
            return "white"


def print_errors(errors: list[str], err_console: Console) -> None:
    """One ``error:`` line per override that could not be handled."""
    for line in errors:
        err_console.print(f"error: {e(line)}", soft_wrap=True)


def render_overrides(listing: OverrideList, console: Console, err_console: Console) -> None:
    """The overrides as a table, then the cause of each broken one."""
    if not listing.items:
        console.print(
            "[dim]no overrides found under .overrides/[/dim]\n"
            "Run [cyan]sq override scaffold <template_name>[/cyan] to start one.",
            soft_wrap=True,
        )
        return
    table = Table(box=None, pad_edge=False)
    for col in ("Name", "Kind", "Base Version", "State"):
        table.add_column(col)
    for row in listing.items:
        color = _state_color(row.state)
        table.add_row(
            e(row.name),
            row.kind,
            e(row.base_version or "(unstamped)"),
            f"[{color}]{row.state}[/{color}]",
        )
    console.print(table)
    print_errors(listing.errors, err_console)


def _label(row: OverrideDiffRow) -> str:
    match row.kind:
        case "template":
            return row.name
        case "role":
            return f"--role {row.name}"
        case "playbook" | "roles":
            return row.kind
        case _:
            return "workflow"


def _render_diff(row: OverrideDiffRow, console: Console) -> None:
    console.print(f"\n[bold]Override: {e(_label(row))}[/bold]  [dim](kind: {row.kind})[/dim]")
    if row.base_version:
        console.print(f"[dim]base version: v{row.base_version}[/dim]")
    console.print("\n[yellow]Δ-mine[/yellow]  (your override vs current bundled):")
    if row.delta_mine:
        console.print(row.delta_mine, markup=False, highlight=False)
    else:
        console.print("[dim](no difference)[/dim]")
    console.print(
        "\n[yellow]Δ-upgrade[/yellow]  "
        "(base-version bundled vs current bundled — what the upgrade changed):"
    )
    if row.delta_upgrade:
        console.print(row.delta_upgrade, markup=False, highlight=False)
    else:
        console.print("[dim](no difference)[/dim]")


def render_diffs(diff: OverrideDiff, console: Console, err_console: Console) -> None:
    """Each override's two deltas, then a line for each broken override."""
    if not diff.items and not diff.failed:
        console.print("[dim]no drifted overrides found[/dim]")
    for row in diff.items:
        _render_diff(row, console)
    print_errors(diff.errors, err_console)


def render_scaffolded(scaffolded: ScaffoldedOverride, console: Console) -> None:
    """Where the override was written, and what to do with it next."""
    path = e(scaffolded.entry.path)
    match scaffolded.entry.kind:
        case "role":
            action = (
                "uncomment the fields to override"
                if scaffolded.prefilled
                else "add fields to override (e.g. full_name, model)"
            )
            text = (
                f"[green]scaffolded[/green] role override: [bold]{path}[/bold]\n"
                f"Edit [cyan]{path}[/cyan] to {action}, then verify with "
                f"[cyan]sq override diff --role {e(scaffolded.entry.name)}[/cyan]."
            )
        case "workflow":
            text = (
                f"[green]scaffolded[/green] workflow override: [bold]{path}[/bold]\n"
                f"Edit [cyan]{path}[/cyan] to add custom types, statuses, and lifecycles,\n"
                f"then validate with [cyan]sq workflow lint[/cyan] and "
                f"inspect with [cyan]sq override diff workflow[/cyan]."
            )
        case "playbook":
            text = (
                f"[green]scaffolded[/green] playbook override: [bold]{path}[/bold]\n"
                f"Edit [cyan]{path}[/cyan] to add a role's guidance to a type "
                f"(the '$(*self)' append idiom), then "
                f"inspect with [cyan]sq override diff playbook[/cyan]."
            )
        case "roles":
            text = (
                f"[green]scaffolded[/green] role catalog override: [bold]{path}[/bold]\n"
                f"Edit [cyan]{path}[/cyan] to override \\[\\[roles]], \\[bundles], or "
                f"\\[templates.<name>], then inspect with [cyan]sq override diff roles[/cyan]."
            )
        case _:
            text = (
                f"[green]scaffolded[/green] template override: [bold]{path}[/bold]\n"
                f"Edit [cyan]{path}[/cyan], then verify with "
                f"[cyan]sq override diff {e(scaffolded.entry.name)}[/cyan]."
            )
    console.print(text, soft_wrap=True)


def render_stamped(stamped: StampedOverrides, console: Console, err_console: Console) -> None:
    """Each override re-stamped and the version it now carries, then the ones that could not
    be read."""
    if not stamped.stamped:
        if not stamped.errors:
            console.print("[dim]nothing to update (no overrides found, or all are current)[/dim]")
    else:
        for name in stamped.stamped:
            console.print(f"[green]re-stamped[/green] {e(name)} → v{e(stamped.version)}")
        console.print(
            "\nRun [cyan]sq check[/cyan] to confirm the drift warning is cleared.", soft_wrap=True
        )
    print_errors(stamped.errors, err_console)
