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

import squads._cli._common as common
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
    print_json_clean,
    priority_badge,
    resolve_item_id_any,
    resolve_slug_or_raise,
)
from squads._errors import SquadsError
from squads._models._config import CONFIG_FILENAME
from squads._models._enums import Priority
from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._paths import load_config
from squads._roles._catalog import resolve_roles
from squads._services._base import ItemFilter
from squads._services._refs import graph_to_dot, graph_to_mermaid
from squads._services._results import GraphNode, ReflogEntry, TreeNode
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


def _parse_backend_option(raw: list[str]) -> list[str]:
    """Parse the repeatable ``--backend`` values into an ``active_backends`` list.

    ``--backend none`` (case-insensitive) means sq-only (no backends → ``[]``).
    Combining ``none`` with a real backend name raises :class:`~squads._errors.SquadsError`.
    Empty input defaults to ``["claude_code"]``.
    """
    if not raw:
        return ["claude_code"]
    lowered = [v.lower() for v in raw]
    has_none = "none" in lowered
    real = [v for v in raw if v.lower() != "none"]
    if has_none and real:
        raise SquadsError(
            "--backend none cannot be combined with a real backend name "
            f"(got: {', '.join(real)}). Use --backend none alone for a sq-only squad."
        )
    return [] if has_none else raw


@app.command()
@common.command
async def init(
    squad_dir: str = typer.Option(
        "squads", "--squad-dir", help="Folder name for the squad's content."
    ),
    backend: list[str] = typer.Option(
        [],
        "--backend",
        help=(
            "Active backend(s): repeatable (e.g. --backend claude_code --backend agents_md). "
            "Use --backend none for a sq-only squad (no agent files)."
        ),
    ),
    roles: str = typer.Option(
        "all", "--roles", help="Bundle (all|core|minimal) or comma-separated slugs."
    ),
    no_claude: bool = typer.Option(False, "--no-claude", help="Skip Claude Code scaffolding."),
    no_seed_skills: bool = typer.Option(
        False,
        "--no-seed-skills",
        help="Skip stamping SKILL ids onto bundled skill files (for test compatibility).",
        hidden=True,
    ),
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

    # Parse --backend flags (repeatable; "none" sentinel → sq-only squad).
    active_backends = _parse_backend_option(backend)

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
            try:
                typed = typer.prompt(
                    f"Name for {slug!r} (Enter to keep default '{default_name}')",
                    default="",
                    show_default=False,
                ).strip()
            except typer.Abort, EOFError:
                # On Windows, sys.stdin.isatty() may report a console even inside a
                # subprocess with a closed/empty stdin pipe, causing typer.prompt to
                # raise EOFError (or typer.Abort) on the first read. Degrade gracefully:
                # fall back to bundled defaults and stop prompting rather than aborting
                # the whole init.
                break
            if typed:
                combined_names[slug] = typed

    result = await svc_init(
        squad_dir=squad_dir,
        backend=active_backends,
        roles_spec=roles,
        no_claude=no_claude,
        force=force,
        names=combined_names if combined_names else None,
        _skip_skill_seed=no_seed_skills,
    )
    sp = result.paths
    roles_line = ", ".join(r.extra.get(X.SLUG, r.slug) for r in result.roles) or "—"
    lines = [
        f"[bold]squad:[/bold] {sp.squad_dir}",
        f"[bold]index:[/bold] {sp.index_path}",
        f"[bold]roles:[/bold] {roles_line}",
    ]
    if sp.config.active_backends:
        backends_str = ", ".join(sp.config.active_backends)
        lines.append(f"[bold]agent backends:[/bold] {backends_str}")
    else:
        lines.append("[bold]agent backends:[/bold] (none)")
    console.print(Panel("\n".join(lines), title="squads initialized", expand=False))
    console.print(
        'Next: [cyan]sq create task "…"[/cyan] · [cyan]sq list[/cyan]'
        " · [cyan]sq role catalog[/cyan]"
    )


@app.command()
@common.command
async def adopt(
    squad_dir: str = typer.Option(
        "squads", "--squad-dir", help="Folder name to adopt (default if no .squads.toml yet)."
    ),
    backend: list[str] = typer.Option(
        [],
        "--backend",
        help=(
            "Active backend(s): repeatable (e.g. --backend claude_code --backend agents_md). "
            "Use --backend none for a sq-only squad (no agent files)."
        ),
    ),
    roles: str = typer.Option(
        "all", "--roles", help="Bundle (all|core|minimal) or comma-separated slugs."
    ),
    no_claude: bool = typer.Option(False, "--no-claude", help="Skip Claude Code scaffolding."),
):
    """Adopt an existing squad-structured folder (non-destructive; imports existing items)."""
    active_backends = _parse_backend_option(backend)
    result = await svc_adopt(
        squad_dir=squad_dir, backend=active_backends, roles_spec=roles, no_claude=no_claude
    )
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
@common.command
async def list_items(
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
    validated_assignee = await resolve_slug_or_raise(assignee, svc) if assignee else None
    resolved_parent = await resolve_item_id_any(parent, svc) if parent else None
    items = await svc.list_items(
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
        print_json_clean(json.dumps([i.model_dump(mode="json") for i in items]))
        return
    if not items:
        console.print("[dim]no items[/dim]")
        return
    console.print(_item_table(items))


@app.command()
@common.command
async def tree(
    root_id: str | None = typer.Argument(None),
    type: str | None = typer.Option(None, "--type", "-t"),
    status: str | None = typer.Option(None, "--status", "-s"),
    assignee: str | None = typer.Option(None, "--assignee"),
    priority: str | None = typer.Option(None, "--priority", help="urgent|high|medium|low."),
    depth: int | None = typer.Option(None, "--depth", help="Maximum depth from root (root = 0)."),
    all_: bool = typer.Option(False, "--all", "-a", help="Include closed (done/cancelled) items."),
    json_out: bool = typer.Option(False, "--json", help="Emit the nested subtree as JSON."),
):
    """Show the item hierarchy (closed items are hidden unless --all or --status is given).

    Filters (--type, --status, --assignee, --priority) narrow the tree to matching nodes;
    ancestor paths are always preserved so every match shows in context (ancestors that only
    serve as path are rendered dimmed).  --depth N limits the tree to N levels from the root.

    `--json` emits the subtree (`id/type/status/priority/assignee/blocked` + nested `children`) —
    the read an orchestrating agent uses to see a feature's state and decide what to do next.
    """
    svc = get_service()
    # Resolve root_id early so bare numbers work and unknown IDs get a clear error.
    resolved_root: str | None = None
    if root_id is not None:
        resolved_root = await resolve_item_id_any(root_id, svc)
    validated_assignee = await resolve_slug_or_raise(assignee, svc) if assignee else None

    # Mirror list's closed-item gate exactly:
    #   --status filter (or --all) reveals matching closed items;
    #   --priority / --assignee / --type alone do NOT widen to closed.
    include_closed = bool(all_ or status)

    item_filter = ItemFilter(
        item_type=parse_type(type) if type else None,
        status=parse_status(status) if status else None,
        assignee=validated_assignee,
        priority=parse_priority(priority) if priority else None,
    )

    nodes = await svc.tree_view(
        resolved_root,
        filter=item_filter,
        depth=depth,
        include_closed=include_closed,
    )

    if json_out:
        blocked_ids = {t.id for t, _ in await svc.blocked()}

        def node(tn: TreeNode) -> dict[str, Any]:
            it = tn.item
            return {
                "id": it.id,
                "type": it.type.value,
                "status": it.status.value,
                "priority": it.priority.value if it.priority else None,
                "assignee": it.assignee,
                "blocked": it.id in blocked_ids,
                "children": [node(c) for c in tn.children],
            }

        print_json_clean(json.dumps([node(n) for n in nodes]))
        return

    def _label(it: Item, path_only: bool) -> str:
        prio = f"{e(priority_badge(it.priority))} · " if it.priority else ""
        base = f"[bold]{it.id}[/bold] {prio}{e(it.title)} [dim]({it.status.value})[/dim]"
        if path_only:
            return f"[dim]{base}[/dim]"
        return base

    def _attach(parent: Tree, tn: TreeNode) -> None:
        branch = parent.add(_label(tn.item, tn.path_only))
        for child in tn.children:
            _attach(branch, child)

    rich_tree = Tree("squad")
    for n in nodes:
        _attach(rich_tree, n)
    console.print(rich_tree)


@app.command()
@common.command
async def repair(renumber: bool = typer.Option(False, "--renumber")):
    """Rebuild the index from the markdown frontmatter."""
    svc = get_service()
    result = await svc.repair(renumber=renumber)
    console.print(f"rebuilt index: {len(result.db.items)} items, counter={result.db.counter}")
    for mid in result.missing_ids:
        console.print(
            f"[yellow]warn[/yellow] [dim]{mid}[/dim]: indexed but no markdown file found (deleted?)"
        )


@app.command()
@common.command
async def inbox(
    role: str = typer.Argument(..., help="Role slug (e.g. qa)."),
    json_out: bool = typer.Option(False, "--json"),
):
    """Open items whose discussion mentions @role."""
    svc = get_service()
    slug = await resolve_slug_or_raise(role, svc)
    hits = await svc.inbox(slug)
    if json_out:
        print_json_clean(
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
@common.command
async def search(
    text: str = typer.Argument(..., help="Text to find (case-insensitive)."),
    type: str | None = typer.Option(None, "--type", "-t"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Search item titles, summaries, and bodies/discussion for text."""
    svc = get_service()
    hits = await svc.search(text, item_type=parse_type(type) if type else None)
    if json_out:
        print_json_clean(
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
@common.command
async def blocked(json_out: bool = typer.Option(False, "--json")):
    """Show open items blocked by other open items (via the `blocks` ref kind)."""
    svc = get_service()
    rows = await svc.blocked()
    if json_out:
        print_json_clean(
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


def _graph_edge_label(edge_kind: str, direction: str) -> str:
    """Return the human-readable branch label for a graph edge.

    Dependency edges (``edge_kind="depends-on"``) are surfaced as a two-way binding:

    - ``direction="out"`` → the expanded node depends on the child → ``"depends on"``
    - ``direction="in"``  → the child depends on the expanded node → ``"required by"``

    All other kinds show the kind name verbatim (e.g. ``"related"``, ``"fixes"``).
    The raw strings ``"depends-on"`` and ``"blocks"`` are never shown as labels.
    """
    if edge_kind == "depends-on":
        return "depends on" if direction == "out" else "required by"
    return edge_kind


def _attach_graph_node(parent_tree: Tree, node: GraphNode) -> None:
    """Recursively attach a GraphNode's children to a Rich Tree node."""
    for child in node.children:
        # Build the branch label
        if child.edge_kind is not None and child.direction is not None:
            label_text = _graph_edge_label(child.edge_kind, child.direction)
            edge_part = f" [dim]({e(label_text)})[/dim]"
        else:
            edge_part = ""

        prio = f"{e(priority_badge(Priority(child.priority)))} · " if child.priority else ""
        seen_mark = " [dim](seen)[/dim]" if child.seen else ""
        node_label = f"{edge_part} [bold]{child.id}[/bold] {prio}{e(child.status)}{seen_mark}"
        branch = parent_tree.add(node_label)
        if not child.seen:
            _attach_graph_node(branch, child)


@app.command()
@common.command
async def graph(
    root_id: str = typer.Argument(..., metavar="ID", help="Item ID or bare number."),
    depth: int = typer.Option(2, "--depth", "-d", help="BFS depth (default 2; 0 = root only)."),
    kind: list[str] = typer.Option(
        [],
        "--kind",
        "-k",
        help="Ref kind to follow (repeatable; default all).",
    ),
    direction: str = typer.Option(
        "both",
        "--direction",
        help="'out' (forward refs), 'in' (backrefs), or 'both' (default).",
    ),
    all_: bool = typer.Option(False, "--all", "-a", help="Include closed items."),
    json_out: bool = typer.Option(False, "--json"),
    format_: str = typer.Option(
        "",
        "--format",
        help="Export format: 'dot' or 'mermaid' (overrides Rich tree).",
    ),
):
    """Show the ref graph around an item (ego-centric BFS traversal).

    ``--json`` emits a nested root object (``id/type/status/priority/assignee/edge_kind/
    direction/seen/children``) — the read surface for agents and orchestrators. Shape::

        {
          "id": "BUG-000022", "type": "bug", "status": "Open", "priority": "high",
          "assignee": null, "edge_kind": null, "direction": null, "seen": false,
          "children": [
            { "id": "FEAT-000035", ..., "edge_kind": "depends-on", "direction": "out",
              "seen": false, "children": [...] },
            { "id": "TASK-000100", ..., "edge_kind": "related", "direction": "in",
              "seen": true, "children": [] }
          ]
        }

    ``edge_kind`` for dependency edges is always ``"depends-on"`` (never ``"blocks"``);
    ``direction="out"`` means the root depends on the child, ``direction="in"`` means the
    child depends on the root.  In the Rich tree these render as human-readable labels:
    ``"depends on"`` and ``"required by"`` respectively.

    ``--format dot|mermaid`` emits a serialized graph instead of the Rich tree; suitable
    for piping to ``dot``, ``mmdc``, or pasting into Mermaid Live.
    """
    if format_ and format_ not in ("dot", "mermaid"):
        raise SquadsError(f"invalid --format {format_!r}; expected 'dot' or 'mermaid'")

    svc = get_service()
    resolved_id = await resolve_item_id_any(root_id, svc)
    kinds_filter: set[str] | None = set(kind) if kind else None

    root_node = await svc.graph(
        resolved_id,
        depth=depth,
        kinds=kinds_filter,
        direction=direction,
        include_closed=all_,
    )

    if json_out:
        print_json_clean(json.dumps(root_node.to_dict()))
        return

    if format_ == "dot":
        console.print(graph_to_dot(root_node), markup=False, highlight=False)
        return

    if format_ == "mermaid":
        console.print(graph_to_mermaid(root_node), markup=False, highlight=False)
        return

    # Rich tree rendering
    prio = f"{e(priority_badge(Priority(root_node.priority)))} · " if root_node.priority else ""
    root_label = f"[bold]{root_node.id}[/bold] {prio}{e(root_node.status)}"
    tree_view = Tree(root_label)
    _attach_graph_node(tree_view, root_node)
    console.print(tree_view)


@app.command()
@common.command
async def workload(json_out: bool = typer.Option(False, "--json")):
    """Per-assignee open/closed/total work-item counts (busiest first)."""
    svc = get_service()
    rows = await svc.workload()
    if json_out:
        print_json_clean(
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
@common.command
async def mine(
    role: str = typer.Argument(..., help="Role slug (e.g. python-dev or op-pierre)."),
    all_: bool = typer.Option(False, "--all", "-a", help="Include closed items."),
    json_out: bool = typer.Option(False, "--json"),
):
    """Items assigned to a role slug."""
    svc = get_service()
    slug = await resolve_slug_or_raise(role, svc)
    items = await svc.list_items(assignee=slug)
    if not all_:
        items = [i for i in items if is_open(i.status)]
    if json_out:
        print_json_clean(json.dumps([i.model_dump(mode="json") for i in items]))
        return
    if not items:
        console.print(f"[dim]nothing assigned to {e(slug)}[/dim]")
        return
    console.print(_item_table(items))


@app.command()
@common.command
async def sync():
    """Regenerate tool-owned managed files to the current squads version."""
    svc = get_service()
    await svc.sync()
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


@app.command()
@common.command
async def reflog(
    item: str | None = typer.Option(
        None,
        "--item",
        help="Filter by target item ID (e.g. TASK-000042).",
        metavar="ID",
    ),
    actor: str | None = typer.Option(
        None,
        "--actor",
        help="Filter by actor slug (e.g. python-dev, system).",
    ),
    op: str | None = typer.Option(
        None,
        "--op",
        help="Filter by op name (create/status/update/body/comment/subentity/ref/link"
        "/remove/repair/migrate).",
    ),
    since: str | None = typer.Option(
        None,
        "--since",
        help="Include only entries at or after this ISO-8601 timestamp.",
        metavar="WHEN",
    ),
    tail: int = typer.Option(
        50,
        "--tail",
        "-n",
        help="Maximum number of entries to show (most recent; 0 = all).",
    ),
    tree_view: bool = typer.Option(
        False,
        "--tree",
        help=(
            "Render a spawn-lineage tree grouped by session_id/parent_session_id edges. "
            "BEST-EFFORT, UNTRUSTED, OBSERVABILITY-ONLY — reflects declared lineage; "
            "a copied session id appears as a legitimate edge. "
            "Missing intermediate sessions degrade to a forest (multiple roots), never an error."
        ),
    ),
    json_out: bool = typer.Option(False, "--json"),
):
    """Show the operation reflog — a chronological log of every mutating sq command.

    Tails the most recent entries by default (``--tail 50``); use ``--tail 0`` for
    all.  Filters are AND-ed: ``--item TASK-000042 --op status`` shows only status
    changes on that item.

    A squad with no reflog (pre-FEAT-000024 or first run) prints empty results —
    never an error.  A truncated or partially-written reflog is tolerated silently.

    **Exit codes:** 0 = normal; 1 = error; see ``sq docs faq`` for the full table.
    """
    from squads._clock import parse_iso

    svc = get_service()
    since_ts: str | None = None
    if since:
        try:
            from squads import _clock as clock

            since_ts = clock.iso(parse_iso(since))
        except ValueError:
            from squads._cli._common import err_console

            err_console.print(
                f"[red]error:[/red] invalid --since timestamp {since!r} "
                "(use ISO 8601, e.g. 2026-01-15 or 2026-01-15T09:30:00Z)"
            )
            raise typer.Exit(1) from None

    entries: list[ReflogEntry] = await svc.read_reflog(
        item=item,
        actor_filter=actor,
        op_filter=op,
        since=since_ts,
        tail=tail if tail > 0 else None,
    )

    if json_out:
        import dataclasses

        print_json_clean(
            json.dumps(
                [dataclasses.asdict(entry) for entry in entries],
                ensure_ascii=False,
            )
        )
        return

    if tree_view:
        _render_reflog_tree(entries)
        return

    if not entries:
        console.print("[dim]no reflog entries[/dim]")
        return

    for entry in entries:
        delta_str = json.dumps(entry.delta, separators=(",", ":"), ensure_ascii=False)
        console.print(
            f"[dim]{e(entry.ts)}[/dim]  [bold]{e(entry.op)}[/bold]"
            f"  [cyan]{e(entry.target)}[/cyan]"
            f"  [dim]actor={e(entry.actor)}[/dim]  {e(delta_str)}"
        )


def _reflog_entry_line(entry: ReflogEntry) -> str:
    """Format a single reflog entry as a Rich-markup line for tree display."""
    delta_str = json.dumps(entry.delta, separators=(",", ":"), ensure_ascii=False)
    return (
        f"[dim]{e(entry.ts)}[/dim]  [bold]{e(entry.op)}[/bold]"
        f"  [cyan]{e(entry.target)}[/cyan]"
        f"  [dim]actor={e(entry.actor)}[/dim]  {e(delta_str)}"
    )


def _build_session_maps(
    entries: list[ReflogEntry],
) -> tuple[
    dict[str, list[ReflogEntry]],
    dict[str, str | None],
    dict[str, list[str]],
    list[ReflogEntry],
]:
    """Partition entries into session buckets and build parent/children maps.

    Returns:
        session_entries:  session_id → entries in that session
        session_parents:  session_id → parent_session_id (first-occurrence wins)
        children_map:     session_id → list of child session_ids
        no_session:       entries that carry no session_id at all
    """
    session_entries: dict[str, list[ReflogEntry]] = {}
    session_parents: dict[str, str | None] = {}
    no_session: list[ReflogEntry] = []

    for entry in entries:
        sid = entry.session_id
        if sid is None:
            no_session.append(entry)
        else:
            session_entries.setdefault(sid, []).append(entry)
            if sid not in session_parents:
                session_parents[sid] = entry.parent_session_id

    known = set(session_entries.keys())
    children_map: dict[str, list[str]] = {}
    for sid in session_entries:
        p = session_parents.get(sid)
        if p and p in known:
            children_map.setdefault(p, []).append(sid)

    return session_entries, session_parents, children_map, no_session


def _attach_session_node(
    parent_node: Tree,
    sid: str,
    session_entries: dict[str, list[ReflogEntry]],
    children_map: dict[str, list[str]],
    visited: set[str],
) -> None:
    """Recursively attach child session nodes under *parent_node*.

    *visited* is updated in-place as nodes are attached.  The guard prevents
    revisiting a node so the recursion cannot loop even on cyclic edge inputs.
    """
    for child_sid in sorted(children_map.get(sid, [])):
        if child_sid in visited:
            continue
        visited.add(child_sid)
        child_node = parent_node.add(f"[dim]session:[/dim] {e(child_sid)}")
        for child_entry in session_entries.get(child_sid, []):
            child_node.add(_reflog_entry_line(child_entry))
        _attach_session_node(child_node, child_sid, session_entries, children_map, visited)


def _render_reflog_tree(entries: list[ReflogEntry]) -> None:
    """Render reflog entries as a spawn-lineage tree grouped by session edges.

    Best-effort, untrusted, observability-only.  Reflects declared lineage only —
    a copied session id appears as a legitimate edge; a missing intermediate session
    degrades to a forest (extra roots), never an error.  Entries with no session_id
    are grouped as slug-only roots.
    """
    console.print("[dim]Spawn-lineage tree — BEST-EFFORT / UNTRUSTED / OBSERVABILITY-ONLY[/dim]")
    console.print(
        "[dim]Reflects declared lineage; no tamper-evidence or enforcement guarantee.[/dim]"
    )
    console.print()

    if not entries:
        console.print("[dim]no reflog entries[/dim]")
        return

    session_entries, session_parents, children_map, no_session = _build_session_maps(entries)
    known_sessions = set(session_entries.keys())

    tree_root = Tree("[dim]reflog[/dim]")
    visited: set[str] = set()

    # Attach session-based roots (sessions whose parent is absent or outside the view).
    for sid in sorted(session_entries.keys()):
        p = session_parents.get(sid)
        if p is None or p not in known_sessions:
            if p and p not in known_sessions:
                root_label = (
                    f"[dim]session:[/dim] {e(sid)}"
                    f"  [dim](parent {e(p)} not in view — forest root)[/dim]"
                )
            else:
                root_label = f"[dim]session:[/dim] {e(sid)}"
            visited.add(sid)
            root_node = tree_root.add(root_label)
            for root_entry in session_entries.get(sid, []):
                root_node.add(_reflog_entry_line(root_entry))
            _attach_session_node(root_node, sid, session_entries, children_map, visited)

    # Reachability pass — any session not yet visited (e.g. pure cycles in forged/corrupt
    # declared edges) is surfaced here so no recorded session is silently discarded.
    for sid in sorted(session_entries.keys()):
        if sid in visited:
            continue
        visited.add(sid)
        p = session_parents.get(sid)
        cycle_label = (
            f"[dim]session:[/dim] {e(sid)}  [dim](parent {e(p)} — cycle/forest root)[/dim]"
            if p
            else f"[dim]session:[/dim] {e(sid)}  [dim](cycle/forest root)[/dim]"
        )
        cycle_node = tree_root.add(cycle_label)
        for cycle_entry in session_entries.get(sid, []):
            cycle_node.add(_reflog_entry_line(cycle_entry))
        _attach_session_node(cycle_node, sid, session_entries, children_map, visited)

    # Attach no-session entries as individual roots.
    for entry in no_session:
        slug_node = tree_root.add(
            f"[dim]actor=[/dim]{e(entry.actor)}  [dim](no session recorded)[/dim]"
        )
        slug_node.add(_reflog_entry_line(entry))

    console.print(tree_root)


@app.command(name="show")
@common.command
async def show_any(
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
    resolved_id = await resolve_item_id_any(item_id, svc)
    it = await svc.get(resolved_id)
    if json_out:
        print_json_clean(it.model_dump_json())
        return
    await print_item(svc, it, raw=raw, comments=comments, full=full)


@app.command()
@common.command
async def check(json_out: bool = typer.Option(False, "--json")):
    """Lint the squad: markers, dangling links, invalid status, index drift.

    Exit codes: 0 = clean (or warnings only), 3 = one or more error-level issues found.
    See `sq docs faq` for the full exit-code table.
    """
    svc = get_service()
    issues = await svc.check()
    if json_out:
        print_json_clean(
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
