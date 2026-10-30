"""Top-level commands: init, adopt, list, tree, repair, inbox, sync, docs, check.

Per-item operations (show/update/status/body/comment/refs + sub-entities) live in the
resource-oriented `sq <type> <num> <verb> …` groups built by `_items.build_item_app`.

The ``workflow`` command group (cheatsheet + lint) lives in ``_workflow_cmd.py`` and is
registered as a Typer sub-app in ``_cli/__init__.py``.
"""

import sys
from collections.abc import Callable
from pathlib import Path

import typer

import squads._cli._common as common
import squads._cli._field_options as field_options
from squads._api import _ops as ops
from squads._cli import _calls as calls
from squads._cli import app
from squads._cli._common import (
    console,
    err_console,
    handle_errors,
    parse_badge_field,
    parse_category,
    parse_filter_badge_code,
    parse_status,
    parse_type,
    print_json_clean,
)
from squads._context import get_context
from squads._errors import SquadsError
from squads._index._reflog import REFLOG_OPS
from squads._models._config import CONFIG_FILENAME
from squads._models._schema import SCHEMA_VERSION
from squads._paths import load_config, process_dir, resolve
from squads._roles._catalog import resolve_roles

# ---------------------------------------------------------------------------
# Generic badge helpers — one path for every declared badge axis.
# ---------------------------------------------------------------------------


def _parse_badge_pairs(pairs: list[str]) -> dict[str, str]:
    """Parse repeatable ``code=value`` tokens (``--badge``/``--min-badge``) into a dict."""
    out: dict[str, str] = {}
    for pair in pairs:
        code, sep, value = pair.partition("=")
        if not sep or not code.strip():
            raise SquadsError(f"expected code=value, got {pair!r}")
        field = parse_badge_field(code)
        out[field] = parse_filter_badge_code(field, value)
    return out


def _build_badge_filters(
    ctx: typer.Context, badge: list[str], min_badge: list[str]
) -> tuple[dict[str, str], dict[str, str]]:
    """Merge the derived ``--<code>``/``--min-<code>`` options into the generic ``--badge``/
    ``--min-badge code=value`` maps shared by ``list``/``tree``: each means exactly its generic
    form.

    Values validate cross-type (:func:`parse_filter_badge_code`) because the filter itself is
    cross-type — no single type's bound collection is the authority here."""
    filters = _parse_badge_pairs(badge)
    for code, value in field_options.given_values(ctx).items():
        filters[code] = parse_filter_badge_code(code, value)
    badge_min = _parse_badge_pairs(min_badge)
    for code, value in field_options.given_min(ctx).items():
        badge_min[code] = parse_filter_badge_code(code, value)
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
@handle_errors
def init(  # noqa: PLR0913 — one parameter per init option
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
        help=(
            "Roles to activate: a bundle of the squad's role catalog (bundled: `all`, `core`, "
            "`minimal`) or comma-separated slugs."
        ),
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
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Print one JSON object: the squad created; no role name is asked for.",
    ),
):
    """Initialize squads in the current directory."""
    # Parse --backend flags (repeatable; "none" sentinel → sq-only squad).
    from squads._api._dto._squad import InitRequest
    from squads._cli._render._squad import render_init

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
            pass  # Malformed config — the init call raises AlreadyInitializedError or SquadsError.

    # Prompt on a terminal unless --default-names or --json says not to.
    # A squad at another schema refuses the call, so it is not asked for names it would discard.
    interactive = _is_tty() and not default_names and not json_out and not _schema_differs()

    # Build the combined names map: config < flags (flags win).
    # A slug already covered by either source is not asked interactively.
    combined_names: dict[str, str] = {**names_from_config, **names_from_flags}

    if interactive:
        _prompt_names(roles, (root or process_dir()) / squad_dir, combined_names)

    request = InitRequest(
        squad_dir=squad_dir,
        backends=active_backends,
        roles=roles,
        no_claude=no_claude,
        force=force,
        names=combined_names,
        seed_skills=not no_seed_skills,
    )
    response = calls.call(ops.INIT, request)
    if json_out:
        calls.print_json(ops.INIT, response)
        return
    calls.print_warnings(response)
    render_init(response.data, console)


def _schema_differs() -> bool:
    """Whether the squad this directory resolves to is at a schema other than the package's."""
    try:
        paths = resolve(client_cwd=get_context().client_cwd)
    except SquadsError:
        return False
    return paths.config.schema_version != SCHEMA_VERSION


def _prompt_names(roles: str, squad_dir: Path, names: dict[str, str]) -> None:
    """Ask for the name of each role *roles* activates that *names* does not hold yet, and add
    every name typed; Enter keeps the bundled one."""
    sources = common.invocation_sources(squad_dir)
    role_defs = resolve_roles(roles, sources.catalog()) if roles else []
    for rdef in role_defs:
        slug = rdef.slug
        if slug in names:
            continue
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
            # On Windows, isatty() can report a console on a closed stdin pipe, so the first
            # prompt raises: fall back to bundled defaults rather than aborting the init.
            break
        if typed:
            names[slug] = typed


@app.command()
@handle_errors
def adopt(
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
        help=(
            "Roles to activate: a bundle of the squad's role catalog (bundled: `all`, `core`, "
            "`minimal`) or comma-separated slugs."
        ),
    ),
    no_claude: bool = typer.Option(False, "--no-claude", help="Skip Claude Code scaffolding."),
    renumber: bool = typer.Option(
        False,
        "--renumber",
        help="Give files that share a number a new one, then adopt.",
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: the squad adopted and what it held."
    ),
):
    """Adopt an existing squad folder and index the items already in it."""
    from squads._api._dto._squad import AdoptRequest
    from squads._cli._render._squad import render_adopt

    request = AdoptRequest(
        squad_dir=squad_dir,
        backends=_parse_backend_option(backend),
        roles=roles,
        no_claude=no_claude,
        renumber=renumber,
    )
    response = calls.call(ops.ADOPT, request)
    report = response.data
    if json_out:
        calls.print_json(ops.ADOPT, response)
    else:
        calls.print_warnings(response)
        render_adopt(report, console)
    # An unreadable file is the partial-completion condition `sq repair` exits 1 for, so a
    # caller gating on `$?` gets the same answer either way.
    if report.unreadable:
        raise typer.Exit(1)


@app.command(name="list", cls=field_options.FilterCommand)
@handle_errors
def list_items(  # noqa: PLR0913 — the badge axis is generic, not a growing hand-list
    ctx: typer.Context,
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
    badge: list[str] = typer.Option(
        [], "--badge", help="Exact filter on any declared badge field: code=value (repeatable)."
    ),
    min_badge: list[str] = typer.Option(
        [],
        "--min-badge",
        help="Threshold filter on any ordered badge field: code=value (repeatable).",
    ),
    sort: str | None = typer.Option(
        None, "--sort", help="Sort by an ordered badge field's rank, by its code."
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
    terminal status, while a records item stays visible while it is in force and
    hides once retired. Filters combine: an item is listed only when it matches
    every one given.
    """
    from squads._api._dto._items import ItemListRequest
    from squads._cli._render._items import render_list

    if compact and json_out:
        raise typer.BadParameter("--compact and --json are mutually exclusive")
    badges, badge_min = _build_badge_filters(ctx, badge, min_badge)
    if sort is not None:
        sort = parse_badge_field(sort, ordered=True)
    request = ItemListRequest(
        type=parse_type(type) if type else None,
        status=parse_status(status) if status else None,
        parent=parent,
        label=label,
        assignee=assignee,
        category=parse_category(category) if category else None,
        badge=[f"{code}={value}" for code, value in badges.items()],
        min_badge=[f"{code}={value}" for code, value in badge_min.items()],
        sort=sort,
        all=all_,
    )
    response = calls.call(ops.ITEMS_LIST, request)
    if json_out:
        calls.print_json(ops.ITEMS_LIST, response)
    else:
        calls.print_warnings(response)
        render_list(response.data, console, compact=compact)
    calls.finish(response, json_out=json_out)


@app.command(cls=field_options.FilterCommand)
@handle_errors
def tree(  # noqa: PLR0913 — the badge axis is generic, not a growing hand-list
    ctx: typer.Context,
    root_id: str | None = typer.Argument(
        None, help="Item ID or number to root the tree at; omit for the whole squad."
    ),
    type: str | None = common.type_filter_option(),
    status: str | None = common.status_filter_option(),
    assignee: str | None = common.assignee_filter_option(),
    category: str | None = typer.Option(
        None, "--category", help="Narrow to one category: roster, work, or records."
    ),
    label: str | None = typer.Option(None, "--label", help="Show only items carrying this label."),
    badge: list[str] = typer.Option(
        [], "--badge", help="Exact filter on any declared badge field: code=value (repeatable)."
    ),
    min_badge: list[str] = typer.Option(
        [],
        "--min-badge",
        help="Threshold filter on any ordered badge field: code=value (repeatable).",
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
    from squads._api._dto._tree import TreeRequest
    from squads._cli._render._tree import render_tree

    badges, badge_min = _build_badge_filters(ctx, badge, min_badge)
    if sort is not None:
        sort = parse_badge_field(sort, ordered=True)
    request = TreeRequest(
        root=root_id,
        type=parse_type(type) if type else None,
        status=parse_status(status) if status else None,
        assignee=assignee,
        category=parse_category(category) if category else None,
        label=label,
        badge=[f"{code}={value}" for code, value in badges.items()],
        min_badge=[f"{code}={value}" for code, value in badge_min.items()],
        sort=sort,
        depth=depth,
        all=all_,
    )
    response = calls.call(ops.TREE, request)
    if json_out:
        calls.print_json(ops.TREE, response)
    else:
        calls.print_warnings(response)
        render_tree(response.data, console)
    calls.finish(response, json_out=json_out)


@app.command()
@handle_errors
def repair(
    renumber: bool = typer.Option(
        False,
        "--renumber",
        help=(
            "First renumber items that share a number after a merge; refs to an ID "
            "that two files carry are listed for checking by hand, not rewritten."
        ),
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: what the rebuild found and did."
    ),
):
    """Rebuild the index from the markdown frontmatter.

    It can also rewrite item content, and prints a notice when it does. To keep
    two branches' numbers apart before a merge, use `sq renumber` instead.

    Exit codes: 1 a file was unreadable or refs need checking. See sq docs faq.
    """
    from squads._api._dto._squad import RepairRequest
    from squads._cli._render._squad import render_repair

    response = calls.call(ops.REPAIR, RepairRequest(renumber=renumber))
    report = response.data
    if json_out:
        calls.print_json(ops.REPAIR, response)
    else:
        calls.print_warnings(response)
        render_repair(report, console)
    if report.unreadable or report.references_left:
        raise typer.Exit(1)


@app.command()
@handle_errors
def renumber(
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
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: the items moved and the counter."
    ),
):
    """Move this branch's item numbers past another branch's before a merge.

    Run it once, on the branch that yields, before merging; every reference to a
    moved item is rewritten. To fix numbers that already collide after a merge,
    use `sq repair --renumber`. Give exactly one of `--onto` or `--by`.

    Read the other branch's counter (for `--onto`) with:
      git show <mainref>:squads/.squads.json | jq .counter
    """
    from squads._api._dto._squad import RenumberRequest
    from squads._cli._render._squad import render_renumber

    if (onto is None) == (by is None):
        raise typer.BadParameter("provide exactly one of --onto or --by")
    response = calls.call(ops.RENUMBER, RenumberRequest(from_seq=from_seq, onto=onto, by=by))
    if json_out:
        calls.print_json(ops.RENUMBER, response)
        return
    calls.print_warnings(response)
    render_renumber(response.data, console)


@app.command()
@handle_errors
def inbox(
    role: str = typer.Argument(..., help="Role or operator slug, such as `qa`."),
    json_out: bool = typer.Option(False, "--json", help="Print a JSON array, one object per item."),
):
    """List open items whose discussion mentions a role.

    Exit codes: 4 partial result; what could be read is printed. See sq docs faq.
    """
    from squads._api._dto._queues import InboxRequest
    from squads._cli._render._queues import render_inbox

    response = calls.call(ops.INBOX, InboxRequest(slug=role))
    if json_out:
        calls.print_json(ops.INBOX, response)
    else:
        calls.print_warnings(response)
        render_inbox(response.data, console, skipped=len(response.omitted))
    calls.finish(response, json_out=json_out)


@app.command()
@handle_errors
def search(
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
    from squads._api._dto._search import SearchRequest
    from squads._cli._render._search import render_search

    request = SearchRequest(
        q=text,
        type=parse_type(type) if type else None,
        status=parse_status(status) if status else None,
    )
    response = calls.call(ops.SEARCH, request)
    if json_out:
        calls.print_json(ops.SEARCH, response)
    else:
        calls.print_warnings(response)
        render_search(response.data, console, text=text, skipped=len(response.omitted))
    calls.finish(response, json_out=json_out)


@app.command()
@handle_errors
def blocked(
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per blocked item."
    ),
):
    """Show open items that wait on another open item."""
    from squads._api._dto._queues import BlockedRequest
    from squads._cli._render._queues import render_blocked

    response = calls.call(ops.BLOCKED, BlockedRequest())
    if json_out:
        calls.print_json(ops.BLOCKED, response)
    else:
        calls.print_warnings(response)
        render_blocked(response.data, console)
    calls.finish(response, json_out=json_out)


@app.command()
@handle_errors
def graph(
    root_id: str = typer.Argument(..., metavar="id", help="Item ID or number to start from."),
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
    from squads._api._dto._graph import GraphRequest
    from squads._cli._render._graph import render_graph, render_graph_text

    valid_formats = ("dot", "mermaid", "mermaid-md")
    if format_ and format_ not in valid_formats:
        raise SquadsError(f"invalid --format {format_!r}; expected one of {valid_formats}")

    request = GraphRequest(root=root_id, depth=depth, kind=kind, direction=direction, all=all_)
    response = calls.call(ops.GRAPH, request)
    if json_out:
        calls.print_json(ops.GRAPH, response)
    else:
        calls.print_warnings(response)
        if format_:
            render_graph_text(response.data, console, fmt=format_)
        else:
            render_graph(response.data, console)
    calls.finish(response, json_out=json_out)


@app.command()
@handle_errors
def workload(
    json_out: bool = typer.Option(
        False, "--json", help="Print a JSON array, one object per assignee."
    ),
):
    """Count each assignee's open and closed work, busiest first.

    Items and sub-entities are counted separately.
    """
    from squads._api._dto._queues import WorkloadRequest
    from squads._cli._render._queues import render_workload

    response = calls.call(ops.WORKLOAD, WorkloadRequest())
    if json_out:
        calls.print_json(ops.WORKLOAD, response)
    else:
        calls.print_warnings(response)
        render_workload(response.data, console)
    calls.finish(response, json_out=json_out)


@app.command()
@handle_errors
def mine(
    role: str = typer.Argument(..., help="Role or operator slug, such as `python-dev`."),
    all_: bool = common.closed_option(),
    json_out: bool = typer.Option(False, "--json", help="Print a JSON array, one object per item."),
):
    """List the items assigned to someone, directly or through a sub-entity."""
    from squads._api._dto._queues import MineRequest
    from squads._cli._render._queues import render_mine

    response = calls.call(ops.MINE, MineRequest(slug=role, all=all_))
    if json_out:
        calls.print_json(ops.MINE, response)
    else:
        calls.print_warnings(response)
        render_mine(response.data, console)
    calls.finish(response, json_out=json_out)


@app.command()
@handle_errors
def sync(
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: what the regeneration left alone."
    ),
):
    """Regenerate tool-owned managed files to the current squads version."""
    from squads._api._dto._check import SyncRequest
    from squads._cli._render._check import render_sync

    response = calls.call(ops.SYNC, SyncRequest())
    if json_out:
        calls.print_json(ops.SYNC, response)
        return
    calls.print_warnings(response)
    render_sync(response.data, console)


@app.command()
@handle_errors
def docs(
    name: str | None = typer.Argument(
        None, help="Doc to print, such as `internals`; omit to list."
    ),
    pretty: bool = typer.Option(False, "--rich", help="Pretty-print instead of raw markdown."),
    json_out: bool = typer.Option(
        False, "--json", help="Print one JSON object: the doc, or the list of docs."
    ),
):
    """Print the squads documentation in the terminal, offline."""
    from squads import _docfiles
    from squads._api._dto._package import DocIndex
    from squads._cli._render._package import render_doc, render_doc_index

    found = _docfiles.doc_index() if name is None else _docfiles.doc(name)
    if json_out:
        print_json_clean(found.model_dump_json())
    elif isinstance(found, DocIndex):
        render_doc_index(found, console)
    else:
        render_doc(found, console, pretty=pretty)


@app.command()
@handle_errors
def reflog(
    item: str | None = typer.Option(
        None,
        "--item",
        help="Show only entries on this full item ID, such as `<prefix>-<n>`.",
        metavar="id",
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
        metavar="when",
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

    Filters combine: `--item <prefix>-<n> --op status` shows only that item's
    status changes. A squad with no log yet prints nothing rather than an error.
    """
    from squads import _clock as clock
    from squads._api._dto._reflog import ReflogRequest
    from squads._cli._render._reflog import render_reflog, render_reflog_tree

    since_ts: str | None = None
    if since:
        try:
            since_ts = clock.iso(clock.parse_iso(since))
        except ValueError:
            err_console.print(
                f"[red]error:[/red] invalid --since timestamp {since!r} "
                "(use ISO 8601, e.g. 2026-01-15 or 2026-01-15T09:30:00Z)",
                soft_wrap=True,
            )
            raise typer.Exit(1) from None
    if op is not None and op not in REFLOG_OPS:
        raise SquadsError(f"unknown operation {op!r} (one of: {', '.join(REFLOG_OPS)})")
    request = ReflogRequest(
        item=item, actor=actor, op=op, since=since_ts, tail=tail if tail > 0 else None
    )
    response = calls.call(ops.REFLOG, request)
    if json_out:
        calls.print_json(ops.REFLOG, response)
        return
    calls.print_warnings(response)
    if tree_view:
        render_reflog_tree(response.data, console)
    else:
        render_reflog(response.data, console)


@app.command(name="show")
@handle_errors
def show_any(
    item_id: str = typer.Argument(
        ..., metavar="id", help="Item ID, such as `<prefix>-<n>`, or its bare number."
    ),
    json_out: bool = typer.Option(False, "--json", help="Print one JSON object: the item."),
    raw: bool = common.raw_option(),
    comments: bool = typer.Option(
        False, "--comments", help="Append the discussion as comment panes."
    ),
    full: bool = typer.Option(False, "--full", help="Add one pane per sub-entity (body + badges)."),
):
    """Show any item by ID or number, whatever its type."""
    from squads._api._dto._items import ItemShowRequest
    from squads._cli._render._items import render_show

    response = calls.call(ops.ITEM_SHOW, ItemShowRequest(id=item_id))
    if json_out:
        calls.print_json(ops.ITEM_SHOW, response)
    else:
        calls.print_warnings(response)
        render_show(response.data, console, raw=raw, comments=comments, full=full)
    calls.finish(response, json_out=json_out)


@app.command()
@handle_errors
def check(
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
    from squads._api._dto._check import CheckRequest
    from squads._cli._render._check import render_check

    response = calls.call(ops.CHECK, CheckRequest())
    if json_out:
        calls.print_json(ops.CHECK, response)
    else:
        calls.print_warnings(response)
        render_check(response.data, console)
    if response.data.errors:
        raise typer.Exit(3)
