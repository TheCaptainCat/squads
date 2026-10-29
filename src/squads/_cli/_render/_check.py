"""The check and sync renderers: the lint report, one line per finding, and what a sync left
alone."""

from rich.console import Console

from squads._api._dto._check import CheckReport, SyncReport
from squads._cli._render._style import e


def render_check(report: CheckReport, console: Console) -> None:
    """Each finding, coloured by its level, with the item or file it is about."""
    if not report.items:
        console.print("[green]✓ no issues[/green]")
        return
    for issue in report.items:
        color = "red" if issue.level == "error" else "yellow"
        loc = f" [dim]{issue.item}[/dim]" if issue.item else ""
        console.print(f"[{color}]{issue.level}[/{color}]{loc}: {e(issue.message)}", soft_wrap=True)


def render_sync(report: SyncReport, console: Console) -> None:
    """A warning per file the regeneration left alone, then the verdict."""
    for warning in report.skipped:
        console.print(f"[yellow]warning:[/yellow] {e(warning)}", soft_wrap=True)
    console.print("[green]synced[/green] managed files to this squads version")
