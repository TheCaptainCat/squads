"""Top-level commands: init, adopt, list, tree, repair, inbox, sync, workflow, docs, check.

Per-item operations (show/update/status/body/comment/refs + sub-entities) live in the
resource-oriented `sq <type> <num> <verb> …` groups built by `_items.build_item_app`.
"""

import json
import sys as _sys
from collections.abc import Callable
from typing import Any

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
    parse_priority,
    parse_status,
    parse_type,
    print_item,
    priority_badge,
    resolve_item_id_any,
    resolve_slug_or_raise,
)
from squads._errors import SquadsError
from squads._models._config import CONFIG_FILENAME
from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._paths import load_config, number_for_id
from squads._roles._catalog import resolve_roles
from squads._services._service import adopt as svc_adopt
from squads._services._service import init as svc_init
from squads._workflow import is_open

# ---------------------------------------------------------------------------
# TTY detection — injectable for testing.
# The default implementation delegates to sys.stdin.isatty().
# Tests can replace this with a monkeypatched callable that returns True/False.
# ---------------------------------------------------------------------------


def _default_is_tty() -> bool:
    return _sys.stdin.isatty()


# Module-level slot; tests monkeypatch this to control TTY behaviour.
_is_tty: Callable[[], bool] = _default_is_tty


# ---------------------------------------------------------------------------
# Name-flag parser
# ---------------------------------------------------------------------------


def _parse_name_flags(raw: list[str]) -> dict[str, str]:
    """Parse a list of ``slug=Full Name`` strings into a dict.

    Raises :class:`~squads._errors.SquadsError` on any malformed entry.
    """
    result: dict[str, str] = {}
    for entry in raw:
        if "=" not in entry:
            raise SquadsError(
                f"--name {entry!r}: expected format slug=Full Name (e.g. architect='Ada Lovelace')"
            )
        slug, _, name = entry.partition("=")
        slug = slug.strip()
        name = name.strip()
        if not slug:
            raise SquadsError(f"--name {entry!r}: slug (before '=') must not be empty")
        if not name:
            raise SquadsError(f"--name {entry!r}: name (after '=') must not be empty")
        result[slug] = name
    return result


def _item_table(items: list[Item]) -> Table:
    """The shared item table (shared by `list`, `search`, `mine`) — escape all dynamic strings."""
    table = Table(box=None, pad_edge=False)
    for col in ("ID", "Type", "Status", "Priority", "Title", "Parent", "Assignee"):
        table.add_column(col)
    for it in items:
        table.add_row(
            it.id,
            it.type.value,
            it.status.value,
            e(priority_badge(it.priority)) if it.priority else "",
            e(it.title),
            it.parent or "",
            e(it.assignee or ""),
        )
    return table


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
    name: list[str] = typer.Option(
        [],
        "--name",
        help="Override a role's name: slug=Full Name (repeatable).",
    ),
    default_names: bool = typer.Option(
        False,
        "--default-names",
        help="Skip interactive prompting; use bundled/pool names for every role.",
    ),
):
    """Initialize squads in the current directory."""
    from pathlib import Path

    # Parse --name slug=Full Name flags.
    names_from_flags = _parse_name_flags(name)

    # Load [init.names] from a pre-existing .squads.toml (e.g. when using --force or when the
    # user has created the file manually before running sq init).  Flags win on conflict.
    names_from_config: dict[str, str] = {}
    config_path = Path.cwd() / CONFIG_FILENAME
    if config_path.is_file():
        try:
            existing_cfg = load_config(config_path)
            names_from_config = existing_cfg.init_names
        except SquadsError:
            pass  # Malformed config — svc_init will raise AlreadyInitializedError or SquadsError.

    # Determine whether to prompt interactively.
    # Rule: prompt if (TTY and not --default-names), else skip.
    interactive = _is_tty() and not default_names

    # Collect the full set of role slugs that will be activated.
    role_defs = resolve_roles(roles) if roles else []

    # Build the combined names map: config < flags (flags win).
    # A slug already covered by either source is not asked interactively.
    combined_names: dict[str, str] = {**names_from_config, **names_from_flags}

    if interactive:
        for rdef in role_defs:
            slug = rdef.slug
            if slug in combined_names:
                # Already supplied via flag — skip prompt.
                continue
            # Prompt: show the default name, allow blank to keep it.
            default_name = rdef.full_name
            typed = typer.prompt(
                f"Name for {slug!r} (Enter to keep default '{default_name}')",
                default="",
                show_default=False,
            ).strip()
            if typed:
                combined_names[slug] = typed

    result = svc_init(
        squad_dir=squad_dir,
        backend=backend,
        roles_spec=roles,
        no_claude=no_claude,
        force=force,
        names=combined_names if combined_names else None,
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
        'Next: [cyan]sq create task "…"[/cyan] · [cyan]sq list[/cyan]'
        " · [cyan]sq role catalog[/cyan]"
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
    priority: str | None = typer.Option(None, "--priority", help="urgent|high|medium|low."),
    all_: bool = typer.Option(False, "--all", "-a", help="Include closed (done/cancelled) items."),
    json_out: bool = typer.Option(False, "--json"),
):
    """List items in a table (closed items are hidden unless --all or --status is given)."""
    svc = get_service()
    validated_assignee = resolve_slug_or_raise(assignee, svc) if assignee else None
    resolved_parent = resolve_item_id_any(parent, svc) if parent else None
    items = svc.list_items(
        item_type=parse_type(type) if type else None,
        status=parse_status(status) if status else None,
        parent=resolved_parent,
        label=label,
        assignee=validated_assignee,
        priority=parse_priority(priority) if priority else None,
    )
    if not (all_ or status):
        items = [i for i in items if is_open(i.status)]
    if json_out:
        console.print_json(json.dumps([i.model_dump(mode="json") for i in items]))
        return
    if not items:
        console.print("[dim]no items[/dim]")
        return
    console.print(_item_table(items))


def _build_children(
    listed: list[Item],
) -> dict[str | None, list[Item]]:
    """Group items by their canonical parent ID (width-tolerant).

    ``item.parent`` stores the old zero-pad width after a ``sq migrate repad`` while
    ``item.id`` uses the current width.  Resolving via sequence number makes the tree
    correct across a repad boundary (FEAT-000027 / TASK-000103).
    """
    all_ids = {i.id for i in listed}
    seq_to_id = {number_for_id(i.id): i.id for i in listed}
    children: dict[str | None, list[Item]] = {}
    for it in listed:
        parent_canonical: str | None = None
        if it.parent:
            canonical = seq_to_id.get(number_for_id(it.parent))
            if canonical is not None and canonical in all_ids:
                parent_canonical = canonical
        children.setdefault(parent_canonical, []).append(it)
    return children


@app.command()
@handle_errors
def tree(
    root_id: str | None = typer.Argument(None),
    all_: bool = typer.Option(False, "--all", "-a", help="Include closed (done/cancelled) items."),
    json_out: bool = typer.Option(False, "--json", help="Emit the nested subtree as JSON."),
):
    """Show the item hierarchy (closed items are hidden unless --all).

    `--json` emits the subtree (`id/type/status/priority/assignee/blocked` + nested `children`) —
    the read an orchestrating agent uses to see a feature's state and decide what to do next.
    """
    svc = get_service()
    # Resolve root_id early so bare numbers work and unknown IDs get a clear error.
    resolved_root: str | None = None
    if root_id is not None:
        resolved_root = resolve_item_id_any(root_id, svc)
    listed = svc.list_items()
    if not all_:
        listed = [i for i in listed if is_open(i.status)]
    all_items = {i.id: i for i in listed}
    children = _build_children(listed)

    def kids(item_id: str) -> list[Item]:
        return sorted(children.get(item_id, []), key=lambda i: number_for_id(i.id))

    if resolved_root and resolved_root not in all_items:
        raise SquadsError(
            f"no {'item' if all_ else 'open item'} {resolved_root!r} to root the tree"
            " (add --all to include closed items, or check it exists)"
        )
    roots = (
        [all_items[resolved_root]]
        if resolved_root
        else sorted(children.get(None, []), key=lambda i: number_for_id(i.id))
    )

    if json_out:
        blocked_ids = {t.id for t, _ in svc.blocked()}

        def node(it: Item) -> dict[str, Any]:
            return {
                "id": it.id,
                "type": it.type.value,
                "status": it.status.value,
                "priority": it.priority.value if it.priority else None,
                "assignee": it.assignee,
                "blocked": it.id in blocked_ids,
                "children": [node(c) for c in kids(it.id)],
            }

        console.print_json(json.dumps([node(r) for r in roots]))
        return

    def label(it: Item) -> str:
        prio = f"{e(priority_badge(it.priority))} · " if it.priority else ""
        return f"[bold]{it.id}[/bold] {prio}{e(it.title)} [dim]({it.status.value})[/dim]"

    def attach(parent: Tree, item: Item) -> None:
        for child in kids(item.id):
            attach(parent.add(label(child)), child)

    tree_view = Tree("squad")
    for r in roots:
        attach(tree_view.add(label(r)), r)
    console.print(tree_view)


@app.command()
@handle_errors
def repair(renumber: bool = typer.Option(False, "--renumber")):
    """Rebuild the index from the markdown frontmatter."""
    svc = get_service()
    result = svc.repair(renumber=renumber)
    console.print(f"rebuilt index: {len(result.db.items)} items, counter={result.db.counter}")
    for mid in result.missing_ids:
        console.print(
            f"[yellow]warn[/yellow] [dim]{mid}[/dim]: indexed but no markdown file found (deleted?)"
        )


@app.command()
@handle_errors
def inbox(
    role: str = typer.Argument(..., help="Role slug (e.g. qa)."),
    json_out: bool = typer.Option(False, "--json"),
):
    """Open items whose discussion mentions @role."""
    svc = get_service()
    slug = resolve_slug_or_raise(role, svc)
    hits = svc.inbox(slug)
    if json_out:
        console.print_json(
            json.dumps([{"id": it.id, "title": it.title, "lines": lines} for it, lines in hits])
        )
        return
    if not hits:
        console.print(f"[dim]nothing for @{slug}[/dim]")
        return
    for it, lines in hits:
        console.print(f"[bold]{it.id}[/bold] {e(it.title)} [dim]({it.status.value})[/dim]")
        for ln in lines:
            console.print(f"    {e(ln)}")


@app.command()
@handle_errors
def search(
    text: str = typer.Argument(..., help="Text to find (case-insensitive)."),
    type: str | None = typer.Option(None, "--type", "-t"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Search item titles, summaries, and bodies/discussion for text."""
    svc = get_service()
    hits = svc.search(text, item_type=parse_type(type) if type else None)
    if json_out:
        console.print_json(
            json.dumps([{"id": it.id, "title": it.title, "hits": lines} for it, lines in hits])
        )
        return
    if not hits:
        console.print(f"[dim]no matches for {e(text)}[/dim]")
        return
    for it, lines in hits:
        console.print(f"[bold]{it.id}[/bold] {e(it.title)} [dim]({it.status.value})[/dim]")
        for ln in lines[:3]:
            console.print(f"    {e(ln)}")


@app.command()
@handle_errors
def blocked(json_out: bool = typer.Option(False, "--json")):
    """Show open items blocked by other open items (via the `blocks` ref kind)."""
    svc = get_service()
    rows = svc.blocked()
    if json_out:
        console.print_json(
            json.dumps(
                [
                    {
                        "id": t.id,
                        "title": t.title,
                        "blockers": [
                            {"id": b.id, "title": b.title, "status": b.status.value} for b in bs
                        ],
                    }
                    for t, bs in rows
                ]
            )
        )
        return
    if not rows:
        console.print("[dim]nothing blocked[/dim]")
        return
    for target, blockers in rows:
        console.print(
            f"[bold]{target.id}[/bold] {e(target.title)} [dim]({target.status.value})[/dim]"
        )
        for b in blockers:
            console.print(
                f"    [red]blocked by[/red] {b.id} {e(b.title)} [dim]({b.status.value})[/dim]"
            )


@app.command()
@handle_errors
def workload(json_out: bool = typer.Option(False, "--json")):
    """Per-assignee open/closed/total work-item counts (busiest first)."""
    svc = get_service()
    rows = svc.workload()
    if json_out:
        console.print_json(
            json.dumps(
                [
                    {"assignee": r.assignee, "open": r.open, "closed": r.closed, "total": r.total}
                    for r in rows
                ]
            )
        )
        return
    if not rows:
        console.print("[dim]no items[/dim]")
        return
    table = Table(box=None, pad_edge=False)
    for col in ("Assignee", "Open", "Closed", "Total"):
        table.add_column(col)
    for r in rows:
        table.add_row(e(r.assignee or "(unassigned)"), str(r.open), str(r.closed), str(r.total))
    console.print(table)


@app.command()
@handle_errors
def mine(
    role: str = typer.Argument(..., help="Role slug (e.g. python-dev or op-pierre)."),
    all_: bool = typer.Option(False, "--all", "-a", help="Include closed items."),
    json_out: bool = typer.Option(False, "--json"),
):
    """Items assigned to a role slug."""
    svc = get_service()
    slug = resolve_slug_or_raise(role, svc)
    items = svc.list_items(assignee=slug)
    if not all_:
        items = [i for i in items if is_open(i.status)]
    if json_out:
        console.print_json(json.dumps([i.model_dump(mode="json") for i in items]))
        return
    if not items:
        console.print(f"[dim]nothing assigned to {e(slug)}[/dim]")
        return
    console.print(_item_table(items))


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

    from squads._models._enums import TYPE_ALIASES
    from squads._rendering._engine import render

    console.print(Markdown(render("workflow.md.j2", type_aliases=TYPE_ALIASES)))


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


@app.command(name="show")
@handle_errors
def show_any(
    item_id: str = typer.Argument(
        ..., metavar="ID", help="Item ID (e.g. FEAT-000013) or bare number (e.g. 13)."
    ),
    json_out: bool = typer.Option(False, "--json"),
    raw: bool = typer.Option(
        False, "--raw", help="Plain text output (opt out of markdown render)."
    ),
    comments: bool = typer.Option(
        False, "--comments", help="Append the discussion as comment panes."
    ),
    full: bool = typer.Option(False, "--full", help="Add one pane per sub-entity (body + badges)."),
):
    """Show any work item by ID or bare number, regardless of type.

    Accepts both the full ID (e.g. ``FEAT-000013``) and a bare sequence number (e.g. ``13``).
    Unknown IDs error cleanly.
    """
    svc = get_service()
    resolved_id = resolve_item_id_any(item_id, svc)
    it = svc.get(resolved_id)
    if json_out:
        console.print_json(it.model_dump_json())
        return
    print_item(svc, it, raw=raw, comments=comments, full=full)


@app.command()
@handle_errors
def check(json_out: bool = typer.Option(False, "--json")):
    """Lint the squad: markers, dangling links, invalid status, index drift.

    Exit codes: 0 = clean (or warnings only), 3 = one or more error-level issues found.
    See `sq docs faq` for the full exit-code table.
    """
    svc = get_service()
    issues = svc.check()
    if json_out:
        console.print_json(
            json.dumps([{"level": i.level, "item": i.item, "message": i.message} for i in issues])
        )
        errors = sum(1 for i in issues if i.level == "error")
        if errors:
            raise typer.Exit(3)
        return
    if not issues:
        console.print("[green]✓ no issues[/green]")
        return
    errors = sum(1 for i in issues if i.level == "error")
    for i in issues:
        color = "red" if i.level == "error" else "yellow"
        loc = f" [dim]{i.item}[/dim]" if i.item else ""
        console.print(f"[{color}]{i.level}[/{color}]{loc}: {i.message}")
    if errors:
        raise typer.Exit(3)
