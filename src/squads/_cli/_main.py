"""Top-level commands: init, adopt, list, tree, repair, inbox, sync, workflow, docs, check.

Per-item operations (show/update/status/body/comment/refs + sub-entities) live in the
resource-oriented `sq <type> <num> <verb> …` groups built by `_items.build_item_app`.
"""

import json

import typer
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from squads._cli import app
from squads._cli._common import (
    console,
    e,
    get_service,
    handle_errors,
    parse_status,
    parse_type,
)
from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._paths import number_for_id
from squads._services._service import adopt as svc_adopt
from squads._services._service import init as svc_init


@app.command()
@handle_errors
def init(
    squad_dir: str = typer.Option(
        "squads", "--squad-dir", help="Folder name for the squad's content."
    ),
    backend: str = typer.Option("claude_code", "--backend"),
    roles: str = typer.Option(
        "all", "--roles", help="Bundle (all|core|minimal) or comma-separated slugs."
    ),
    no_claude: bool = typer.Option(False, "--no-claude", help="Skip Claude Code scaffolding."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing .squads.toml."),
):
    """Initialize squads in the current directory."""
    result = svc_init(
        squad_dir=squad_dir, backend=backend, roles_spec=roles, no_claude=no_claude, force=force
    )
    sp = result.paths
    roles_line = ", ".join(r.extra.get(X.SLUG, r.slug) for r in result.roles) or "—"
    lines = [
        f"[bold]squad:[/bold] {sp.squad_dir}",
        f"[bold]index:[/bold] {sp.index_path}",
        f"[bold]roles:[/bold] {roles_line}",
    ]
    if not no_claude:
        lines.append(f"[bold]claude:[/bold] {sp.claude_dir} (pointers + squads skill + CLAUDE.md)")
    console.print(Panel("\n".join(lines), title="squads initialized", expand=False))
    console.print(
        'Next: [cyan]sq create task "…"[/cyan] · [cyan]sq list[/cyan] · [cyan]sq role list[/cyan]'
    )


@app.command()
@handle_errors
def adopt(
    squad_dir: str = typer.Option(
        "squads", "--squad-dir", help="Folder name to adopt (default if no .squads.toml yet)."
    ),
    backend: str = typer.Option("claude_code", "--backend"),
    roles: str = typer.Option(
        "all", "--roles", help="Bundle (all|core|minimal) or comma-separated slugs."
    ),
    no_claude: bool = typer.Option(False, "--no-claude", help="Skip Claude Code scaffolding."),
):
    """Adopt an existing squad-structured folder (non-destructive; imports existing items)."""
    result = svc_adopt(squad_dir=squad_dir, backend=backend, roles_spec=roles, no_claude=no_claude)
    sp = result.paths
    new_roles = ", ".join(r.extra.get(X.SLUG, r.slug) for r in result.roles) or "—"
    lines = [
        f"[bold]squad:[/bold] {sp.squad_dir}",
        f"[bold]imported:[/bold] {result.imported} existing item(s)",
        f"[bold]roles activated:[/bold] {new_roles}",
    ]
    console.print(Panel("\n".join(lines), title="squads adopted", expand=False))
    console.print(
        "Migrate legacy docs with [cyan]sq --at <date> create …[/cyan] to preserve history; "
        "then [cyan]sq check[/cyan]."
    )


@app.command(name="list")
@handle_errors
def list_items(
    type: str | None = typer.Option(None, "--type", "-t"),
    status: str | None = typer.Option(None, "--status", "-s"),
    parent: str | None = typer.Option(None, "--parent"),
    label: str | None = typer.Option(None, "--label"),
    assignee: str | None = typer.Option(None, "--assignee"),
    json_out: bool = typer.Option(False, "--json"),
):
    """List items in a table."""
    svc = get_service()
    items = svc.list_items(
        item_type=parse_type(type) if type else None,
        status=parse_status(status) if status else None,
        parent=parent,
        label=label,
        assignee=assignee,
    )
    if json_out:
        console.print_json(json.dumps([i.model_dump(mode="json") for i in items]))
        return
    if not items:
        console.print("[dim]no items[/dim]")
        return
    table = Table(box=None, pad_edge=False)
    for col in ("ID", "Type", "Status", "Title", "Parent", "Assignee"):
        table.add_column(col)
    for it in items:
        table.add_row(
            it.id,
            it.type.value,
            it.status.value,
            e(it.title),
            it.parent or "",
            e(it.assignee or ""),
        )
    console.print(table)


@app.command()
@handle_errors
def tree(root_id: str | None = typer.Argument(None)):
    """Show the item hierarchy."""
    svc = get_service()
    all_items = {i.id: i for i in svc.list_items()}
    children: dict[str | None, list[Item]] = {}
    for it in all_items.values():
        key = it.parent if it.parent in all_items else None
        children.setdefault(key, []).append(it)

    def label(it: Item) -> str:
        return f"[bold]{it.id}[/bold] {e(it.title)} [dim]({it.status.value})[/dim]"

    def attach(node: Tree, item: Item) -> None:
        for child in sorted(children.get(item.id, []), key=lambda i: number_for_id(i.id)):
            attach(node.add(label(child)), child)

    tree_view = Tree("squad")
    roots = (
        [all_items[root_id]]
        if root_id
        else sorted(children.get(None, []), key=lambda i: number_for_id(i.id))
    )
    for r in roots:
        attach(tree_view.add(label(r)), r)
    console.print(tree_view)


@app.command()
@handle_errors
def repair(renumber: bool = typer.Option(False, "--renumber")):
    """Rebuild the index from the markdown frontmatter."""
    svc = get_service()
    db = svc.repair(renumber=renumber)
    console.print(f"rebuilt index: {len(db.items)} items, counter={db.counter}")


@app.command()
@handle_errors
def inbox(
    role: str = typer.Argument(..., help="Role slug (e.g. qa)."),
    json_out: bool = typer.Option(False, "--json"),
):
    """Open items whose discussion mentions @role."""
    svc = get_service()
    hits = svc.inbox(role)
    if json_out:
        console.print_json(
            json.dumps([{"id": it.id, "title": it.title, "lines": lines} for it, lines in hits])
        )
        return
    if not hits:
        console.print(f"[dim]nothing for @{role.lstrip('@')}[/dim]")
        return
    for it, lines in hits:
        console.print(f"[bold]{it.id}[/bold] {e(it.title)} [dim]({it.status.value})[/dim]")
        for ln in lines:
            console.print(f"    {e(ln)}")


@app.command()
@handle_errors
def sync():
    """Regenerate tool-owned managed files to the current squads version."""
    svc = get_service()
    svc.sync()
    console.print("[green]synced[/green] managed files to this squads version")


@app.command()
def workflow():
    """Print the team workflow cheatsheet (who writes what, how items link)."""
    from rich.markdown import Markdown

    from squads._rendering._engine import render

    console.print(Markdown(render("workflow.md.j2")))


@app.command()
@handle_errors
def docs(
    name: str | None = typer.Argument(None, help="Doc to print (e.g. internals). Omit to list."),
    pretty: bool = typer.Option(False, "--rich", help="Pretty-print instead of raw markdown."),
):
    """Print project documentation in the terminal — offline, no fetch."""
    from squads import _docfiles

    if name is None:
        table = Table(title="squads docs — read with `sq docs <name>`")
        table.add_column("name")
        table.add_column("title")
        for stem, title in _docfiles.available():
            table.add_row(stem, e(title))
        console.print(table)
        return
    content = _docfiles.read(name)
    if pretty:
        from rich.markdown import Markdown

        console.print(Markdown(content))
    else:
        # raw markdown, verbatim: no Rich markup interpretation, no reflow
        console.print(content, markup=False, highlight=False, soft_wrap=True)


@app.command()
@handle_errors
def check():
    """Lint the squad: markers, dangling links, invalid status, index drift."""
    svc = get_service()
    issues = svc.check()
    if not issues:
        console.print("[green]✓ no issues[/green]")
        return
    errors = sum(1 for i in issues if i.level == "error")
    for i in issues:
        color = "red" if i.level == "error" else "yellow"
        loc = f" [dim]{i.item}[/dim]" if i.item else ""
        console.print(f"[{color}]{i.level}[/{color}]{loc}: {i.message}")
    if errors:
        raise typer.Exit(1)
