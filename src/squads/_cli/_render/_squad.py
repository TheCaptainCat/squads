"""The corpus-wide and squad-creation renderers: what a repair, renumber, migration, repad, bulk
rename, import, init and adopt did."""

from rich.console import Console
from rich.panel import Panel

from squads._api._dto._squad import (
    AdoptReport,
    ImportFindingRow,
    ImportIssueRow,
    ImportReport,
    InitReport,
    MigrationReport,
    Reconciled,
    RenameStatusReport,
    RenameTypeReport,
    RenumberReport,
    RepadReport,
    RepairReport,
)
from squads._cli._render._style import e

_CHECK_HINT = "  run [cyan]`sq check`[/cyan] to verify integrity"

#: What a migration that skipped items says about them, after the count and the ids.
_SKIPPED_REMEDY = (
    " — a missing body region needs one added by hand; a body carrying content this step has no "
    "model for is left exactly as it was — `sq check` (reachable once this run completes) names "
    "which applies to each. Once the item's own problem is fixed and it genuinely carries no tag, "
    "place one with `sq <type> <n> view add <name>` (a role or skill instead addresses by slug: "
    "`sq role|skill <slug> view add <name>`); an item already carrying the tag outside its own "
    "region needs its own different fix — placing another copy inside the region would duplicate "
    "it, so delete the outside line from the file by hand first, then place it with the same "
    "`view add`"
)


def _print_unreadable(lines: list[str], console: Console) -> None:
    for line in lines:
        console.print(f"[red]error[/red]: {e(line)}", soft_wrap=True)


def _print_notice(notice: str | None, console: Console) -> None:
    if notice:
        console.print(notice, soft_wrap=True)


def _print_warnings(warnings: list[str], console: Console) -> None:
    for warning in warnings:
        console.print(f"[yellow]warning:[/yellow] {e(warning)}", soft_wrap=True)


def render_repair(report: RepairReport, console: Console) -> None:
    """The rebuilt index, the content notice, then each missing file, unreadable file and
    renumbering line."""
    console.print(f"rebuilt index: {report.indexed} items, counter={report.counter}")
    _print_notice(report.notice, console)
    for missing in report.missing:
        console.print(
            f"[yellow]warn[/yellow] [dim]{missing}[/dim]: indexed but no markdown file found "
            "(deleted?)"
        )
    _print_unreadable(report.unreadable, console)
    for line in report.renumbered:
        console.print(e(line), soft_wrap=True)


def render_renumber(report: RenumberReport, console: Console) -> None:
    """The offset's caution, then the count, the content notice and each move."""
    if report.warning:
        console.print(f"[yellow]warning:[/yellow] {e(report.warning)}", soft_wrap=True)
    if not report.moved:
        console.print("[dim]nothing to renumber — no local item at or above --from[/dim]")
        return
    console.print(f"renumbered {len(report.moved)} item(s); counter={report.counter}")
    _print_notice(report.notice, console)
    for moved in report.moved:
        console.print(f"  {e(moved.old)} -> {e(moved.new)}")


def _reconcile_line(reconciled: Reconciled) -> str:
    parts: list[str] = []
    if reconciled.indexed:
        parts.append(f"indexed {', '.join(e(i) for i in reconciled.indexed)}")
    if reconciled.missing:
        parts.append(f"dropped {', '.join(e(i) for i in reconciled.missing)} (no file backs it)")
    return f"  index reconciled with the files: {'; '.join(parts)}"


def render_migration(report: MigrationReport, console: Console) -> None:
    """Each migration run with its report lines and skipped items, then the verdict, the content
    notice, the unreadable files and where the manual steps are."""
    if not report.applied:
        console.print(f"already at schema v{report.schema_version}; nothing to migrate")
        return
    reconciled = report.reconciled
    if reconciled is not None and (reconciled.indexed or reconciled.missing):
        console.print(_reconcile_line(reconciled), soft_wrap=True)
    for m in report.applied:
        changed_suffix = f" — {m.changed} changed" if m.changed else ""
        console.print(
            f"  {m.version} (schema v{m.from_schema}→v{m.to_schema}): "
            f"{e(m.summary)}{changed_suffix}"
        )
        for line in m.reports:
            console.print(f"    {e(line)}", soft_wrap=True)
        if m.skipped:
            console.print(
                f"  [yellow]skipped[/yellow] {len(m.skipped)} item(s) rather than abort the "
                f"run: {', '.join(e(i) for i in m.skipped)}{_SKIPPED_REMEDY}",
                soft_wrap=True,
            )
    if report.config_dropped:
        console.print(
            "  [yellow]dropped[/yellow] from .squads.toml (not read by squads): "
            f"{', '.join(e(k) for k in report.config_dropped)}",
            soft_wrap=True,
        )
    console.print(
        f"[green]migrated[/green] to schema v{report.schema_version}; index rebuilt — "
        "run `sq sync` to regenerate the agent files "
        "(pointers, skills, CLAUDE.md/AGENTS.md sections)",
        soft_wrap=True,
    )
    _print_notice(report.notice, console)
    _print_unreadable(report.unreadable, console)
    if report.manual_span is not None:
        console.print(
            "[yellow]manual steps remain[/yellow] — read them with "
            f"`sq migrate chlog {report.manual_span}`",
            soft_wrap=True,
        )


def render_repad(report: RepadReport, console: Console) -> None:
    console.print(
        f"[green]repad done[/green]: padding {report.previous} → {report.width}; "
        f"{report.renamed} file(s) renamed; index rebuilt"
    )
    console.print(_CHECK_HINT, soft_wrap=True)


def render_rename_type(report: RenameTypeReport, console: Console) -> None:
    console.print(
        f"[green]rename-type done[/green]: {e(report.old_type)} → {e(report.new_type)}, "
        f"{report.renamed} item(s) renamed; index rebuilt"
    )
    console.print(_CHECK_HINT, soft_wrap=True)


def render_rename_status(report: RenameStatusReport, console: Console) -> None:
    console.print(
        f"[green]rename-status done[/green]: {e(report.type)}: {e(report.old_status)} → "
        f"{e(report.new_status)}, {report.renamed} item(s) renamed"
    )
    console.print(_CHECK_HINT, soft_wrap=True)


def render_import_refusal(report: ImportReport, console: Console) -> None:
    """Every pre-pass problem, line-numbered and in order, then the count."""
    for issue in report.issues:
        if isinstance(issue, ImportIssueRow):
            console.print(f"[red]line {issue.line}:[/red] {e(issue.message)}", soft_wrap=True)
    console.print(f"[red]{len(report.issues)} issue(s) found — nothing written.[/red]")


def render_import(report: ImportReport, console: Console) -> None:
    """The events by op and the handles given, then the dry-run note, or the applied run's
    error-level findings, its warnings and the count."""
    for op, count in report.op_counts.items():
        console.print(f"  {e(op)}: {count}")
    if report.handle_to_id or report.handle_to_sub:
        console.print("[bold]handles:[/bold]")
        for handle, item_id in report.handle_to_id.items():
            console.print(f"  {e(handle)} -> {e(item_id)}")
        for handle, (parent_id, local_id) in report.handle_to_sub.items():
            console.print(f"  {e(handle)} -> {e(parent_id)} {e(local_id)}")
    if not report.applied:
        console.print("[dim]dry run — nothing written[/dim]")
        return
    for finding in report.issues:
        if isinstance(finding, ImportFindingRow) and finding.level == "error":
            console.print(
                f"[red]error:[/red] {e(finding.item)}: {e(finding.message)}", soft_wrap=True
            )
    _print_warnings(report.warnings, console)
    console.print(f"[green]imported[/green] {sum(report.op_counts.values())} event(s)")


def render_init(report: InitReport, console: Console) -> None:
    """The squad's panel, the scaffolding notices and the next steps."""
    lines = [
        f"[bold]squad:[/bold] {report.squad}",
        f"[bold]index:[/bold] {report.index}",
        f"[bold]roles:[/bold] {', '.join(report.roles) or '—'}",
        f"[bold]agent backends:[/bold] {', '.join(report.backends) or '(none)'}",
    ]
    console.print(Panel("\n".join(lines), title="squads initialized", expand=False))
    _print_warnings(report.warnings, console)
    console.print(
        "Next: [cyan]sq create --help[/cyan] to see your item types · [cyan]sq list[/cyan]"
        " · [cyan]sq role catalog[/cyan]",
        soft_wrap=True,
    )


def render_adopt(report: AdoptReport, console: Console) -> None:
    """The squad's panel, the content notice, the scaffolding notices and the unreadable files;
    the next steps only when every file was read."""
    lines = [
        f"[bold]squad:[/bold] {report.squad}",
        f"[bold]imported:[/bold] {report.imported} existing item(s)",
        f"[bold]roles activated:[/bold] {', '.join(report.roles) or '—'}",
    ]
    console.print(Panel("\n".join(lines), title="squads adopted", expand=False))
    _print_notice(report.notice, console)
    _print_warnings(report.warnings, console)
    _print_unreadable(report.unreadable, console)
    for line in report.renumbered:
        console.print(e(line), soft_wrap=True)
    if report.unreadable:
        return
    console.print(
        "Migrate legacy docs with [cyan]sq --at <date> create …[/cyan] to preserve history; "
        "then [cyan]sq check[/cyan].",
        soft_wrap=True,
    )
