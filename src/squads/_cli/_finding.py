"""`sq finding` — a review's findings (severity + status)."""

import typer
from rich.table import Table

from squads._cli._common import (
    console,
    e,
    get_service,
    handle_errors,
    parse_severity,
    parse_status,
    print_block,
)
from squads._discussion import BlockInfo
from squads._models._enums import SEVERITY_EMOJI, Severity

finding_app = typer.Typer(no_args_is_help=True, help="Manage a review's findings.")


def _severity_cell(b: BlockInfo) -> str:
    return f"{SEVERITY_EMOJI[Severity(b.severity)]} {b.severity}" if b.severity else ""


@finding_app.command("add")
@handle_errors
def finding_add(
    review_id: str = typer.Argument(...),
    title: str = typer.Argument("", help="Optional short label; write detail in the body."),
    severity: str = typer.Option(
        "medium", "--severity", help="critical | high | medium | low | info."
    ),
    json_out: bool = typer.Option(False, "--json"),
):
    """Scaffold a review finding (severity + free-form body + its own discussion)."""
    svc = get_service()
    print_block(
        review_id, svc.add_finding(review_id, title, severity=parse_severity(severity)), json_out
    )


@finding_app.command("list")
@handle_errors
def finding_list(review_id: str = typer.Argument(...)):
    """List a review's findings with their severity and status."""
    blocks = get_service().list_findings(review_id)
    if not blocks:
        console.print("[dim]no findings[/dim]")
        return
    table = Table(box=None, pad_edge=False)
    for col in ("ID", "Severity", "Status", "Finding"):
        table.add_column(col)
    for b in blocks:
        table.add_row(b.local_id, _severity_cell(b), b.status, e(b.title))
    console.print(table)


@finding_app.command("status")
@handle_errors
def finding_status(
    review_id: str = typer.Argument(...),
    local_id: str = typer.Argument(..., metavar="Fn"),
    new_status: str = typer.Argument(..., metavar="STATUS"),
    force: bool = typer.Option(False, "--force"),
):
    """Transition a finding (Open → Fixed → Verified; + WontFix)."""
    svc = get_service()
    svc.set_finding_status(review_id, local_id, parse_status(new_status), force=force)
    console.print(f"{review_id} {local_id} → [bold]{parse_status(new_status).value}[/bold]")
