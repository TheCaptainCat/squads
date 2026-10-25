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
    ItemRowFields,
    build_item_json,
    build_item_row_json,
    console,
    e,
    err_console,
    get_active_spec,
    get_service,
    handle_errors,
    parse_category,
    parse_filter_badge_code,
    parse_status,
    parse_type,
    print_item,
    print_json_clean,
    resolve_item_id_any,
    resolve_slug_or_raise,
    status_text,
)
from squads._context import get_context
from squads._errors import PlaybookConfigError, SquadsError
from squads._index._reflog import REFLOG_OPS
from squads._models._config import CONFIG_FILENAME
from squads._models._item import Item
from squads._models._subentity import SubEntity
from squads._paths import load_config, process_dir
from squads._roles._catalog import resolve_roles
from squads._services._base import ItemFilter
from squads._services._refs import graph_to_dot, graph_to_mermaid
from squads._services._results import (
    TREE_ANCHOR_MARKER,
    GraphNode,
    MineRow,
    ReflogEntry,
    TreeNode,
    UnreadableItems,
    check_issue_sort_key,
)
from squads._services._service import Service
from squads._services._service import adopt as svc_adopt
from squads._services._service import init as svc_init
from squads._workflow._loader import refusal_cause
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


def _tree_label(it: Item, spec: WorkflowSpec, *, path_only: bool, anchor: bool) -> Text:
    """One line of the human ``sq tree`` rendering.

    The two flags are independent states that **combine**, not alternatives: a cycle anchor
    under a filter matching something below the cycle is a path-only node as well. The anchor
    marker is therefore appended after the path-only dim, so the disclosure stays readable on a
    dimmed line — a dimmed anchor marker is easy to produce and hard to read. Its wording has to
    land on a reader who has never heard of this: the item is not a root anybody wrote, it was
    picked to make an otherwise invisible parent loop visible.
    """
    badge = _field_badge(it.type, "priority", it.priority, spec) if it.priority else ""
    prio = f"{e(badge)} · " if badge else ""
    text = Text.from_markup(f"[bold]{it.id}[/bold] {prio}{e(it.title)} ")
    text.append("(", style="dim")
    text.append_text(status_text(it.status, spec))
    text.append(")", style="dim")
    if path_only:
        text.stylize("dim")
    if anchor:
        text.append(f"  {TREE_ANCHOR_MARKER}", style="yellow")
    return text


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
    ``--badge``/``--min-badge CODE=VALUE`` maps shared by ``list``/``tree``.

    The sugar validates cross-type (:func:`parse_filter_badge_code`) because the filter
    itself is cross-type — no single type's bound collection is the authority here."""
    filters = _parse_badge_pairs(badge)
    if priority:
        # sanctioned field-code literal: `--priority` is the flag *for* this field code
        filters["priority"] = parse_filter_badge_code("priority", priority)
    badge_min = _parse_badge_pairs(min_badge)
    if min_priority:
        # sanctioned field-code literal: `--min-priority` is the flag *for* this field code
        badge_min["priority"] = parse_filter_badge_code("priority", min_priority)
    return filters, badge_min


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


def _item_table(
    items: list[Item],
    spec: WorkflowSpec,
    *,
    matched: dict[str, list[SubEntity]] | None = None,
) -> Table:
    """The shared item table (shared by `list`, `search`, `mine`) — escape all dynamic strings.

    The Status cell is coloured by the status's role intent (``status_text``) — join
    status -> role -> colour, per client, never a hardcoded status-name check.

    ``matched`` (keyed by item id) is `mine`'s roll-up of which sub-entities matched the
    queried slug — when supplied, an extra "Matched" column names them, so a roll-up row
    is never indistinguishable from a direct item assignment.
    """
    table = Table(box=None, pad_edge=False)
    cols = ("ID", "Type", "Status", "Priority", "Title", "Parent", "Assignee")
    if matched is not None:
        cols = (*cols, "Matched")
    for col in cols:
        table.add_column(col)
    for it in items:
        row = [
            it.id,
            it.type,
            status_text(it.status, spec),
            e(_field_badge(it.type, "priority", it.priority)) if it.priority else "",
            e(it.title),
            it.parent or "",
            e(it.assignee or ""),
        ]
        if matched is not None:
            subs = matched.get(it.id, [])
            row.append(e(", ".join(f"{s.local_id} ({s.status})" for s in subs)))
        table.add_row(*row)
    return table


def _compact_lines(items: list[Item], spec: WorkflowSpec) -> list[Text]:
    """One borderless line per item: ID, status, title. The caller prints each unwrapped, cut
    with an ellipsis at the terminal width."""
    return [
        Text.assemble((it.id, "bold"), "  ", status_text(it.status, spec), "  ", it.title)
        for it in items
    ]


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
        console.print(f"[yellow]warning:[/yellow] {e(warning)}", soft_wrap=True)


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
            "Agent backend to write files for (repeatable), such as `claude_code` or "
            "`agents_md`; `none` writes no agent files."
        ),
    ),
    roles: str = typer.Option(
        "all",
        "--roles",
        help="Roles to activate: `all`, `core`, `minimal` or comma-separated slugs.",
    ),
    no_claude: bool = typer.Option(False, "--no-claude", help="Skip Claude Code scaffolding."),
    no_seed_skills: bool = typer.Option(
        False,
        "--no-seed-skills",
        help="Skip stamping skill IDs onto the bundled skill files.",
        hidden=True,
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing .squads.toml."),
    name: list[str] = typer.Option(
        [],
        "--name",
        help="Name a role: `slug=Full Name` (repeatable).",
    ),
    default_names: bool = typer.Option(
        False,
        "--default-names",
        help="Skip interactive prompting; use bundled/pool names for every role.",
    ),
):
    """Initialize squads in the current directory."""
    # Parse --backend flags (repeatable; "none" sentinel → sq-only squad).
    active_backends = _parse_backend_option(backend)

    # Parse --name slug=Full Name flags.
    names_from_flags = _parse_name_flags(name)

    # Load [init.names] from a pre-existing .squads.toml (e.g. when using --force or when the
    # user has created the file manually before running sq init).  Flags win on conflict.
    names_from_config: dict[str, str] = {}
    root = get_context().client_cwd
    config_path = (root or process_dir()) / CONFIG_FILENAME
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
        root=root,
        squad_dir=squad_dir,
        backend=active_backends,
        roles_spec=roles,
        no_claude=no_claude,
        force=force,
        names=combined_names if combined_names else None,
        _skip_skill_seed=no_seed_skills,
    )
    sp = result.paths
    roles_line = ", ".join(r.slug for r in result.roles) or "—"
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
        " · [cyan]sq role catalog[/cyan]",
        soft_wrap=True,
    )


@app.command()
@common.command
async def adopt(
    squad_dir: str = typer.Option(
        "squads", "--squad-dir", help="Folder to adopt when no `.squads.toml` names one."
    ),
    backend: list[str] = typer.Option(
        [],
        "--backend",
        help=(
            "Agent backend to write files for (repeatable), such as `claude_code` or "
            "`agents_md`; `none` writes no agent files."
        ),
    ),
    roles: str = typer.Option(
        "all",
        "--roles",
        help="Roles to activate: `all`, `core`, `minimal` or comma-separated slugs.",
    ),
    no_claude: bool = typer.Option(False, "--no-claude", help="Skip Claude Code scaffolding."),
):
    """Adopt an existing squad folder and index the items already in it."""
    active_backends = _parse_backend_option(backend)
    result = await svc_adopt(
        root=get_context().client_cwd,
        squad_dir=squad_dir,
        backend=active_backends,
        roles_spec=roles,
        no_claude=no_claude,
    )
    sp = result.paths
    new_roles = ", ".join(r.slug for r in result.roles) or "—"
    lines = [
        f"[bold]squad:[/bold] {sp.squad_dir}",
        f"[bold]imported:[/bold] {result.imported} existing item(s)",
        f"[bold]roles activated:[/bold] {new_roles}",
    ]
    console.print(Panel("\n".join(lines), title="squads adopted", expand=False))
    # The import sweep is also the corpus sweep, and this is the only route an existing folder
    # of squads-native markdown takes — no schema stamp to migrate, no repair anyone ran. So
    # the content diff is announced here too, in the same sentence `sq repair` prints; the
    # panel above counts what was imported, which says nothing about what was rewritten.
    notice = result.repair.strip_notice()
    if notice:
        console.print(notice, soft_wrap=True)
    _print_scaffold_warnings(result.warnings)
    # Same channel `sq repair` reports at error level for the identical corpus state, in its
    # own wording — an unreadable file whose previous index entry (if any) was carried forward
    # unrefreshed. Reported here rather than left to `sq check`, which has no model for it:
    # this sweep is the only pass an adopted folder ever gets, so an operator who never runs
    # `sq repair` by hand must still be told.
    for msg in result.repair.unreadable:
        console.print(common.unreadable_report(msg), soft_wrap=True)
    if result.repair.unreadable:
        # Same partial-completion condition `sq repair` itself exits 1 for, over the same
        # rebuild — a caller gating on `$?` must see the same answer from either route. Skip
        # the generic closing hint below: the loop above already names `sq repair` as the
        # next step, and `sq check` cannot see this state to suggest it.
        raise typer.Exit(1)
    console.print(
        "Migrate legacy docs with [cyan]sq --at <date> create …[/cyan] to preserve history; "
        "then [cyan]sq check[/cyan].",
        soft_wrap=True,
    )


@app.command(name="list")
@common.command
async def list_items(  # noqa: PLR0913 — the badge axis is generic, not a growing hand-list
    type: str | None = common.type_filter_option(),
    status: str | None = common.status_filter_option(),
    parent: str | None = typer.Option(
        None, "--parent", help="Show only the direct children of this item ID or number."
    ),
    label: str | None = typer.Option(None, "--label", help="Show only items carrying this label."),
    assignee: str | None = common.assignee_filter_option(),
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
    all_: bool = common.closed_option(),
    json_out: bool = typer.Option(False, "--json", help="Print a JSON array, one object per item."),
    compact: bool = typer.Option(
        False,
        "--compact",
        help="One line per item (ID, status, title cut to the terminal width); not with --json.",
    ),
):
    """List items in a table.

    Closed items are hidden unless `--all` or `--status` is given. What counts as
    closed depends on the item's category: a work or roster item hides on a
    terminal status, while a records item such as a decision stays visible on
    `Accepted` or `Published` and hides once retired (`Superseded`, `Deprecated`,
    `Cancelled`). Filters combine: an item is listed only when it matches every
    one given.
    """
    if compact and json_out:
        raise typer.BadParameter("--compact and --json are mutually exclusive")
    svc = get_service()
    spec = get_active_spec()
    # --assignee is a filter, not authorship: a retired role's already-assigned items must
    # stay reachable, so this validates against the full roster, not live-only.
    validated_assignee = (
        await resolve_slug_or_raise(assignee, svc, live_only=False) if assignee else None
    )
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
                        **i.to_row(),
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
    if compact:
        for line in _compact_lines(items, spec):
            console.print(line, no_wrap=True, overflow="ellipsis")
        return
    console.print(_item_table(items, spec))


@app.command()
@common.command
async def tree(  # noqa: PLR0913 — the badge axis is generic, not a growing hand-list
    root_id: str | None = typer.Argument(
        None, help="Item ID or number to root the tree at; omit for the whole squad."
    ),
    type: str | None = common.type_filter_option(),
    status: str | None = common.status_filter_option(),
    assignee: str | None = common.assignee_filter_option(),
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
    depth: int | None = common.depth_option(None),
    all_: bool = common.closed_option(),
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array of root nodes, each with nested children."
    ),
):
    """Show the item hierarchy.

    Closed items are hidden unless `--all` or `--status` is given, by the same
    rule as `sq list`. A filter keeps the items that match it plus their
    ancestors, so each match shows in context; an ancestor kept only for the path
    is dimmed.

    Items in a parent cycle have no root, so the tree shows one member of each
    cycle as an anchor, marked as such; `sq check` names both ends of the loop.

    In `--json`, a node with `anchor` true is that invented root for a parent
    cycle, not an item somebody made a root.
    Fields: sq docs stability

    \f
    A cycle's members all have a parent, so without an anchor the whole component would be
    absent from the tree while `sq list` still returned it; the anchor is a tiebreak, since
    every member is an equally good root.
    """
    svc = get_service()
    spec = get_active_spec()
    # Resolve root_id early so bare numbers work and unknown IDs get a clear error.
    resolved_root: str | None = None
    if root_id is not None:
        resolved_root = await resolve_item_id_any(root_id, svc)
    # --assignee is a filter, not authorship: a retired role's already-assigned items must
    # stay reachable, so this validates against the full roster, not live-only.
    validated_assignee = (
        await resolve_slug_or_raise(assignee, svc, live_only=False) if assignee else None
    )
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
            # `anchor` is additive, and deliberately asymmetric with `path_only`, which is not
            # on the wire and is not being put there as a rider. The disclosure a fabricated
            # root needs stands on its own for a JSON consumer: without this field the
            # consumer cannot tell an invented root from one somebody wrote.
            return build_item_row_json(
                ItemRowFields(
                    id=it.id,
                    type=it.type,
                    title=it.title,
                    status=it.status,
                    priority=it.priority,
                    assignee=it.assignee,
                    badge_value=it.badge_value,
                ),
                spec=spec,
                blocked_ids=blocked_ids,
                anchor=tn.anchor,
                children=[node(c) for c in _sort_children(tn.children)],
            )

        print_json_clean(json.dumps([node(n) for n in _sort_children(nodes)]))
        return

    def _attach(parent: Tree, tn: TreeNode) -> None:
        branch = parent.add(_tree_label(tn.item, spec, path_only=tn.path_only, anchor=tn.anchor))
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
async def repair(
    renumber: bool = typer.Option(
        False,
        "--renumber",
        help=(
            "First renumber items that share a number after a merge; refs to an ID "
            "that two files carry are listed for checking by hand, not rewritten."
        ),
    ),
):
    """Rebuild the index from the markdown frontmatter.

    It can also rewrite item content, and prints a notice when it does. To keep
    two branches' numbers apart before a merge, use `sq renumber` instead.

    Exit codes: 1 a file was unreadable or refs need checking. See sq docs faq.
    """
    # Repair reconciles the index against the frontmatter, so it must run in every state the
    # live-index cross-check refuses over, including one it did not cause.
    svc = common.get_service_bypassing_index_cross_check()
    result = await svc.repair(renumber=renumber)
    console.print(f"rebuilt index: {len(result.db.items)} items, counter={result.db.counter}")
    notice = result.strip_notice()
    if notice:
        # Announced, not prevented: repair's advertised job is the index, and the sweep also
        # rewrites content. Saying so here is what makes the resulting diff stated rather
        # than discovered by an operator who ran this to reconcile an index. The sentence
        # itself comes from the result so `sq migrate up`, which reaches the same sweep,
        # prints the same one.
        console.print(notice, soft_wrap=True)
    for mid in result.missing_ids:
        console.print(
            f"[yellow]warn[/yellow] [dim]{mid}[/dim]: indexed but no markdown file found (deleted?)"
        )
    for msg in result.unreadable:
        console.print(common.unreadable_report(msg), soft_wrap=True)
    for line in result.renumber_report:
        console.print(e(line), soft_wrap=True)
    if result.unreadable or result.references_left:
        raise typer.Exit(1)


@app.command()
@common.command
async def renumber(
    from_seq: int = typer.Option(
        ..., "--from", help="Lowest item number on this branch to move; it moves too."
    ),
    onto: int | None = typer.Option(
        None,
        "--onto",
        help="The other branch's counter; sq moves numbers just past it.",
    ),
    by: int | None = typer.Option(
        None,
        "--by",
        help="Add this many to each moved number; refused if a collision would remain.",
    ),
):
    """Move this branch's item numbers past another branch's before a merge.

    Run it once, on the branch that yields, before merging; every reference to a
    moved item is rewritten. To fix numbers that already collide after a merge,
    use `sq repair --renumber`. Give exactly one of `--onto` or `--by`.

    Read the other branch's counter (for `--onto`) with:
      git show <mainref>:squads/.squads.json | jq .counter
    """
    if (onto is None) == (by is None):
        raise typer.BadParameter("provide exactly one of --onto or --by")
    svc = get_service()
    result = await svc.renumber(from_seq=from_seq, onto=onto, by=by)
    if result.warning:
        console.print(f"[yellow]warning:[/yellow] {e(result.warning)}", soft_wrap=True)
    if not result.remap:
        console.print("[dim]nothing to renumber — no local item at or above --from[/dim]")
        return
    console.print(f"renumbered {len(result.remap)} item(s); counter={result.db.counter}")
    # The shift borrows `repair`'s index rebuild, which is also the corpus sweep — so this
    # verb rewrites content while its advertised job is identity. Announced here, before the
    # remap listing, in the same sentence `sq repair` prints.
    notice = result.strip_notice()
    if notice:
        console.print(notice, soft_wrap=True)
    for old, new in sorted(result.remap.items(), key=lambda kv: kv[1]):
        console.print(f"  {e(old)} -> {e(new)}")


def _empty_result_note(empty: str, unreadable: UnreadableItems) -> str:
    """The human-mode line for an empty result — *empty* when the corpus was fully read, an
    explicitly partial one when it was not.

    "no matches" is a claim about the corpus, and on a degraded read the command has not seen
    the whole corpus, so it is not in a position to make it. The named files follow immediately
    below either way, but the headline is what a reader acts on, and a confident negative is
    the one shape that stops them looking further.
    """
    if not unreadable:
        return empty
    files = "item file" if len(unreadable) == 1 else "item files"
    return f"{empty} in what could be read — {len(unreadable)} {files} skipped, listed below"


@app.command()
@common.command
async def inbox(
    role: str = typer.Argument(..., help="Role or operator slug, such as `qa`."),
    json_out: bool = typer.Option(False, "--json", help="Print a JSON array, one object per item."),
):
    """List open items whose discussion mentions a role.

    Exit codes: 4 partial result; what could be read is printed. See sq docs faq.
    """
    svc = get_service()
    # A read/filter, not authoring a new participant — a retired role's past @mentions
    # must stay reachable, so this validates against the full roster, not live-only.
    slug = await resolve_slug_or_raise(role, svc, live_only=False)
    hits, unreadable = await svc.inbox(slug)
    if json_out:
        print_json_clean(
            json.dumps(
                [
                    {
                        "id": hit.item.id,
                        "title": hit.item.title,
                        "lines": [ln.text for ln in hit.lines],
                        "regions": [ln.region for ln in hit.lines],
                        "hashes": [ln.hash for ln in hit.lines],
                    }
                    for hit in hits
                ]
            )
        )
        common.report_omissions(unreadable, json_out=True)
        return
    if not hits:
        console.print(f"[dim]{e(_empty_result_note(f'nothing for @{slug}', unreadable))}[/dim]")
    for hit in hits:
        it = hit.item
        console.print(f"[bold]{it.id}[/bold] {e(it.title)} [dim]({it.status})[/dim]")
        for ln in hit.lines:
            suffix = f" [dim]({e(ln.region)})[/dim]" if ln.region else ""
            console.print(f"    {e(ln.text)}{suffix}")
    common.report_omissions(unreadable, json_out=False)


@app.command()
@common.command
async def search(
    text: str = typer.Argument(..., help="Text to find (case-insensitive)."),
    type: str | None = common.type_filter_option(),
    status: str | None = common.status_filter_option(),
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per matching item."
    ),
):
    """Find items whose title, summary, body or discussion contains text.

    `--type` and `--status` narrow the search; a hit must match every one given.
    In `--json`, each hit's `region` says where it was found; the docs list its
    forms.
    Fields: sq docs stability

    Exit codes: 4 partial result; what could be read is printed. See sq docs faq.
    """
    svc = get_service()
    results, unreadable = await svc.search(
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
                            {
                                "region": h.region,
                                "location": h.location,
                                "snippet": h.snippet,
                                "hash": h.hash,
                            }
                            for h in r.hits
                        ],
                    }
                    for r in results
                ]
            )
        )
        common.report_omissions(unreadable, json_out=True)
        return
    if not results:
        note = _empty_result_note(f"no matches for {text}", unreadable)
        console.print(f"[dim]{e(note)}[/dim]")
    for r in results:
        status_part = f"[dim]({e(r.item.status)})[/dim]"
        console.print(f"[bold]{e(r.item.id)}[/bold] {e(r.item.title)} {status_part}")
        for h in r.hits[:3]:
            console.print(f"    [dim]{e(h.region)}:[/dim] {e(h.snippet)}")
    common.report_omissions(unreadable, json_out=False)


@app.command()
@common.command
async def blocked(
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per blocked item."
    ),
):
    """Show open items that wait on another open item."""
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


def _graph_edge_label(edge_kind: str, edge_semantic: str | None, direction: str) -> str:
    """Return the human-readable branch label for a graph edge.

    Branches on ``edge_semantic``, never ``edge_kind`` — the declared kind's spelling is
    display-only. A ``"dependency"``-semantic edge is surfaced as a two-way binding:

    - ``direction="out"`` → the expanded node depends on the child → ``"depends on"``
    - ``direction="in"``  → the child depends on the expanded node → ``"required by"``

    Every other (navigational) kind shows its own declared key verbatim (e.g. ``"related"``,
    ``"fixes"``).
    """
    if edge_semantic == "dependency":
        return "depends on" if direction == "out" else "required by"
    return edge_kind


def _attach_graph_node(parent_tree: Tree, node: GraphNode) -> None:
    """Recursively attach a GraphNode's children to a Rich Tree node."""
    for child in node.children:
        # Build the branch label
        if child.edge_kind is not None and child.direction is not None:
            label_text = _graph_edge_label(child.edge_kind, child.edge_semantic, child.direction)
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
    root_id: str = typer.Argument(..., metavar="ID", help="Item ID or number to start from."),
    depth: int = common.depth_option(2, "-d"),
    kind: list[str] = typer.Option(
        [],
        "--kind",
        "-k",
        help="Follow only this ref kind (repeatable; see `sq workflow ref-kinds`).",
    ),
    direction: str = typer.Option(
        "both",
        "--direction",
        help="`out` follows the item's own refs, `in` the refs to it, `both` either.",
    ),
    all_: bool = common.closed_option(),
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: the root, with nested children."
    ),
    format_: str = typer.Option(
        "",
        "--format",
        help="Print the graph as `dot`, `mermaid` or `mermaid-md` text instead.",
    ),
):
    """Show the items linked to an item by refs, a few levels out.

    A dependency edge reads `depends on` or `required by`; any other edge shows
    its ref kind. A node already shown elsewhere is marked `(seen)` and not
    expanded. `--format` prints the graph as text for another tool instead of the
    tree: `mermaid-md` wraps the Mermaid output in a fence, ready to paste into
    markdown.

    In `--json`, branch on `edge_semantic`, never on `edge_kind`, which a project
    can rename.
    Fields: sq docs stability
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
async def workload(
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per assignee."
    ),
):
    """Count each assignee's open and closed work, busiest first.

    Items and sub-entities are counted separately.
    """
    svc = get_service()
    rows = await svc.workload()
    if json_out:
        print_json_clean(
            json.dumps(
                [
                    {
                        "assignee": r.assignee,
                        "open": r.open,
                        "closed": r.closed,
                        "total": r.total,
                        "subentity_open": r.subentity_open,
                        "subentity_closed": r.subentity_closed,
                        "subentity_total": r.subentity_total,
                    }
                    for r in rows
                ]
            )
        )
        return
    if not rows:
        console.print("[dim]no items[/dim]")
        return
    table = Table(box=None, pad_edge=False)
    for col in ("Assignee", "Open", "Closed", "Total", "Sub Open", "Sub Closed", "Sub Total"):
        table.add_column(col)
    for r in rows:
        table.add_row(
            e(r.assignee or "(unassigned)"),
            str(r.open),
            str(r.closed),
            str(r.total),
            str(r.subentity_open),
            str(r.subentity_closed),
            str(r.subentity_total),
        )
    console.print(table)


@app.command()
@common.command
async def mine(
    role: str = typer.Argument(..., help="Role or operator slug, such as `python-dev`."),
    all_: bool = common.closed_option(),
    json_out: bool = typer.Option(False, "--json", help="Print a JSON array, one object per item."),
):
    """List the items assigned to someone, directly or through a sub-entity."""
    svc = get_service()
    # A read/filter: a retired role's still-open assigned items must stay reachable for
    # review, so this validates against the full roster, not live-only.
    slug = await resolve_slug_or_raise(role, svc, live_only=False)
    rows = await svc.mine(slug, include_closed=all_)
    spec = get_active_spec()
    if json_out:
        print_json_clean(json.dumps([_mine_row_json(r, spec) for r in rows]))
        return
    if not rows:
        console.print(f"[dim]nothing assigned to {e(slug)}[/dim]")
        return
    items = [r.item for r in rows]
    matched = {r.item.id: r.matched_subentities for r in rows}
    console.print(_item_table(items, spec, matched=matched))


def _mine_row_json(row: MineRow, spec: WorkflowSpec) -> dict[str, Any]:
    """`mine --json`'s per-item payload: the item, plus the additive ``matched_subentities``
    key naming every sub-entity of it assigned to the queried slug (see :class:`MineRow`)."""
    data = row.item.to_row()
    kind = spec.item_subentity_kind(row.item.type)
    data["matched_subentities"] = [
        {"local_id": s.local_id, "kind": kind, "title": s.title, "status": s.status}
        for s in row.matched_subentities
    ]
    return data


@app.command()
@common.command
async def sync():
    """Regenerate tool-owned managed files to the current squads version."""
    svc = get_service()
    skipped = await svc.sync()
    _print_scaffold_warnings(skipped)
    console.print("[green]synced[/green] managed files to this squads version")


@app.command()
@handle_errors
def docs(
    name: str | None = typer.Argument(
        None, help="Doc to print, such as `internals`; omit to list."
    ),
    pretty: bool = typer.Option(False, "--rich", help="Pretty-print instead of raw markdown."),
):
    """Print the squads documentation in the terminal, offline."""
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
        help="Show only entries on this full item ID, such as `TASK-<n>`.",
        metavar="ID",
    ),
    actor: str | None = typer.Option(
        None,
        "--actor",
        help="Show only entries by this slug, such as `python-dev` or `system`.",
    ),
    op: str | None = typer.Option(
        None,
        "--op",
        help=f"Show only entries of this operation: {', '.join(REFLOG_OPS)}.",
    ),
    since: str | None = typer.Option(
        None,
        "--since",
        help="Show only entries at or after this ISO 8601 date or time.",
        metavar="WHEN",
    ),
    tail: int = typer.Option(
        50,
        "--tail",
        "-n",
        help="Show at most this many of the latest entries; 0 shows all.",
    ),
    tree_view: bool = typer.Option(
        False,
        "--tree",
        help=(
            "Group entries into a tree of which session started which; sessions report "
            "their own parent, so treat the tree as a hint, not a record."
        ),
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per entry."
    ),
):
    """Show the log of every command that changed the squad, latest last.

    Filters combine: `--item TASK-<n> --op status` shows only that item's status
    changes. A squad with no log yet prints nothing rather than an error.
    """
    from squads._clock import parse_iso

    svc = get_service()
    since_ts: str | None = None
    if since:
        try:
            from squads import _clock as clock

            since_ts = clock.iso(parse_iso(since))
        except ValueError:
            err_console.print(
                f"[red]error:[/red] invalid --since timestamp {since!r} "
                "(use ISO 8601, e.g. 2026-01-15 or 2026-01-15T09:30:00Z)",
                soft_wrap=True,
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
        ..., metavar="ID", help="Item ID, such as `FEAT-<n>`, or its bare number."
    ),
    json_out: bool = typer.Option(False, "--json", help="Print one JSON object: the item."),
    raw: bool = common.raw_option(),
    comments: bool = typer.Option(
        False, "--comments", help="Append the discussion as comment panes."
    ),
    full: bool = typer.Option(False, "--full", help="Add one pane per sub-entity (body + badges)."),
):
    """Show any item by ID or number, whatever its type."""
    svc = get_service()
    resolved_id = await resolve_item_id_any(item_id, svc)
    it = await svc.get(resolved_id)
    if json_out:
        print_json_clean(await build_item_json(svc, it))
        return
    await common.warn_duplicate_id(svc, it)
    await print_item(svc, it, raw=raw, comments=comments, full=full)


@app.command()
@common.command
async def check(
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per issue."
    ),
):
    """Lint the squad: markers, dangling links, invalid status, index drift.

    Exit codes: 3 error-level issues found. See sq docs faq.

    Output is in a stable order, so two runs can be diffed.
    A broken workflow or playbook override is reported as an issue, and the other
    checks still run.
    """
    from squads._paths import resolve
    from squads._services._results import CheckIssue
    from squads._services._service import check_fallback, compose_service

    ctx = get_context()
    sp = resolve(client_cwd=ctx.client_cwd)
    workflow_issues: list[CheckIssue] = []

    # Open the service the normal way (``open_service``, which merges any override and runs
    # the live-index cross-check). This IS the ground truth for "does the workflow config
    # actually load" — unlike scanning `sq workflow lint`'s findings for any error level, it
    # cannot be tripped by a finding (e.g. the stamp obligation) that is deliberately reported
    # rather than load-blocking. Only a genuine load failure falls back, so the remaining checks
    # (marker scan, dangling links, etc.) still run. The stamp finding reaches the issue list on
    # its own through the override walk, so a config that loads is never also reported as invalid.
    #
    # Which mode the fallback composes in is `check_fallback`'s table: a broken playbook keeps the
    # merged workflow spec (the playbook is what failed, and falling back to the bundled spec
    # would make any item of a project-declared type look undeclared and drown the real finding
    # in a false corpus error), and anything else falls back to the bundled spec. The playbook
    # finding is worded apart from the workflow one: `sq workflow lint` does not read the
    # playbook and no command lints it, so it names the loader's violation and the file.
    try:
        svc = get_service()
    except SquadsError as exc:
        if isinstance(exc, PlaybookConfigError):
            workflow_issues.append(
                CheckIssue("error", "playbook", f"playbook config invalid: {exc}", "playbook_loads")
            )
        else:
            workflow_issues.append(
                CheckIssue(
                    "error",
                    "workflow",
                    f"workflow config invalid: {refusal_cause(str(exc))} — run `sq workflow lint`",
                    "workflow_loads",
                )
            )
        svc = compose_service(
            sp,
            check_fallback(exc),
            resolved_spec=ctx.active_spec,
            sources=common.invocation_sources(sp.squad_dir),
        )

    # The corpus scan runs against whichever spec survived above, and that spec may be unable to
    # load the index at all: both fallbacks can land on a spec that does not declare a type the
    # board still carries (both overrides broken, or a workflow override that drops a type with
    # live items — the latter reachable with no playbook override in play). Letting that propagate
    # discards every config finding collected above and prints one unrelated corpus error in their
    # place, which is the failure mode this command exists to avoid: a reporter that stops at the
    # first problem fails exactly when it is needed most. So the scan's own failure becomes its
    # own finding and the collected ones still print — report and stop, never report nothing.
    collected: list[CheckIssue] = list(workflow_issues)
    try:
        collected += await svc.check()
    except SquadsError as exc:
        collected.append(
            CheckIssue("error", "corpus", f"could not scan the corpus: {exc}", "corpus_scans")
        )
    issues: list[CheckIssue] = sorted(collected, key=check_issue_sort_key)

    if json_out:
        print_json_clean(
            json.dumps(
                [
                    {"level": i.level, "item": i.item, "message": i.message, "rule": i.rule}
                    for i in issues
                ]
            )
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
        console.print(f"[{color}]{i.level}[/{color}]{loc}: {e(i.message)}", soft_wrap=True)
    if errors:
        raise typer.Exit(3)
