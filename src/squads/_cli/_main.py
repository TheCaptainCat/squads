"""Top-level commands: init, adopt, list, tree, repair, inbox, sync, docs, check.

Per-item operations (show/update/status/body/comment/refs + sub-entities) live in the
resource-oriented `sq <type> <num> <verb> …` groups built by `_items.build_item_app`.

The ``workflow`` command group (cheatsheet + lint) lives in ``_workflow_cmd.py`` and is
registered as a Typer sub-app in ``_cli/__init__.py``.
"""

import json
import math
import sys
from collections.abc import Callable
from typing import Any

import typer
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

import squads._cli._common as common
from squads import _badges as badges
from squads._badges import resolve_badges as resolve_item_badges
from squads._cli import app
from squads._cli._common import (
    build_item_json,
    console,
    e,
    get_active_spec,
    get_service,
    handle_errors,
    parse_badge_code,
    parse_category,
    parse_status,
    parse_type,
    print_item,
    print_json_clean,
    resolve_item_id_any,
    resolve_slug_or_raise,
    status_text,
)
from squads._errors import SquadsError
from squads._models._config import CONFIG_FILENAME
from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._paths import load_config
from squads._roles._catalog import resolve_roles
from squads._services._base import ItemFilter
from squads._services._refs import graph_to_dot, graph_to_mermaid
from squads._services._results import GraphNode, ReflogEntry, TreeNode
from squads._services._service import Service
from squads._services._service import adopt as svc_adopt
from squads._services._service import init as svc_init
from squads._workflow._models import WorkflowSpec

# ---------------------------------------------------------------------------
# Generic badge helpers — one path for priority/severity/any project-declared axis.
# ---------------------------------------------------------------------------


def _field_badge(
    item_type: str, field_code: str, value: str, spec: WorkflowSpec | None = None
) -> str:
    """Render *field_code*'s badge *value* for an item/node of *item_type*, resolving the
    collection from its own declared field (list/tree/graph's "raw code" rendering
    convention). Takes the bare type string (not an ``Item``) so it also serves
    ``GraphNode`` — the ref-graph's own lightweight node shape."""
    active_spec = spec or get_active_spec()
    coll = badges.resolve_collection(item_type, field_code, active_spec)
    return badges.badge_render(coll, value, active_spec)


def _parse_badge_pairs(pairs: list[str]) -> dict[str, str]:
    """Parse repeatable ``CODE=VALUE`` tokens (``--badge``/``--min-badge``) into a dict."""
    out: dict[str, str] = {}
    for pair in pairs:
        code, sep, value = pair.partition("=")
        if not sep or not code.strip():
            raise SquadsError(f"expected CODE=VALUE, got {pair!r}")
        out[code.strip()] = value.strip().lower()
    return out


def _badge_rank(it: Item, field_code: str, spec: WorkflowSpec) -> float:
    """The badge's position in its ordered collection (lower = first); unresolvable sorts last."""
    field = next((f for f in spec.fields_for(it.type) if f.code == field_code), None)
    coll = spec.collections.get(field.collection) if field else None
    value = it.badge_value(field_code)
    if coll is None or value is None:
        return math.inf
    codes = [b.code for b in coll.badges]
    return codes.index(value) if value in codes else math.inf


def _sort_by_badge(items: list[Item], sort: str | None, spec: WorkflowSpec) -> list[Item]:
    """Stable-sort *items* by a badge field's rank when ``--sort CODE`` is given."""
    if sort is None:
        return items
    return sorted(items, key=lambda it: _badge_rank(it, sort, spec))


def _print_empty_or_hidden_hint(hidden_count: int) -> None:
    """Print the closed-count hint when the default filter hid items down to an empty view,
    else the plain empty-view message — shared by ``list``/``tree`` so an empty board never
    looks broken without saying why."""
    if hidden_count:
        console.print(f"[dim]{hidden_count} closed items hidden — use --all[/dim]")
    else:
        console.print("[dim]no items[/dim]")


async def _tree_hidden_count(svc: Service, item_filter: ItemFilter, spec: WorkflowSpec) -> int:
    """Count of items dropped purely by the default category-aware visibility gate, scoped
    to ``item_filter``'s other dimensions (type/status/assignee/category/badges) — the same
    quantity ``sq list`` reports, computed independently of ``tree_view``'s own candidate
    filtering so the CLI can report it without changing that method's signature."""
    pre_visibility = await svc.list_items(
        item_type=item_filter.item_type,
        status=item_filter.status,
        assignee=item_filter.assignee,
        category=item_filter.category,
        badges=dict(item_filter.badges) or None,
        badge_min=dict(item_filter.badge_min) or None,
    )
    return sum(1 for i in pre_visibility if spec.hidden_by_default(i.type, i.status))


def _build_badge_filters(
    priority: str | None, min_priority: str | None, badge: list[str], min_badge: list[str]
) -> tuple[dict[str, str], dict[str, str]]:
    """Merge the dedicated ``--priority``/``--min-priority`` sugar into the generic
    ``--badge``/``--min-badge CODE=VALUE`` maps shared by ``list``/``tree``."""
    badges = _parse_badge_pairs(badge)
    if priority:
        badges["priority"] = parse_badge_code("priority", priority)
    badge_min = _parse_badge_pairs(min_badge)
    if min_priority:
        badge_min["priority"] = parse_badge_code("priority", min_priority)
    return badges, badge_min


# TTY detection — injectable for testing (monkeypatch this callable).
def _default_is_tty() -> bool:
    return sys.stdin.isatty()


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


def _item_table(items: list[Item], spec: WorkflowSpec) -> Table:
    """The shared item table (shared by `list`, `search`, `mine`) — escape all dynamic strings.

    The Status cell is coloured by the status's role intent (``status_text``) — join
    status -> role -> colour, per client, never a hardcoded status-name check.
    """
    table = Table(box=None, pad_edge=False)
    for col in ("ID", "Type", "Status", "Priority", "Title", "Parent", "Assignee"):
        table.add_column(col)
    for it in items:
        table.add_row(
            it.id,
            it.type,
            status_text(it.status, spec),
            e(_field_badge(it.type, "priority", it.priority)) if it.priority else "",
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


def _print_scaffold_warnings(warnings: list[str]) -> None:
    """Print `init`/`adopt`'s WARN-only backend notices (a candidate orphan pointer/skill
    file, or a pre-existing hand-written CLAUDE.md/AGENTS.md) — advisory only, never gates
    the run."""
    for warning in warnings:
        console.print(f"[yellow]warning:[/yellow] {e(warning)}")


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
            # Parenthesized (not PEP 758 bare-tuple) so `vulture` can still parse this file;
            # ruff's py314-target formatter would otherwise strip the parens back off.
            except (typer.Abort, EOFError):  # fmt: skip
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
    _print_scaffold_warnings(result.warnings)
    console.print(
        "Next: [cyan]sq create --help[/cyan] to see your item types · [cyan]sq list[/cyan]"
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
    _print_scaffold_warnings(result.warnings)
    console.print(
        "Migrate legacy docs with [cyan]sq --at <date> create …[/cyan] to preserve history; "
        "then [cyan]sq check[/cyan]."
    )


@app.command(name="list")
@common.command
async def list_items(  # noqa: PLR0913 — the badge axis is generic, not a growing hand-list
    type: str | None = typer.Option(None, "--type", "-t"),
    status: str | None = typer.Option(None, "--status", "-s"),
    parent: str | None = typer.Option(None, "--parent"),
    label: str | None = typer.Option(None, "--label"),
    assignee: str | None = typer.Option(None, "--assignee"),
    category: str | None = typer.Option(
        None, "--category", help="Narrow to one category: roster, work, or records."
    ),
    priority: str | None = typer.Option(
        None,
        "--priority",
        help="Priority code (as defined by your workflow's priority collection).",
    ),
    min_priority: str | None = typer.Option(
        None,
        "--min-priority",
        help="At-least-this-priority threshold (your workflow's priority collection).",
    ),
    badge: list[str] = typer.Option(
        [], "--badge", help="Exact filter on any declared badge field: CODE=VALUE (repeatable)."
    ),
    min_badge: list[str] = typer.Option(
        [],
        "--min-badge",
        help="Threshold filter on any ordered badge field: CODE=VALUE (repeatable).",
    ),
    sort: str | None = typer.Option(
        None, "--sort", help="Sort by an ordered badge field's rank (e.g. priority)."
    ),
    all_: bool = typer.Option(False, "--all", "-a", help="Include closed (done/cancelled) items."),
    json_out: bool = typer.Option(False, "--json"),
):
    """List items in a table.

    Closed items are hidden unless ``--all`` or ``--status`` is given — category-aware: a
    ``work``/``roster`` item hides on a terminal status; a ``records`` item (e.g. a decision)
    stays visible while final-but-live (``Accepted``, ``Published``) and hides only once
    retired (``Superseded``, ``Deprecated``, ``Cancelled``). When hiding empties the view, a
    dim hint reports how many were hidden instead of a bare "no items".

    ``--category`` narrows to one of the fixed roster/work/records axis. ``--priority``/
    ``--min-priority`` are dedicated sugar for the bundled axis; ``--badge``/``--min-badge
    CODE=VALUE`` (repeatable) work generically for any field a spec declares — including a
    project's own custom axis — deriving filter/threshold semantics from ``fields_for()``
    rather than a hand-written per-axis pair.
    """
    svc = get_service()
    spec = get_active_spec()
    validated_assignee = await resolve_slug_or_raise(assignee, svc) if assignee else None
    resolved_parent = await resolve_item_id_any(parent, svc) if parent else None
    badges, badge_min = _build_badge_filters(priority, min_priority, badge, min_badge)
    items = await svc.list_items(
        item_type=parse_type(type) if type else None,
        status=parse_status(status) if status else None,
        parent=resolved_parent,
        label=label,
        assignee=validated_assignee,
        category=parse_category(category) if category else None,
        badges=badges or None,
        badge_min=badge_min or None,
    )
    hidden_count = 0
    if not (all_ or status):
        visible = [i for i in items if not spec.hidden_by_default(i.type, i.status)]
        hidden_count = len(items) - len(visible)
        items = visible
    items = _sort_by_badge(items, sort, spec)
    if json_out:
        print_json_clean(
            json.dumps(
                [
                    {
                        **i.model_dump(mode="json"),
                        "badges": resolve_item_badges(spec, i.type, i.badge_value),
                    }
                    for i in items
                ]
            )
        )
        return
    if not items:
        _print_empty_or_hidden_hint(hidden_count)
        return
    console.print(_item_table(items, spec))


@app.command()
@common.command
async def tree(  # noqa: PLR0913 — the badge axis is generic, not a growing hand-list
    root_id: str | None = typer.Argument(None),
    type: str | None = typer.Option(None, "--type", "-t"),
    status: str | None = typer.Option(None, "--status", "-s"),
    assignee: str | None = typer.Option(None, "--assignee"),
    category: str | None = typer.Option(
        None, "--category", help="Narrow to one category: roster, work, or records."
    ),
    priority: str | None = typer.Option(
        None,
        "--priority",
        help="Priority code (as defined by your workflow's priority collection).",
    ),
    min_priority: str | None = typer.Option(
        None,
        "--min-priority",
        help="At-least-this-priority threshold (your workflow's priority collection).",
    ),
    badge: list[str] = typer.Option(
        [], "--badge", help="Exact filter on any declared badge field: CODE=VALUE (repeatable)."
    ),
    min_badge: list[str] = typer.Option(
        [],
        "--min-badge",
        help="Threshold filter on any ordered badge field: CODE=VALUE (repeatable).",
    ),
    sort: str | None = typer.Option(
        None, "--sort", help="Sort each level by an ordered badge field's rank."
    ),
    depth: int | None = typer.Option(None, "--depth", help="Maximum depth from root (root = 0)."),
    all_: bool = typer.Option(False, "--all", "-a", help="Include closed (done/cancelled) items."),
    json_out: bool = typer.Option(False, "--json", help="Emit the nested subtree as JSON."),
):
    """Show the item hierarchy.

    Closed items are hidden unless ``--all`` or ``--status`` is given — category-aware, the
    same rule ``sq list`` applies (see its help for the work/records distinction). When
    hiding empties the view, a dim hint reports how many were hidden instead of a bare tree.

    Filters (--type, --status, --assignee, --category, --priority) narrow the tree to
    matching nodes; ancestor paths are always preserved so every match shows in context
    (ancestors that only serve as path are rendered dimmed).  --depth N limits the tree to
    N levels from the root. ``--badge``/``--min-badge`` work generically for any declared
    field (see `sq list --help`).

    `--json` emits the subtree (`id/type/title/status/priority/assignee/blocked` + nested
    `children`) — the read an orchestrating agent uses to see a feature's state and decide what to
    do next. Join `status` to `sq workflow statuses --json` / `sq workflow roles --json` for
    open/settled-ness instead of a per-node field.
    """
    svc = get_service()
    spec = get_active_spec()
    # Resolve root_id early so bare numbers work and unknown IDs get a clear error.
    resolved_root: str | None = None
    if root_id is not None:
        resolved_root = await resolve_item_id_any(root_id, svc)
    validated_assignee = await resolve_slug_or_raise(assignee, svc) if assignee else None
    parsed_category = parse_category(category) if category else None

    # Mirror list's closed-item gate exactly:
    #   --status filter (or --all) reveals matching closed items;
    #   --priority / --assignee / --type / --category alone do NOT widen to closed.
    include_closed = bool(all_ or status)

    badges, badge_min = _build_badge_filters(priority, min_priority, badge, min_badge)

    item_filter = ItemFilter(
        item_type=parse_type(type) if type else None,
        status=parse_status(status) if status else None,
        assignee=validated_assignee,
        category=parsed_category,
        badges=tuple(badges.items()),
        badge_min=tuple(badge_min.items()),
        spec=spec,
    )

    hidden_count = 0 if include_closed else await _tree_hidden_count(svc, item_filter, spec)

    nodes = await svc.tree_view(
        resolved_root,
        filter=item_filter,
        depth=depth,
        include_closed=include_closed,
    )

    def _sort_children(tns: list[TreeNode]) -> list[TreeNode]:
        if sort is None:
            return tns
        sort_code = sort
        return sorted(tns, key=lambda tn: _badge_rank(tn.item, sort_code, spec))

    if json_out:
        blocked_ids = {t.id for t, _ in await svc.blocked()}

        def node(tn: TreeNode) -> dict[str, Any]:
            it = tn.item
            return {
                "id": it.id,
                "type": it.type,
                "title": it.title,
                "status": it.status,
                "priority": it.priority,
                "assignee": it.assignee,
                "blocked": it.id in blocked_ids,
                "badges": resolve_item_badges(spec, it.type, it.badge_value),
                "children": [node(c) for c in _sort_children(tn.children)],
            }

        print_json_clean(json.dumps([node(n) for n in _sort_children(nodes)]))
        return

    def _label(it: Item, path_only: bool) -> Text:
        badge = _field_badge(it.type, "priority", it.priority, spec) if it.priority else ""
        prio = f"{e(badge)} · " if badge else ""
        text = Text.from_markup(f"[bold]{it.id}[/bold] {prio}{e(it.title)} ")
        text.append("(", style="dim")
        text.append_text(status_text(it.status, spec))
        text.append(")", style="dim")
        if path_only:
            text.stylize("dim")
        return text

    def _attach(parent: Tree, tn: TreeNode) -> None:
        branch = parent.add(_label(tn.item, tn.path_only))
        for child in _sort_children(tn.children):
            _attach(branch, child)

    if not nodes:
        _print_empty_or_hidden_hint(hidden_count)
        return

    rich_tree = Tree("squad")
    for n in _sort_children(nodes):
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
async def renumber(
    from_seq: int = typer.Option(
        ..., "--from", help="Lowest local sequence number to shift (inclusive)."
    ),
    onto: int | None = typer.Option(
        None,
        "--onto",
        help="The other branch's counter; sq computes the minimal safe offset.",
    ),
    by: int | None = typer.Option(
        None,
        "--by",
        help="Explicit offset (seq -> seq + n); validated, refused if unsafe.",
    ),
):
    """Pre-merge block-shift: reassign this branch's local IDs into a range disjoint from
    another branch's, preserving referential intent.

    A distinct verb from `sq repair --renumber` (the post-merge collision fixer): this one
    is operator-parameterized and run deliberately, once, before a merge — on the branch
    that will yield its IDs to the other's higher-numbered range.

    Read the other branch's counter (for --onto) with:

        git show <mainref>:squads/.squads.json | jq .counter
    """
    if (onto is None) == (by is None):
        raise typer.BadParameter("provide exactly one of --onto or --by")
    svc = get_service()
    result = await svc.renumber(from_seq=from_seq, onto=onto, by=by)
    if result.warning:
        console.print(f"[yellow]warning:[/yellow] {e(result.warning)}")
    if not result.remap:
        console.print("[dim]nothing to renumber — no local item at or above --from[/dim]")
        return
    console.print(f"renumbered {len(result.remap)} item(s); counter={result.db.counter}")
    for old, new in sorted(result.remap.items(), key=lambda kv: kv[1]):
        console.print(f"  {e(old)} -> {e(new)}")


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
        console.print(f"[bold]{it.id}[/bold] {e(it.title)} [dim]({it.status})[/dim]")
        for ln in lines:
            console.print(f"    {e(ln)}")


@app.command()
@common.command
async def search(
    text: str = typer.Argument(..., help="Text to find (case-insensitive)."),
    type: str | None = typer.Option(None, "--type", "-t"),
    status: str | None = typer.Option(None, "--status", "-s"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Search item titles, summaries, and bodies/discussion for text.

    ``--type``/``--status`` AND-compose with the query (same filter dimensions as
    ``sq list``/``sq tree``). A hit's ``region`` names where it matched: ``"title"``,
    ``"description"``, ``"body"``, ``"discussion"`` (``"discussion#<n>"`` for the *n*-th
    comment), or a named sub-entity — ``"<kind>:<local_id>"`` for its heading/body, or
    ``"<kind>:<local_id>:discussion#<n>"`` for its *n*-th comment (e.g. ``"story:US<n>"``,
    ``"story:US<n>:discussion#2"``).

    ``--json`` shape (a stable superset of the legacy ``{id, title, hits}``)::

        [
          {
            "id": "TASK-<n>", "title": "...", "type": "task", "status": "InProgress",
            "hits": [
              {"region": "body", "location": "body", "snippet": "..."},
              {"region": "subtask:ST<n>", "location": "subtask:ST<n>", "snippet": "..."},
              {"region": "discussion#1", "location": "discussion — comment 1 (manager, ...)",
               "snippet": "[<ts>] manager: ..."}
            ]
          }
        ]
    """
    svc = get_service()
    results = await svc.search(
        text,
        item_type=parse_type(type) if type else None,
        status=parse_status(status) if status else None,
    )
    if json_out:
        print_json_clean(
            json.dumps(
                [
                    {
                        "id": r.item.id,
                        "title": r.item.title,
                        "type": r.item.type,
                        "status": r.item.status,
                        "hits": [
                            {"region": h.region, "location": h.location, "snippet": h.snippet}
                            for h in r.hits
                        ],
                    }
                    for r in results
                ]
            )
        )
        return
    if not results:
        console.print(f"[dim]no matches for {e(text)}[/dim]")
        return
    for r in results:
        status_part = f"[dim]({e(r.item.status)})[/dim]"
        console.print(f"[bold]{e(r.item.id)}[/bold] {e(r.item.title)} {status_part}")
        for h in r.hits[:3]:
            console.print(f"    [dim]{e(h.region)}:[/dim] {e(h.snippet)}")


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
                            {"id": b.id, "title": b.title, "status": b.status} for b in bs
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
        console.print(f"[bold]{target.id}[/bold] {e(target.title)} [dim]({target.status})[/dim]")
        for b in blockers:
            console.print(f"    [red]blocked by[/red] {b.id} {e(b.title)} [dim]({b.status})[/dim]")


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

        badge = _field_badge(child.type, "priority", child.priority) if child.priority else ""
        prio = f"{e(badge)} · " if badge else ""
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
        help="Export format: 'dot', 'mermaid', or 'mermaid-md' (overrides Rich tree).",
    ),
):
    """Show the ref graph around an item (ego-centric BFS traversal).

    ``--json`` emits a nested root object (``id/type/status/priority/assignee/edge_kind/
    direction/seen/children``) — the read surface for agents and orchestrators. Shape::

        {
          "id": "BUG-<n>", "type": "bug", "status": "Open", "priority": "high",
          "assignee": null, "edge_kind": null, "direction": null, "seen": false,
          "children": [
            { "id": "FEAT-<n>", ..., "edge_kind": "depends-on", "direction": "out",
              "seen": false, "children": [...] },
            { "id": "TASK-<n>", ..., "edge_kind": "related", "direction": "in",
              "seen": true, "children": [] }
          ]
        }

    ``edge_kind`` for dependency edges is always ``"depends-on"`` (never ``"blocks"``);
    ``direction="out"`` means the root depends on the child, ``direction="in"`` means the
    child depends on the root.  In the Rich tree these render as human-readable labels:
    ``"depends on"`` and ``"required by"`` respectively.

    ``--format dot|mermaid`` emits a serialized graph instead of the Rich tree; suitable
    for piping to ``dot``, ``mmdc``, or pasting into Mermaid Live. ``--format mermaid-md``
    wraps the same Mermaid body in a ```` ```mermaid ```` fence, ready to paste into a doc,
    PR description, or issue that renders Mermaid inline.
    """
    valid_formats = ("dot", "mermaid", "mermaid-md")
    if format_ and format_ not in valid_formats:
        raise SquadsError(f"invalid --format {format_!r}; expected one of {valid_formats}")

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

    if format_ == "mermaid-md":
        fenced = f"```mermaid\n{graph_to_mermaid(root_node)}\n```"
        console.print(fenced, markup=False, highlight=False)
        return

    # Rich tree rendering
    prio = (
        f"{e(_field_badge(root_node.type, 'priority', root_node.priority))} · "
        if root_node.priority
        else ""
    )
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
    spec = get_active_spec()
    if not all_:
        items = [i for i in items if spec.is_open(i.status)]
    if json_out:
        print_json_clean(json.dumps([i.model_dump(mode="json") for i in items]))
        return
    if not items:
        console.print(f"[dim]nothing assigned to {e(slug)}[/dim]")
        return
    console.print(_item_table(items, spec))


@app.command()
@common.command
async def sync():
    """Regenerate tool-owned managed files to the current squads version."""
    svc = get_service()
    await svc.sync()
    console.print("[green]synced[/green] managed files to this squads version")


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
        help="Filter by target item ID (any full ID, e.g. <PREFIX>-<n>).",
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
    all.  Filters are AND-ed: ``--item <PREFIX>-<n> --op status`` shows only status
    changes on that item.

    A squad with no reflog (upgraded from an old schema, or first run) prints empty
    results — never an error.  A truncated or partially-written reflog is tolerated
    silently.

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
        ..., metavar="ID", help="Item ID (e.g. FEAT-<n>) or bare number (e.g. 13)."
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

    Accepts both the full ID (e.g. ``FEAT-<n>``) and a bare sequence number (e.g. ``13``).
    Unknown IDs error cleanly.
    """
    svc = get_service()
    resolved_id = await resolve_item_id_any(item_id, svc)
    it = await svc.get(resolved_id)
    if json_out:
        print_json_clean(await build_item_json(svc, it))
        return
    await print_item(svc, it, raw=raw, comments=comments, full=full)


def _check_issue_sort_key(issue: Any) -> tuple[int, int, int, str]:
    """Deterministic total order for `sq check` output (report mode only — `gate()`'s
    abort-on-first-violation is unaffected). Squad-global/no-item issues (an unresolvable
    `item` — a filename, ``""``, or ``"workflow"``) form a fixed leading block; item-attached
    issues then sort by sequence number, error before warn, then message. Stable: any
    remaining tie keeps its original relative order.
    """
    from squads._errors import InvalidIdError
    from squads._paths import number_for_id

    seq: int | None = None
    if issue.item:
        try:
            seq = number_for_id(issue.item)
        except InvalidIdError:
            seq = None
    has_item = 0 if seq is None else 1
    level_rank = 0 if issue.level == "error" else 1
    return (has_item, seq or 0, level_rank, issue.message)


@app.command()
@common.command
async def check(json_out: bool = typer.Option(False, "--json")):
    """Lint the squad: markers, dangling links, invalid status, index drift.

    Exit codes: 0 = clean (or warnings only), 3 = one or more error-level issues found.
    See `sq docs faq` for the full exit-code table.

    Output (console and ``--json`` alike) is sorted into a deterministic total order —
    squad-global issues first, then by item, error before warn, then message — so it is
    diffable/stable across runs; see :func:`_check_issue_sort_key`.

    When the workflow override spec is invalid (pure-spec error or index cross-check
    failure), ``sq check`` degrades gracefully.  It captures the
    workflow error as a single ``CheckIssue`` ("workflow config invalid — run `sq
    workflow lint`") and continues running all other checks (marker scan, dangling
    links, etc.) using the bundled default spec so they are not suppressed.
    """
    from squads._context import get_context
    from squads._paths import resolve
    from squads._services._results import CheckIssue
    from squads._workflow import bundled_spec
    from squads._workflow._loader import lint_workflow_spec

    # --- Step 1: probe the workflow spec without going through the normal open_service
    # hard-stop.  This lets sq check degrade gracefully when the spec is invalid (AC #4).
    ctx = get_context()
    sp = resolve(ctx.active_dir, client_cwd=ctx.client_cwd)
    workflow_issues: list[CheckIssue] = []
    lint_findings = lint_workflow_spec(sp.squad_dir)
    if any(f[0] == "error" for f in lint_findings):
        workflow_issues.append(
            CheckIssue("error", "workflow", "workflow config invalid — run `sq workflow lint`")
        )

    # --- Step 2: try to open the service normally (uses open_service which passes the
    # override spec to Service explicitly).  If the spec is invalid *and* the index
    # cross-check fails, open_service raises.  In that case fall back to the
    # bundled spec so the remaining checks can still run.
    try:
        svc = get_service()
    except SquadsError:
        # The workflow spec was already captured above — build the service with the
        # bundled spec directly so the other checks (markers, dangling links, etc.) still run.
        from squads._services._service import Service

        svc = Service(sp, spec=bundled_spec())

    issues: list[CheckIssue] = sorted(
        list(workflow_issues) + list(await svc.check()), key=_check_issue_sort_key
    )

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
        console.print(f"[{color}]{i.level}[/{color}]{loc}: {e(i.message)}")
    if errors:
        raise typer.Exit(3)
