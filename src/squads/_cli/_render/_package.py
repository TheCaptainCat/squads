"""The package-data renderers: the bundled docs and the migration changelog."""

from rich.console import Console
from rich.table import Table

from squads._api._dto._package import Doc, DocIndex, MigrationIndex, MigrationSteps
from squads._cli._render._style import e


def render_doc_index(index: DocIndex, console: Console) -> None:
    table = Table(title="squads docs — read with `sq docs <name>`")
    table.add_column("name")
    table.add_column("title")
    for doc in index.docs:
        table.add_row(doc.name, e(doc.title))
    console.print(table)


def render_doc(doc: Doc, console: Console, *, pretty: bool) -> None:
    """The doc as markdown with *pretty*, else its text verbatim: no markup, no reflow."""
    if pretty:
        from rich.markdown import Markdown

        console.print(Markdown(doc.markdown))
    else:
        console.print(doc.markdown, markup=False, highlight=False, soft_wrap=True)


def render_migrations(index: MigrationIndex, console: Console) -> None:
    table = Table(title="migration changelog — read steps with `sq migrate chlog vA..vB`")
    for col in ("Release", "Schema", "Summary", "Manual"):
        table.add_column(col)
    for m in index.migrations:
        table.add_row(
            f"v{m.version}",
            f"v{m.from_schema}→v{m.to_schema}",
            e(m.summary),
            "yes" if m.manual else "—",
        )
    console.print(table)


def render_steps(steps: MigrationSteps, console: Console) -> None:
    """Each migration's manual steps under a heading naming its release and schema step."""
    if not steps.migrations:
        console.print(f"[dim]no manual steps for v{steps.from_version}..v{steps.to_version}[/dim]")
        return
    from rich.markdown import Markdown

    for m in steps.migrations:
        heading = f"## v{m.version} — manual steps (schema v{m.from_schema}→v{m.to_schema})"
        console.print(Markdown(f"{heading}\n\n{m.manual}"))
