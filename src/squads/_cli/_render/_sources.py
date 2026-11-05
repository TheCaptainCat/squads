"""The source renderers: the declared sources, a pull, and the commands tying one item to its
issue. A credential is only ever reported as stored or not, never shown."""

from rich.console import Console
from rich.table import Table

from squads._api import (
    CredentialRemoved,
    CredentialWritten,
    SourceChecked,
    SourceListed,
    SourcePulled,
    SourceRefreshed,
    SourceRelinked,
    SourceUnlinked,
)
from squads._cli._render._style import e


def render_credential_written(written: CredentialWritten, console: Console) -> None:
    """Which source's credential was stored, under which address and in which file."""
    console.print(
        f"stored the credential of source [bold]{e(written.source)}[/bold] "
        f"({e(', '.join(written.fields))}) for {e(written.base_url)} in {e(written.path)}"
    )


def render_credential_removed(removed: CredentialRemoved, console: Console) -> None:
    """Whether a credential was deleted for the source."""
    if removed.removed:
        console.print(
            f"removed the credential of source [bold]{e(removed.source)}[/bold] "
            f"for {e(removed.base_url)}"
        )
    else:
        console.print(
            f"[dim]source {e(removed.source)} has no stored credential for "
            f"{e(removed.base_url)}[/dim]"
        )


def render_pulled(pulled: SourcePulled, console: Console) -> None:
    """Each source's outcome: what it created and refreshed, then every line worth reporting."""
    verb = "would create" if pulled.dry_run else "created"
    for report in pulled.sources:
        if report.left_out is not None:
            console.print(f"[yellow]{e(report.name)}[/yellow]: skipped, {e(report.left_out)}")
            continue
        counters = [
            (f"{verb} {len(report.created)}" + (f" ({e(', '.join(report.created))})")),
            f"refreshed {report.refreshed}",
            f"unchanged {report.unchanged}",
            f"dropped {report.dropped}",
            f"gone {report.gone}",
            f"restricted {report.restricted}",
            f"held elsewhere {report.held_elsewhere}",
            f"filtered out {report.filtered_out}",
            f"skipped {report.skipped_no_type} (no type)",
        ]
        counts = [report.created, report.refreshed, report.unchanged, report.dropped, report.gone]
        counts += [report.restricted, report.held_elsewhere, report.filtered_out]
        counts += [report.skipped_no_type]
        shown = [text for text, count in zip(counters, counts, strict=True) if count]
        console.print(f"[bold]{e(report.name)}[/bold]: {', '.join(shown) or 'no issues'}")
        for line in report.lines:
            console.print(f"  {e(line)}")


def render_listed(listed: SourceListed, console: Console) -> None:
    """The declared sources as a table, or a note that there are none."""
    if not listed.sources:
        console.print(
            "[dim]no source is declared; see `sq override scaffold sources`[/dim]", soft_wrap=True
        )
        return
    table = Table(box=None, pad_edge=False)
    for column in ("Source", "Connector", "State", "Credential", "Items", "Newest update"):
        table.add_column(column)
    for row in listed.sources:
        table.add_row(
            e(row.name),
            e(f"{row.connector}@{row.version}"),
            "enabled" if row.enabled else "[yellow]disabled[/yellow]",
            "stored" if row.credential else "[yellow]none[/yellow]",
            str(row.items),
            e(row.newest_updated_at or "-"),
        )
    console.print(table)


def render_refreshed(refreshed: SourceRefreshed, console: Console) -> None:
    """What a refresh found worth reporting; nothing when the item already matched its issue."""
    for line in refreshed.lines:
        console.print(f"[dim]{e(line)}[/dim]")


def render_unlinked(unlinked: SourceUnlinked, console: Console) -> None:
    """The item and the issue it no longer follows."""
    console.print(
        f"unlinked [bold]{e(unlinked.id)}[/bold] from {e(unlinked.source)} {e(unlinked.key)}; "
        "its description is now body prose"
    )


def render_relinked(relinked: SourceRelinked, console: Console) -> None:
    """The item and the issue it follows again, then every line worth reporting."""
    console.print(
        f"relinked [bold]{e(relinked.id)}[/bold] to {e(relinked.source)} {e(relinked.key)}"
    )
    for line in relinked.lines:
        console.print(f"  {e(line)}")


_MARKS = (
    ("pass", "[green]pass[/green]"),
    ("fail", "[red]FAIL[/red]"),
    ("warn", "[yellow]warn[/yellow]"),
)


def render_checked(checked: SourceChecked, console: Console) -> None:
    """Each source's checklist, one line per probe and the fix under each failure or warning."""
    for entry in checked.sources:
        state = "" if entry.enabled else " (disabled)"
        console.print(
            f"[bold]{e(entry.name)}[/bold] ({e(entry.connector)}@{e(entry.version)}){state}"
        )
        for line in entry.lines:
            console.print(f"  {dict(_MARKS)[line.verdict]}  {e(line.text)}", soft_wrap=True)
            if line.fix:
                console.print(f"        fix: {e(line.fix)}", soft_wrap=True)
