"""`sq migrate` — run schema migrations and read their steps.

- `sq migrate up`            run the automatic migration(s) for this squad
- `sq migrate help`          the migration changelog index (every shipped migration)
- `sq migrate chlog vA..vB`  the complete manual steps for migrating across that release range
"""

import typer
from rich.markdown import Markdown
from rich.table import Table

from squads import __version__
from squads._cli._common import (
    console,
    e,
    get_service,
    handle_errors,
    version_tuple,
)
from squads._errors import SquadsError
from squads._migrations._registry import MIGRATIONS
from squads._models._schema import SCHEMA_VERSION

migrate_app = typer.Typer(no_args_is_help=True, help="Run schema migrations and read their steps.")


@migrate_app.command("up")
@handle_errors
def migrate_up():
    """Run the automatic migration(s) to bring this squad to the current schema version."""
    svc = get_service()
    disk = svc.paths.config.schema_version
    if disk > SCHEMA_VERSION:
        raise SquadsError(
            f"this squad is at schema v{disk}, newer than this squads (v{SCHEMA_VERSION}); "
            "upgrade the squads package"
        )
    applied = svc.run_pending_migrations()
    if not applied:
        console.print(f"already at schema v{SCHEMA_VERSION}; nothing to migrate")
        return
    for m in applied:
        console.print(f"  {m.version} (schema v{m.from_schema}→v{m.to_schema}): {e(m.summary)}")
    console.print(
        f"[green]migrated[/green] to schema v{SCHEMA_VERSION}; index rebuilt — "
        "run `sq sync` to refresh managed files"
    )
    if any(m.manual for m in applied):
        span = f"v{svc.paths.config.squads_version}..v{__version__}"
        console.print(
            f"[yellow]manual steps remain[/yellow] — read them with `sq migrate chlog {span}`"
        )


@migrate_app.command("help")
@handle_errors
def migrate_help():
    """Show the migration changelog index (every shipped migration, newest schema last)."""
    table = Table(title="migration changelog — read steps with `sq migrate chlog vA..vB`")
    for col in ("Release", "Schema", "Summary", "Manual"):
        table.add_column(col)
    for m in MIGRATIONS:
        table.add_row(
            f"v{m.version}",
            f"v{m.from_schema}→v{m.to_schema}",
            e(m.summary),
            "yes" if m.manual else "—",
        )
    console.print(table)


@migrate_app.command("chlog")
@handle_errors
def migrate_chlog(
    span: str = typer.Argument(
        ..., metavar="vFROM..vTO", help="Release range, e.g. v0.1.1..v0.2.0."
    ),
):
    """Print the complete manual steps for migrations shipped in (vFROM, vTO]."""
    lo, hi = _parse_span(span)
    selected = [
        m for m in MIGRATIONS if version_tuple(lo) < version_tuple(m.version) <= version_tuple(hi)
    ]
    manual = [m for m in selected if m.manual]
    if not manual:
        console.print(f"[dim]no manual steps for v{lo}..v{hi}[/dim]")
        return
    for m in manual:
        heading = f"## v{m.version} — manual steps (schema v{m.from_schema}→v{m.to_schema})"
        console.print(Markdown(f"{heading}\n\n{m.manual}"))


def _parse_span(span: str) -> tuple[str, str]:
    lo, sep, hi = span.partition("..")
    if not sep:
        raise SquadsError(f"expected a range like v0.1.1..v0.2.0, got {span!r}")
    return lo.strip().lstrip("vV"), hi.strip().lstrip("vV")
