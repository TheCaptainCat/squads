"""Shared CLI helpers: console, error handling, service resolution, value parsing."""

import contextlib
import functools
import json
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, ClassVar

import anyio
import typer
import typer._click as _click  # underscore is upstream's own private module path, not ours
import typer._click.globals as _click_globals  # ditto — upstream's, not ours
import typer.core
import typer.main
from rich.console import Console, Group, RenderableType
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.text import Text

from squads import __version__
from squads import _badges as badges
from squads import _discussion as discussion
from squads._context import get_context, rebind
from squads._errors import SquadsError
from squads._index._store import enter_read_scope, exit_read_scope
from squads._models._item import (
    DEFAULT_KIND,
    DISPLAY_ID_PADDING,
    Item,
    effective_prefix,
    format_item_id,
    split_ref,
)
from squads._models._schema import SCHEMA_VERSION, schema_tuple
from squads._models._subentity import SubEntity
from squads._paths import resolve
from squads._services._results import BlockResult, SubentityDetail
from squads._services._service import Service, open_service
from squads._workflow import CATEGORIES, ROSTER_OPERATOR, ROSTER_ROLE, bundled_spec
from squads._workflow._models import RESERVED_CLI_ALIASES, WorkflowSpec, reserved_alias_owner

console = Console()
err_console = Console(stderr=True)


def print_json_clean(s: str) -> None:
    """Emit JSON to stdout with no ANSI codes, unconditionally.

    Uses plain ``print()`` so FORCE_COLOR / CLICOLOR_FORCE / PY_COLORS have no effect.
    The indent matches Rich's ``print_json`` default (2 spaces).  All ``--json`` output
    must go through this function — never through ``console.print_json()``.
    """
    print(json.dumps(json.loads(s), indent=2))


# The active squad folder and per-invocation WorkflowSpec are ambient RequestContext fields
# (squads._context) now, not module globals — set once per invocation by the root callback's
# single bind_context(RequestContext(...)) call. These setters/getter keep their public
# names/signatures so the ~15 call sites below and in tests are unaffected by the move.


def set_active_dir(value: str | None) -> None:
    rebind(active_dir=value)


def set_active_spec(spec: WorkflowSpec | None) -> None:
    rebind(active_spec=spec)


def get_active_spec() -> WorkflowSpec:
    """Return the per-invocation spec, or the bundled spec if none has been bound yet.

    Raises ``SquadsError`` when the squad **has** a workflow override that failed to resolve
    (``RequestContext.spec_error``). Answering from the bundled spec there would describe
    vocabulary the project did not declare — the failure mode the hard-stop-at-load rule exists
    to prevent — and the caller has no way to tell that answer apart from a correct one. Every
    read surface that consults the spec therefore refuses with the *same* text
    ``open_service`` raises (``_workflow._loader.spec_refusal``), rather than each deciding for
    itself. ``sq workflow lint`` never calls this and never opens a service, which is what
    keeps the diagnostic reachable while everything else is stopped; ``sq check`` and
    ``sq repair`` take the refusal from ``open_service`` and degrade around it, reporting it
    as a finding — reporting the failure is the contract, not dying on it.
    """
    ctx = get_context()
    if ctx.spec_error is not None:
        raise SquadsError(ctx.spec_error)
    active = ctx.active_spec
    return active if active is not None else bundled_spec()


def resolve_spec_for_ctx(ctx: Any) -> WorkflowSpec:
    """Resolve the ``WorkflowSpec`` for the current Click context, on the completion/help
    path where the root callback hasn't necessarily run yet.

    Tries, in order:

    1. The already-bound per-invocation spec (:func:`get_active_spec`) — set by the root
       callback's :func:`bind_active_spec`, and the fast path for ordinary subcommand dispatch
       (the callback fires before subcommand resolution).
    2. ``ctx.params["dir"]`` — the hoisted ``--dir`` value parsed on the root group's own
       params before its callback fires (covers ``sq --help`` and shell completion, where
       Click walks the command tree via ``list_commands``/``get_command`` without ever
       invoking the callback chain).
    3. The bundled spec, so a non-customized squad's ``--help``/completion stays
       byte-identical to before this existed.

    Never raises — every resolution step is fail-soft, matching the two call sites this
    consolidates (``_cli/__init__.py``'s ``_CustomTypeGroup`` and ``_cli/_create.py``'s
    ``_CustomCreateGroup``). That stays true under a broken override: this function only ever
    shapes ``--help`` text and the command table, and a *shell completion* that raised would
    be a worse failure than one listing the built-in set. The refusal belongs to the surfaces
    that answer questions about the squad — :func:`get_active_spec` and ``open_service`` — not
    to the parser that decides whether a word is a command.
    """
    try:
        active = get_context().active_spec
        if active is not None:
            return active

        dir_override: str | None = None
        if ctx is not None and hasattr(ctx, "params"):
            dir_override = ctx.params.get("dir")

        from squads._paths import resolve
        from squads._workflow._loader import (
            WORKFLOW_OVERRIDE_FILENAME,
            load_workflow_spec,
            validate_against_index_fail_closed,
        )

        sp = resolve(dir_override, client_cwd=get_context().client_cwd)
        override_path = sp.squad_dir / WORKFLOW_OVERRIDE_FILENAME
        if not override_path.is_file():
            return bundled_spec()
        merged = load_workflow_spec(squad_dir=sp.squad_dir)
        validate_against_index_fail_closed(merged, sp.squad_dir)
    except Exception:  # pylint: disable=broad-except
        # Deliberately the bundled spec, not get_active_spec() — that one refuses under a
        # broken override, and this path must not raise (see the docstring).
        return bundled_spec()
    else:
        return merged


def stale_static_aliases(spec: WorkflowSpec) -> frozenset[str]:
    """Every statically-registered type alias whose owner type is still declared but no longer
    declares that alias — a rename the static Click table never heard about.

    A *dropped* owner type is deliberately excluded: its aliases keep dispatching, into the
    canonical membership gate whose "unknown item type 'bug'" is the one refusal that owns the
    dropped-type message, named by the type rather than by whichever alias was typed (see
    ``_dropped_static_names``). Only the rename case has no such downstream answer.

    Empty for every non-customized squad — the bundled arrangement is exactly "each owner
    declares its own aliases".
    """
    return frozenset(
        alias
        for alias, owner in RESERVED_CLI_ALIASES
        if (owner_spec := spec.items.get(owner)) is not None and alias not in owner_spec.aliases
    )


def static_alias_is_stale(ctx: Any, cmd_name: str) -> bool:
    """True when *cmd_name* is a statically-registered type ALIAS that the resolved active
    spec no longer declares — the caller must then refuse to dispatch it.

    The root command table binds every bundled alias (``feat``/``f``/``t``/…) unconditionally
    at import time, so an override that renames ``feature``'s aliases to ``["ft"]`` leaves
    ``sq feat 9 show`` and ``sq f 9 show`` dispatching happily into the feature command tree
    and exiting 0 — an alias the spec does not declare, answering as though it did.

    Unlike a dropped *type name* (whose command is deliberately left reachable so the read
    path's own "unknown item type" refusal fires — see ``_dropped_static_names``), a stale
    alias has no accurate downstream refusal available: the type it routes to is usually
    still perfectly valid, so every layer below answers as if nothing were wrong. The caller
    substitutes :func:`stale_alias_command`, which supplies the missing refusal.

    Only ever *narrows* dispatch for a squad whose override touched those aliases: the owner
    type declaring the alias is the bundled arrangement, so a non-customized squad never takes
    the refusal branch. Fail-soft — any spec-resolution error returns ``False`` (dispatch as
    before), never a crash in ``--help``/completion.
    """
    if reserved_alias_owner(cmd_name) is None:
        return False
    try:
        spec = resolve_spec_for_ctx(ctx)
    except Exception:  # pylint: disable=broad-except
        return False
    return cmd_name in stale_static_aliases(spec)


def stale_alias_command(ctx: Any, cmd_name: str) -> _click.Command:
    """A one-off Click command that refuses a stale static alias, exit 1, naming the fix.

    Returning ``None`` from ``get_command`` instead would hand the refusal to Typer's own
    unknown-command handler, whose did-you-mean is built from the *raw registered command
    table* (``self.commands`` — not ``list_commands``, so no amount of hiding reaches it) and
    therefore suggests the exact stale string the user just typed. Dispatching into a real
    refusal is the same "advertise vs dispatch" split the dropped-type path already uses:
    the command stays reachable precisely so the one accurate message is the one that fires.

    Swallows every trailing token (``sq feat 9 show``) and its own ``--help``, so the refusal
    is what the user sees regardless of how the stale alias was invoked.
    """
    owner = reserved_alias_owner(cmd_name) or ""
    try:
        owner_spec = resolve_spec_for_ctx(ctx).items.get(owner)
    except Exception:  # pylint: disable=broad-except
        owner_spec = None
    # `stale_static_aliases` only reports an alias whose owner type IS declared, so the
    # aliases branch is the live case; the `None` guard is fail-soft belt-and-braces.
    declared_aliases = list(owner_spec.aliases) if owner_spec is not None else []
    if declared_aliases:
        detail = f"{owner!r} now declares {', '.join(repr(a) for a in declared_aliases)}"
    else:
        detail = f"{owner!r} now declares no aliases"

    refusal_app = typer.Typer()

    # `help_option_names: []` retires this command's own --help, so `sq feat --help` refuses
    # too instead of documenting an alias that no longer exists; `ignore_unknown_options`
    # keeps every trailing verb/flag out of the parser's way.
    @refusal_app.command(
        cmd_name,
        context_settings={"ignore_unknown_options": True, "help_option_names": []},
        hidden=True,
    )
    def _refuse(  # pyright: ignore[reportUnusedFunction] — registered by the decorator above
        rest: list[str] = typer.Argument(None, hidden=True),
    ) -> None:
        err_console.print(
            f"[red]error:[/red] {cmd_name!r} is not a declared item-type alias in this "
            f"squad's workflow spec — {e(detail)}. Use `sq {e(owner)}` instead.",
            soft_wrap=True,
        )
        raise typer.Exit(1)

    leaf: _click.Command = typer.main.get_command(refusal_app)  # type: ignore[assignment]
    leaf.name = cmd_name
    return leaf


def bind_active_spec(
    dir_override: str | None, client_cwd: Path | None
) -> tuple[WorkflowSpec | None, str | None]:
    """Resolve the WorkflowSpec for this invocation (does not bind it — the caller does, as
    part of the single per-invocation ``RequestContext``).

    Resolves and merges the squad-level workflow override (if present) exactly as
    ``open_service`` does, so parse_type/parse_status and display helpers all see the
    same spec. Returns ``(spec, spec_error)``:

    - **no squad / no override file** — ``(bundled spec, None)``, or ``(None, None)`` when
      even ``resolve()`` failed. Both mean "use the bundled spec", which is the honest answer:
      nothing was declared, so nothing is being substituted for.
    - **an override file that will not load** — ``(None, refusal)``. This is *not* a fall back
      to bundled. Falling soft here is what let ``sq workflow types/statuses/roles`` and the
      cheatsheet exit 0 describing the bundled vocabulary — the project's own declared type
      absent from all of them, with a client unable to detect it (exit 0, well-formed payload,
      empty stderr) — while ``sq list`` beside them exited 1 naming the very same error.
      A spec that fails to load is a hard stop at load, by rule: the type catalog is the only
      honest answer to "what types do I have", and a catalog rendered from a spec the project
      did not declare is not that answer.

    Lives here rather than in the root module so the two spec-resolution helpers sit
    together and the dependency runs one way: ``_cli/__init__`` already imports this
    module, and :func:`_pending_spec_error` needs the same resolution at the root group,
    where the callback that would have bound it has not run yet.

    ``client_cwd`` is threaded straight into ``resolve()`` — the same value the sibling
    ``_CustomTypeGroup._resolve_spec_for_ctx`` path uses (``get_context().client_cwd``) —
    so both spec-resolution paths agree on their resolution base rather than one of them
    silently falling back to ``resolve()``'s own ``Path.cwd()`` default.
    """
    from squads._paths import resolve
    from squads._workflow import bundled_spec
    from squads._workflow._loader import WORKFLOW_OVERRIDE_FILENAME, spec_refusal

    try:
        sp = resolve(dir_override, client_cwd=client_cwd)
        override_path = sp.squad_dir / WORKFLOW_OVERRIDE_FILENAME
        has_override = override_path.is_file()
    except Exception:  # pylint: disable=broad-except
        # Outside a squad, unreadable config, … — nothing was declared here to honour.
        return None, None
    if not has_override:
        return bundled_spec(), None

    from squads._workflow._loader import load_workflow_spec, validate_against_index_fail_closed

    try:
        merged_spec = load_workflow_spec(squad_dir=sp.squad_dir)
        validate_against_index_fail_closed(merged_spec, sp.squad_dir)
    except Exception as exc:  # pylint: disable=broad-except
        return None, spec_refusal(override_path, exc)
    else:
        return merged_spec, None


def _pending_spec_error(ctx: Any) -> str | None:
    """The workflow-override refusal in force for this invocation, or ``None``.

    Reads the bound :class:`~squads._context.RequestContext` first — the root callback has
    already resolved the override for every dispatch below the root group (``sq create
    widget``), so that is the whole answer there and costs nothing.

    At the *root* group it is not, and the ordering is the reason this helper exists: Click
    resolves a subcommand name before invoking the group's own callback, so ``sq widget 19
    show`` reaches ``get_command`` with nothing bound yet — the same "callback may not have run"
    path :func:`resolve_spec_for_ctx` was written for. Only then is the override resolved here,
    through :func:`bind_active_spec` itself rather than a second copy of its logic, so the refusal
    text is the one every other surface prints and cannot drift from it.

    Fail-soft throughout: a squad with no override, or one that cannot even be located, yields
    ``None`` and the caller falls back to Click's own handling.
    """
    from squads._context import get_context

    bound = get_context()
    if bound.spec_error is not None:
        return bound.spec_error
    if bound.active_spec is not None or ctx is None:
        return None  # the callback ran and reported no refusal — the spec is fine
    try:
        dir_override = ctx.params.get("dir") if hasattr(ctx, "params") else None
        _spec, error = bind_active_spec(dir_override, bound.client_cwd)
    except Exception:  # pylint: disable=broad-except
        return None
    return error


def spec_error_command(cmd_name: str, ctx: Any = None) -> _click.Command | None:
    """A refusal command for a name the parser cannot classify because the squad's workflow
    override did not load — or ``None`` when the spec is fine and the name is simply unknown.

    The command table was the last surface still answering from bundled vocabulary. Every
    command that opens a service or reads the active spec refuses with the shared text, but a
    name the static table does not carry was resolved against the *bundled* spec (the parser
    must never raise, so :func:`resolve_spec_for_ctx` falls back), found absent, and handed to
    Click — which exits 2 with ``No such command 'widget'``. For a squad whose own override
    declares ``widget`` and whose board holds live ``WID-*`` items, that is not a degraded
    answer but a wrong one: "no such command" is a claim about *this squad's* vocabulary, made
    from a document this squad did not declare, and it points the adopter at their spelling
    instead of at the file that failed to load.

    So when — and only when — the override is known to have failed
    (``RequestContext.spec_error``, set by the root callback), an unclassifiable name dispatches
    into the same refusal ``sq list`` gives, at the same exit code. Same "advertise vs dispatch"
    split :func:`stale_alias_command` uses, for the same reason: returning ``None`` hands the
    answer to Click's unknown-command handler, whose did-you-mean is built from the raw static
    table and would suggest a bundled type name in place of the adopter's own.

    ``None`` whenever no refusal is in force, so a genuine typo on a healthy squad keeps
    Click's "No such command" — the accurate answer *there*, and the reason this is not simply
    a blanket refusal. See :func:`_pending_spec_error` for how the refusal is found at the root
    group, where the callback that would have bound it has not run yet.
    """
    message = _pending_spec_error(ctx)
    if message is None:
        return None

    refusal_app = typer.Typer()

    @refusal_app.command(
        cmd_name,
        context_settings={"ignore_unknown_options": True, "help_option_names": []},
        hidden=True,
    )
    def _refuse(  # pyright: ignore[reportUnusedFunction] — registered by the decorator above
        rest: list[str] = typer.Argument(None, hidden=True),
    ) -> None:
        err_console.print(f"[red]error:[/red] {e(message)}", soft_wrap=True)
        raise typer.Exit(1)

    leaf: _click.Command = typer.main.get_command(refusal_app)  # type: ignore[assignment]
    leaf.name = cmd_name
    return leaf


def e(value: object) -> str:
    """Escape a dynamic string so Rich does not interpret ``[...]`` as markup."""
    return escape(str(value))


#: Concrete `rich` colour per semantic colour intent (the closed palette declared as
#: ``squads._workflow._models.COLOR_INTENTS``) — the CLI's own per-client rendering of the
#: role's colour axis: colour is single-sourced as an intent in the spec, mapped to a
#: concrete colour per client. A total map over the palette plus a ``"neutral"`` (no colour)
#: entry that also serves as the fallback for any intent this build doesn't recognise.
INTENT_COLORS: dict[str, str] = {
    "positive": "green",
    "danger": "red",
    "warning": "yellow",
    "info": "cyan",
    "muted": "bright_black",
    "neutral": "",
}


def status_style(status: str, spec: WorkflowSpec) -> str:
    """The concrete `rich` style for *status* — joins ``status -> role_for(status).color ->
    INTENT_COLORS``. An intent absent from the map (a future/custom colour word this build
    doesn't know) falls back to the neutral (uncoloured) style rather than raising."""
    intent = spec.role_for(status).color
    return INTENT_COLORS.get(intent, INTENT_COLORS["neutral"])


def status_text(status: str, spec: WorkflowSpec) -> Text:
    """A ``Text`` renderable for *status*, coloured by its role's colour intent.

    Applies the style via Rich's ``style=`` parameter rather than interpolating
    ``[colour]...[/]`` markup around the string — the same escaping discipline as :func:`e`,
    so colouring a status never opens a markup-injection path.
    """
    return Text(status, style=status_style(status, spec))


def print_block(parent_id: str, res: BlockResult, json_out: bool) -> None:
    """Report a scaffolded story/subtask/finding block + where the agent should write its body."""
    if json_out:
        data: dict[str, object] = {
            "local_id": res.local_id,
            "file": str(res.path),
            "region": res.body_tag,
            "start_line": res.start_line,
            "end_line": res.end_line,
        }
        if res.title_advisory is not None:
            data["title_advisory"] = res.title_advisory
        print_json_clean(json.dumps(data))
        return
    kind = res.body_tag.split(":")[0]  # e.g. "subtask:STn:body" → "subtask"
    console.print(f"added [bold]{res.local_id}[/bold] to {parent_id}")
    console.print(
        f'  set its body:  [cyan]sq {kind} body {parent_id} {res.local_id} -m "…"[/cyan]'
        "  [dim](or --file body.md / --file -)[/dim]",
        soft_wrap=True,
    )
    if res.title_advisory is not None:
        console.print(e(res.title_advisory))


def _is_styled() -> bool:
    """True when Rich will actually render markup (TTY + color enabled)."""
    # Console.is_terminal is False when stdout is piped; NO_COLOR collapses markup too.
    return console.is_terminal and not console.no_color


def _render_comments_plain(comments: list[discussion.Comment]) -> None:
    """Render comments as plain delimited text (piped / NO_COLOR / --raw degradation).

    Uses raw (un-escaped) values because markup=False is in effect — e() escaping must not be
    applied here or it will leak backslashes into the plain output.
    """
    for cmt in comments:
        header = f"--- [{cmt.timestamp}] {cmt.author} ---"
        console.print(header, markup=False, highlight=False)
        console.print(cmt.body, markup=False, highlight=False)
        console.print()


def _render_comments_styled(comments: list[discussion.Comment]) -> None:
    """Render each comment as a Rich Panel (TTY, color enabled, not --raw)."""
    for cmt in comments:
        title = f"{e(cmt.timestamp)}  {e(cmt.author)}"
        # Body is parsed markdown; pass through Markdown() so bullets/code are styled.
        # We do NOT escape here — the body is trusted markdown content, not user-input markup.
        console.print(Panel(Markdown(cmt.body), title=title, expand=False))


def print_comments(comments: list[discussion.Comment]) -> None:
    """Render a comment list the same way `show --comments` does (styled panes on a TTY, plain
    delimited text when piped/NO_COLOR) — for the dedicated `comments` read-back verb, or an
    empty-discussion "no comments" line rather than an error."""
    if not comments:
        console.print("[dim](no comments)[/dim]")
        return
    if _is_styled():
        _render_comments_styled(comments)
    else:
        _render_comments_plain(comments)


def _build_item_panel_rows(it: Item) -> list[str]:
    """Build the metadata rows for the item's info panel."""
    rows = [
        f"[bold]{it.id}[/bold]  ({it.type})",
        f"[bold]title:[/bold] {e(it.title)}",
        f"[bold]status:[/bold] {it.status}",
    ]
    # Badge rows: one per field this type declares (priority, severity, or a project's own
    # custom axis) — generic over fields_for(), not a hand-written priority/severity pair.
    spec = get_active_spec()
    for field in spec.fields_for(it.type):
        val = it.badge_value(field.code)
        if val:
            rendered = badges.badge_render(field.collection, val, spec)
            rows.append(f"[bold]{field.code}:[/bold] {e(rendered)}")
    if it.description:
        rows.append(f"[bold]summary:[/bold] {e(it.description)}")
    if it.parent:
        rows.append(f"[bold]parent:[/bold] {it.parent}")
    if it.author:
        if it.created_session:
            rows.append(
                f"[bold]author:[/bold] {e(it.author)}"
                f" [dim]@ {e(it.created_session)}[/dim]"
                " [dim](best-effort session, untrusted)[/dim]"
            )
        else:
            rows.append(f"[bold]author:[/bold] {e(it.author)}")
    if it.modified_session:
        rows.append(
            f"[bold]last-modified session:[/bold] [dim]{e(it.modified_session)}[/dim]"
            " [dim](best-effort, untrusted)[/dim]"
        )
    if it.assignee:
        rows.append(f"[bold]assignee:[/bold] {e(it.assignee)}")
    if it.labels:
        rows.append(f"[bold]labels:[/bold] {e(', '.join(it.labels))}")
    if it.refs:
        rendered = ", ".join(
            rid if kind == DEFAULT_KIND else f"{rid} ({kind})"
            for rid, kind in (split_ref(r) for r in it.refs)
        )
        rows.append(f"[bold]refs:[/bold] {e(rendered)}")
    rows.append(f"[bold]file:[/bold] {it.path}")
    return rows


def _subentity_badge_line(sub: SubEntity, kind: str) -> str:
    """The badges for a sub-entity, joined for a single display line: status, then one per
    declared field with a stored value, then the assignee, then the mapped story iff the kind
    declares ``maps_parent_story``.

    Generic over the kind's declared fields (spec-driven, not a ``kind == "finding"``/
    ``"subtask"`` literal). Shared by the styled pane title and the ``--raw`` markdown section.
    """
    spec = get_active_spec()
    parts = [badges.status_badge(sub.status, spec)]
    for field in spec.fields_for(kind):
        value = sub.badge_value(field.code)
        if value:
            coll = badges.resolve_collection(kind, field.code, spec)
            parts.append(badges.badge_render(coll, value, spec, as_label=True))
    if sub.assignee:
        parts.append(sub.assignee)
    ks = spec.subentity_kinds.get(kind)
    if ks is not None and ks.maps_parent_story and sub.story:
        parts.append(sub.story)
    return "  ".join(parts)


def _subentity_pane_title_raw(sub: SubEntity, kind: str) -> str:
    """Build the raw (un-escaped) pane title for a sub-entity.

    Returns plain text with no Rich markup escaping applied.  Callers that need to pass the title
    into a Rich Panel (styled path) must apply e() themselves; callers printing with markup=False
    (plain path) use this value directly so no backslashes leak.
    """
    return f"{sub.local_id} — {sub.title}  {_subentity_badge_line(sub, kind)}"


async def _print_full_panes(svc: Service, it: Item, *, styled: bool, comments: bool) -> None:
    """Render one pane per sub-entity with its body (and optionally its comments).

    Called when --full is set; comment embedding per sub is gated on --comments.
    Sub-entity panes are printed after the summary table.  When comments is True,
    the main discussion is NOT printed here — the caller (_print_item_content)
    prints it last, after all sub panes.
    """
    kind = get_active_spec().item_subentity_kind(it.type)
    if not kind or not it.subentities:
        return

    for sub in it.subentities:
        detail = await svc.get_block(it.id, kind, sub.local_id)
        # Build the raw (un-escaped) title once; apply e() only at the styled Panel boundary.
        raw_title = _subentity_pane_title_raw(sub, kind)
        body_text = detail.body or ""

        if styled:
            inner_renderables: list[RenderableType] = []
            if body_text:
                inner_renderables.append(Markdown(body_text))
            if comments:
                sub_cmts = discussion.split_discussion(detail.discussion)
                if sub_cmts:
                    for cmt in sub_cmts:
                        cmt_title = f"{e(cmt.timestamp)}  {e(cmt.author)}"
                        inner_renderables.append(
                            Panel(Markdown(cmt.body), title=cmt_title, expand=False)
                        )

            # If we have renderables, put them inside a Group so Panel gets one renderable.
            body_renderable: RenderableType
            if inner_renderables:
                body_renderable = Group(*inner_renderables)
            else:
                body_renderable = Markdown("_(empty)_")
            # e() applied here — only the styled Panel title needs Rich-escaped text.
            console.print(Panel(body_renderable, title=e(raw_title), expand=False))
        else:
            # Plain degradation: use raw_title directly — markup=False, no escaping needed.
            console.print(f"=== {raw_title} ===", markup=False, highlight=False)
            if body_text:
                console.print(body_text, markup=False, highlight=False)
            if comments:
                sub_cmts = discussion.split_discussion(detail.discussion)
                _render_comments_plain(sub_cmts)
            console.print()


def _render_body(body_text: str, *, styled: bool, empty_hint: str | None = None) -> None:
    """Low-level body renderer: styled Markdown or plain, preceded by a blank line.

    Callers must pre-compute ``styled`` (``_is_styled() and not raw``).
    Pass ``empty_hint`` to override the default "set it with `body`" hint, e.g. for
    role/skill/operator groups where there is no ``body`` verb.
    """
    console.print()
    if body_text:
        if styled:
            console.print(Markdown(body_text))
        else:
            console.print(body_text, markup=False, highlight=False)
    else:
        hint = empty_hint if empty_hint is not None else "(empty — set it with `body`)"
        console.print(f"[dim]{hint}[/dim]")


def render_body_text(body_text: str, *, raw: bool = False, empty_hint: str | None = None) -> None:
    """Render a body string to the console: styled Markdown on a TTY, plain otherwise.

    Computes the styled/plain decision via :func:`_is_styled` + ``raw``.  Use this from
    role/skill/operator ``show`` commands; :func:`_print_item_content` uses :func:`_render_body`
    directly with a pre-computed ``styled`` flag.
    Always emits a leading blank line before the content.
    Pass ``empty_hint`` to override the default empty-body hint (e.g. for groups without a
    ``body`` verb — role/skill/operator bodies are template-managed, so ``sq sync`` is the
    right pointer, not ``body``).
    """
    _render_body(body_text, styled=_is_styled() and not raw, empty_hint=empty_hint)


async def _print_item_content(
    svc: Service, it: Item, *, styled: bool, comments: bool, full: bool = False
) -> None:
    """Render the body, sub-entity summary, and optional comments for a non-role/skill item."""
    body = await svc.read_body(it.id)
    _render_body(body, styled=styled)

    # Sub-entity summary table — always shown (not gated on --full); driven from the stored
    # sub-entities, not a re-parse of the markdown table.
    if it.subentities:
        _print_subentity_summary(it)

    # --full: one pane per sub-entity (body + optional per-sub comments)
    if full:
        await _print_full_panes(svc, it, styled=styled, comments=comments)

    # --comments: render the main discussion last (after sub panes when --full is set)
    if comments:
        await _print_discussion(svc, it, styled=styled)


async def _print_discussion(svc: Service, it: Item, *, styled: bool) -> None:
    """Render the main discussion as per-comment panes or plain blocks."""
    cmt_list = discussion.split_discussion(await svc.read_discussion(it.id))
    if cmt_list:
        console.print()
        if styled:
            _render_comments_styled(cmt_list)
        else:
            _render_comments_plain(cmt_list)
    else:
        console.print("[dim](no discussion)[/dim]")


def _raw_metadata_lines(it: Item) -> list[str]:
    """The ``- **key:** value`` bullets for the ``--raw`` markdown metadata block.

    Order: status, per-type badge fields (priority/severity/... — spec-driven, not hard-coded),
    assignee, parent, author, refs, labels — absent fields omitted. Plain text: the raw path
    bypasses Rich markup entirely, so nothing here is escaped with :func:`e`.
    """
    spec = get_active_spec()
    lines = [f"- **status:** {it.status}"]
    for field in spec.fields_for(it.type):
        val = it.badge_value(field.code)
        if val:
            rendered = badges.badge_render(field.collection, val, spec)
            lines.append(f"- **{field.code}:** {rendered}")
    if it.assignee:
        lines.append(f"- **assignee:** {it.assignee}")
    if it.parent:
        lines.append(f"- **parent:** {it.parent}")
    if it.author:
        lines.append(f"- **author:** {it.author}")
    if it.refs:
        rendered_refs = ", ".join(
            rid if kind == DEFAULT_KIND else f"{rid} ({kind})"
            for rid, kind in (split_ref(r) for r in it.refs)
        )
        lines.append(f"- **refs:** {rendered_refs}")
    if it.labels:
        lines.append(f"- **labels:** {', '.join(it.labels)}")
    return lines


async def _raw_subentity_sections(svc: Service, it: Item) -> list[str]:
    """One ``## <Kind> <local_id> — <title>`` section per sub-entity, for ``--raw --full``."""
    kind = get_active_spec().item_subentity_kind(it.type)
    if not kind or not it.subentities:
        return []
    lines: list[str] = []
    for sub in it.subentities:
        detail = await svc.get_block(it.id, kind, sub.local_id)
        lines += [
            "",
            f"## {kind.title()} {sub.local_id} — {sub.title}",
            "",
            _subentity_badge_line(sub, kind),
            "",
            detail.body or "",
        ]
    return lines


async def _print_item_raw(svc: Service, it: Item, *, comments: bool, full: bool) -> None:
    """The ``--raw`` dossier: a deterministic, markdown-preview-clean markdown document.

    ``# TYPE-N — <title>``, a metadata bullet block, a blank line, then the body markdown
    verbatim; ``--full`` appends one section per sub-entity, ``--comments`` appends a Discussion
    section — zero Rich chrome (no box-panel header, no summary table, no ``=== … ===``
    separators). Printed via a single ``console.print(..., markup=False, soft_wrap=True)`` so
    nothing is escaped or reflowed (see the ``sq docs`` raw-markdown path for the same pattern).
    """
    lines = [
        f"# {it.id} — {it.title}",
        "",
        *_raw_metadata_lines(it),
        "",
        await svc.read_body(it.id),
    ]
    if full:
        lines.extend(await _raw_subentity_sections(svc, it))
    if comments:
        cmts = discussion.split_discussion(await svc.read_discussion(it.id))
        lines += ["", "## Discussion"]
        if cmts:
            for cmt in cmts:
                lines += ["", f"### {cmt.author} — {cmt.timestamp}", "", cmt.body]
        else:
            lines += ["", "_(no discussion)_"]
    console.print("\n".join(lines), markup=False, highlight=False, soft_wrap=True)


async def print_item(
    svc: Service,
    it: Item,
    *,
    raw: bool = False,
    comments: bool = False,
    full: bool = False,
) -> None:
    """Render an item's metadata + body (for ``sq <type> <num> show``).

    ``--raw`` renders the clean-markdown dossier (:func:`_print_item_raw`) — no Rich chrome at
    all, suitable for piping straight into a markdown viewer. Any other invocation (TTY or
    piped, styled or not) keeps the existing Rich panel + summary table rendering unchanged:
    on a TTY (with color) the body is styled Rich Markdown, piped / ``NO_COLOR`` falls back to
    plain text.
    ``--comments`` appends the discussion as per-comment panes. ``--full`` adds one pane per
    sub-entity (body, badges); combined with ``--comments`` each sub-entity pane embeds its own
    comments and the main discussion closes the output.
    """
    if raw:
        await _print_item_raw(svc, it, comments=comments, full=full)
        return
    console.print(Panel("\n".join(_build_item_panel_rows(it)), expand=False))
    styled = _is_styled()
    await _print_item_content(svc, it, styled=styled, comments=comments, full=full)


def _print_subentity_summary(it: Item) -> None:
    """Print the sub-entity summary table from the item's frontmatter sub-entities.

    Columns and cells come from the shared field-driven derivation in ``_discussion.py``
    (:func:`discussion.summary_columns`/:func:`discussion.summary_row`) — the same one the
    body's ``:summary`` region renders from, so the two never drift.
    """
    from rich.table import Table as RichTable

    spec = get_active_spec()
    kind = spec.item_subentity_kind(it.type)
    if kind is None:
        return

    table = RichTable(box=None, pad_edge=False)
    for col in discussion.summary_columns(kind, spec):
        table.add_column(col)
    for sub in it.subentities:
        cells = discussion.summary_row(kind, sub, spec)
        table.add_row(*(e(c) for c in cells))

    console.print()
    console.print(table)


def print_subentity(detail: SubentityDetail, kind: str) -> None:
    """Render a sub-entity's meta + body + discussion for `sq <kind> show`."""
    info = detail.info
    console.print(f"[bold]{info.local_id}[/bold] — {e(info.title)}  [dim]({kind})[/dim]")
    meta = [f"status: {e(info.status)}"]
    if info.assignee:
        meta.append(f"assignee: {e(info.assignee)}")
    # Every declared field for this kind (severity today; any custom axis on a custom kind
    # tomorrow) — not just the severity-only slot, so a custom badge field actually shows up.
    for field in get_active_spec().fields_for(kind):
        value = info.badge_value(field.code)
        if value:
            meta.append(f"{field.label.lower()}: {e(value)}")
    if info.story:
        meta.append(f"story: {e(info.story)}")
    console.print("  " + "   ".join(meta))
    console.print()
    console.print(e(detail.body) if detail.body else "[dim](no body yet)[/dim]")
    console.print("\n[bold]Discussion[/bold]")
    console.print(e(detail.discussion) if detail.discussion else "[dim](none)[/dim]")


def resolve_body_optional(messages: list[str] | None, file: str | None) -> str | None:
    """Body from repeatable -m paragraphs or a --file path ('-' = stdin); at most one source."""
    if messages and file:
        raise SquadsError("provide the body via -m or --file, not both")
    if file is not None:
        if file == "-":
            return sys.stdin.read().strip("\n")
        try:
            return Path(file).read_text(encoding="utf-8").strip("\n")
        except OSError as exc:
            raise SquadsError(f"cannot read body file {file!r}: {exc.strerror or exc}") from exc
    if messages:
        return "\n\n".join(messages)
    return None


def resolve_body(messages: list[str] | None, file: str | None) -> str:
    body = resolve_body_optional(messages, file)
    if body is None:
        raise SquadsError("provide the body via -m (repeatable) or --file PATH ('-' for stdin)")
    return body


def build_subentity_json(spec: WorkflowSpec, kind: str, detail: SubentityDetail) -> dict[str, Any]:
    """The one sub-entity JSON object shape — shared by each ``subentities`` entry in
    :func:`build_item_json` and the standalone ``sq <type> <n> <kind> <k> show --json``
    (:func:`squads._cli._items._register_sub_verbs`), so the two surfaces are built from one
    path and cannot drift into two different shapes.

    Frontmatter fields (``local_id``/``title``/``status``/``assignee``/``severity``/
    ``story``/``extra``) plus ``body``, the generic per-field ``badges`` map, and an additive
    ``discussion`` array (ordered ``{author, ts, body}``, same shape/order as the item-level
    one) — generic across every sub-entity kind, since sub-entity discussion is not per-kind.
    """
    data: dict[str, Any] = json.loads(detail.info.model_dump_json())
    data["body"] = detail.body
    data["badges"] = badges.resolve_badges(spec, kind, detail.info.badge_value)
    data["discussion"] = [
        {"author": cmt.author, "ts": cmt.timestamp, "body": cmt.body}
        for cmt in discussion.split_discussion(detail.discussion)
    ]
    return data


async def build_item_json(svc: Service, it: Item) -> str:
    """The ``show --json`` payload: frontmatter fields plus body/discussion — additive only.

    Adds top-level ``body`` (raw body markdown), ``discussion`` (ordered ``{author, ts,
    body}`` list), and ``badges`` (the generic per-item badge map, keyed by field
    code — see :func:`squads._badges.resolve_badges`); plus, per ``subentities`` entry, the
    shared shape built by :func:`build_subentity_json` (adds ``body``, ``badges``, and
    ``discussion``). Added unconditionally — not gated by ``--comments``/``--full`` — so the
    existing invariant that ``show --json`` is byte-identical across
    ``--raw``/``--comments``/``--full`` still holds. Nothing existing is renamed or removed.
    """
    spec = get_active_spec()
    payload: dict[str, Any] = json.loads(it.model_dump_json())
    payload["body"] = await svc.read_body(it.id)
    payload["discussion"] = [
        {"author": cmt.author, "ts": cmt.timestamp, "body": cmt.body}
        for cmt in discussion.split_discussion(await svc.read_discussion(it.id))
    ]
    payload["badges"] = badges.resolve_badges(spec, it.type, it.badge_value)
    kind = spec.item_subentity_kind(it.type)
    if kind:
        subentities: list[dict[str, Any]] = []
        for sub_data in payload["subentities"]:
            detail = await svc.get_block(it.id, kind, sub_data["local_id"])
            subentities.append(build_subentity_json(spec, kind, detail))
        payload["subentities"] = subentities
    return json.dumps(payload)


#: ``click.Context.meta`` key: presence means *this* CLI invocation's read scope was opened
#: by an earlier ``command``-wrapped call in the same dispatch tree and is still open, so a
#: later call must not open a second one. Prefixed per Click's own convention for ``meta``
#: keys (avoid colliding with another extension's).
_READ_SCOPE_META_KEY = "squads.read_scope_token"

#: ``click.Context.meta`` key for the invocation-scoped ``Service`` memo (see
#: :func:`get_service`). Populated only by the *plain* (``open_service``, cross-checked)
#: construction path — never by the bypass path below — so a plain caller can never be handed
#: a bypass-built instance by reading this key.
_SERVICE_META_KEY = "squads.service_memo"

#: ``click.Context.meta`` key for the bypass-built ``Service`` memo (see
#: :func:`get_service_bypassing_index_cross_check`). Populated only when the plain path has
#: actually raised, so a caller that asked for the cross-check never ends up with an instance
#: that skipped it.
_BYPASS_SERVICE_META_KEY = "squads.service_memo_bypass"


def _click_root_context() -> _click.core.Context | None:
    """The current Click invocation's root context, or ``None`` outside of one.

    ``command``-wrapped functions are only ever invoked *by* Click, so this only returns
    ``None`` in the one case that matters: a stray direct call with no Click dispatch at all
    (defensive; never observed in practice).
    """
    ctx = _click_globals.get_current_context(silent=True)
    return ctx.find_root() if ctx is not None else None


def get_service() -> Service:
    """Build (or reuse) the invocation's ``Service``.

    ``sq <type> <n> <verb>`` crosses the sync/async bridge twice for one user-facing
    invocation — the Typer group's id-resolving callback and the leaf verb, as two sequential
    ``anyio.run`` calls (see :func:`command`) — and each used to mint its own ``Service`` and
    its own ``IndexStore``, so the read scope's per-store cache never actually shared a store
    across them: two reads for one invocation, short of the request-scoped read design's
    "one invocation observes one index state" promise for that form.

    Memoized on the same anchor the read scope already uses — the Click root context's
    ``meta`` — and gated on the *same* condition that opens the scope
    (:data:`_READ_SCOPE_META_KEY` present), not merely on a root context existing. That gate is
    what keeps ``sq ui`` — a sync command that never passes through :func:`command`, so no
    scope is ever opened for it — from also getting a Service pinned for its session: it opts
    out of both for the same reason, on the same check, rather than needing a second one to
    remember.
    """
    root = _click_root_context()
    if root is not None and _READ_SCOPE_META_KEY in root.meta:
        cached: Service | None = root.meta.get(_SERVICE_META_KEY)
        if cached is not None:
            return cached
        svc = _build_plain_service()
        root.meta[_SERVICE_META_KEY] = svc
        return svc
    return _build_plain_service()


def _build_plain_service() -> Service:
    """Build the invocation's ``Service`` via ``open_service``, without repeating work the
    root callback's :func:`bind_active_spec` already did for this exact invocation.

    ``RequestContext.active_spec`` is that already-resolved spec — merged and, for an
    override, already cross-checked against the live index — so it is threaded straight
    through as ``open_service``'s ``resolved_spec``, which skips re-running
    ``load_workflow_spec``/``validate_against_index_fail_closed`` a second time on the same
    corpus. ``RequestContext.spec_error`` is the cached refusal from that same earlier
    resolution: raised directly rather than calling ``open_service`` again just to have it
    reproduce the identical ``SquadsError`` a second time (and reparse the index a second time
    doing so). This is the second memo A4 asks to hang off the first (:data:`_SERVICE_META_KEY`
    already collapses the two bridge crossings into one construction) — not a second anchor,
    just this call reading the one spec resolution the root callback already anchored.

    Outside a squad (``bind_active_spec`` itself couldn't resolve a dir) both fields are
    ``None`` and this falls through to ``open_service``'s own independent resolution, which
    raises the same "not a squad" error it always has.
    """
    ctx = get_context()
    if ctx.spec_error is not None:
        raise SquadsError(ctx.spec_error)
    return open_service(ctx.active_dir, client_cwd=ctx.client_cwd, resolved_spec=ctx.active_spec)


def get_service_bypassing_index_cross_check() -> Service:
    """Like :func:`get_service`, but for the one class of caller that must never be blocked by
    ``open_service``'s live-index cross-check: a maintenance command whose entire job is fixing
    exactly what that cross-check can refuse over — a corpus/spec conflict, or (just as often) a
    rebuildable index merely stale relative to the frontmatter it should mirror. A validation
    gate that locks out its own recovery path is not a recovery path.

    Falls back, in order:

    1. The normal path (:func:`get_service` / ``open_service``) — the overwhelming majority of
       invocations hit this and nothing changes.
    2. On a ``SquadsError``, the merged (override-aware) spec with no live-index cross-check
       (``load_workflow_spec`` alone, which never touches the index) — so the caller still
       resolves a custom type's correct folder/prefix from the active override; it just isn't
       blocked by a corpus mismatch the cross-check would refuse over.
    3. If even that fails (a genuinely broken override, unrelated to the index), the bundled
       spec — the same last-resort ``sq check`` already falls back to for the same reason.

    The fallback instance (step 2/3) is memoized under its own key
    (:data:`_BYPASS_SERVICE_META_KEY`), separate from :func:`get_service`'s
    (:data:`_SERVICE_META_KEY`), so the two constructions can never shadow each other within
    one invocation: a plain caller reading :data:`_SERVICE_META_KEY` can never observe a
    cross-check-skipping instance, and this function reusing its own memo never masks a
    genuine, still-current refusal behind a stale success.
    """
    root = _click_root_context()
    if root is not None and _READ_SCOPE_META_KEY in root.meta:
        cached: Service | None = root.meta.get(_BYPASS_SERVICE_META_KEY)
        if cached is not None:
            return cached
        try:
            return get_service()
        except SquadsError:
            svc = _build_bypass_fallback_service()
            root.meta[_BYPASS_SERVICE_META_KEY] = svc
            return svc
    try:
        return get_service()
    except SquadsError:
        return _build_bypass_fallback_service()


def _build_bypass_fallback_service() -> Service:
    ctx = get_context()
    sp = resolve(ctx.active_dir, client_cwd=ctx.client_cwd)
    try:
        from squads._workflow._loader import load_workflow_spec

        merged_spec = load_workflow_spec(squad_dir=sp.squad_dir)
    except SquadsError:
        merged_spec = bundled_spec()
    return Service(sp, spec=merged_spec)


def handle_errors[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return fn(*args, **kwargs)
        except SquadsError as exc:
            err_console.print(f"[red]error:[/red] {e(exc)}", soft_wrap=True)
            raise typer.Exit(1) from exc

    return wrapper


def command[**P](fn: Callable[P, Awaitable[None]]) -> Callable[P, None]:
    """The single sync→async bridge for CLI commands.

    Wraps an ``async def`` Typer command so Typer sees a sync callable, there is exactly one
    ``anyio.run`` per invocation, and ``SquadsError`` becomes a clean message + ``typer.Exit(1)``
    (subsuming the old ``@handle_errors``).

    Also where a request-scoped index read (:func:`squads._index._store.read_scope`'s
    underlying ``enter_read_scope``/``exit_read_scope`` pair) is opened for the invocation, and
    where the invocation-scoped ``Service`` memo (:func:`get_service`) becomes live — both hang
    off the same root-context marker (:data:`_READ_SCOPE_META_KEY`), one anchor for both.
    ``sq <type> <n> <verb>`` crosses *this* bridge twice for one invocation the user thinks
    of as one command — once for the Typer group's own id-resolving ``@item.callback()``
    (e.g. ``_resolve`` in ``_cli/_items.py``), and again for the leaf verb — two separate,
    sequential ``anyio.run`` calls, not one nested inside the other, so a scope opened inside
    the first call's own coroutine is already closed before the second call's coroutine
    starts. Both calls share exactly one Click root ``Context`` for the one real invocation
    they're both part of (Click builds it once per dispatch, before resolving anything), so
    the *first* ``command``-wrapped call in the tree opens the scope and records that on the
    root context's ``meta`` (:data:`_READ_SCOPE_META_KEY`); every later call in the same tree
    sees that marker, leaves the existing scope alone, and — because ``get_service()`` gates
    its own memo on that same marker — reuses the first call's ``Service`` instead of minting a
    second one. That is what takes the addressed-item form from two index reads to one: before
    this, each crossing built its own ``Service``/``IndexStore``, so the read scope's
    store-identity-keyed cache never actually had a store to share. The root context's own
    ``call_on_close`` — which Click fires exactly once, after every nested command in the
    tree has finished, success or error — is what closes it, so teardown happens once, at the
    true end of the invocation, not at the end of whichever call happened to open it.

    ``sq ui`` is a sync command that never passes through here at all, so it opts out for
    free and keeps today's always-fresh behaviour — no scope, no memoized ``Service``, both on
    the one gate.
    """

    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
        root = _click_root_context()
        if root is not None and _READ_SCOPE_META_KEY not in root.meta:
            root.meta[_READ_SCOPE_META_KEY] = enter_read_scope()
            root.call_on_close(functools.partial(_close_read_scope, root))
        try:
            anyio.run(functools.partial(fn, *args, **kwargs))
        except SquadsError as exc:
            err_console.print(f"[red]error:[/red] {e(exc)}", soft_wrap=True)
            raise typer.Exit(1) from exc

    return wrapper


def _close_read_scope(root: _click.core.Context) -> None:
    """``call_on_close`` callback: undo the one scope opened for this invocation, if any, and
    drop the ``Service`` memo(s) that hung off the same marker — nothing outlives the
    invocation that built it."""
    token = root.meta.pop(_READ_SCOPE_META_KEY, None)
    if token is not None:
        exit_read_scope(token)
    root.meta.pop(_SERVICE_META_KEY, None)
    root.meta.pop(_BYPASS_SERVICE_META_KEY, None)


def version_tuple(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for p in version.split("."):
        num = "".join(c for c in p if c.isdigit())
        parts.append(int(num) if num else 0)
    return tuple(parts)


def version_notice() -> None:
    """Print a non-fatal notice if the installed squads is newer than the managed files."""
    try:
        sp = resolve(get_context().active_dir, client_cwd=get_context().client_cwd)
    except SquadsError:
        return  # not initialized yet (e.g. before `sq init`)
    recorded = sp.config.squads_version
    if recorded and version_tuple(__version__) > version_tuple(recorded):
        err_console.print(
            f"[yellow]squads {__version__} detected (managed files at {recorded}). "
            f"Run `sq sync` to refresh them.[/yellow]",
            soft_wrap=True,
        )


def require_current_schema(subcommand: str | None) -> None:
    """Hard-stop when the squad's on-disk schema mismatches this build — except for migrate/help.

    Behind → tell the user to run ``sq migrate``; ahead → tell them to upgrade the package.
    """
    if subcommand in (None, "migrate") or "--help" in sys.argv or "-h" in sys.argv:
        return
    try:
        sp = resolve(get_context().active_dir, client_cwd=get_context().client_cwd)
    except SquadsError:
        return  # not initialized yet — nothing to gate
    disk = sp.config.schema_version
    if disk == SCHEMA_VERSION:
        return
    if schema_tuple(disk) < schema_tuple(SCHEMA_VERSION):
        err_console.print(
            f"[red]error:[/red] this squad is at schema v{disk}; squads {__version__} "
            f"expects v{SCHEMA_VERSION}. Run [bold]sq migrate up[/bold] to upgrade it "
            "(see `sq migrate help`).",
            soft_wrap=True,
        )
    else:
        err_console.print(
            f"[red]error:[/red] this squad is at schema v{disk}, newer than squads "
            f"{__version__} (v{SCHEMA_VERSION}). Upgrade the squads package.",
            soft_wrap=True,
        )
    raise typer.Exit(1)


def _article(word: str) -> str:
    """Return ``"an"`` for vowel-initial words, ``"a"`` otherwise."""
    return "an" if word and word[0].lower() in "aeiou" else "a"


def _mismatch_msg(label: str, actual_id: str, actual_type: str, expected_type: str) -> str:
    """Build a uniform type-mismatch error: ``"<label> is <id> (<type>), not a/an <type>"``."""
    return f"{label} is {actual_id} ({actual_type}), not {_article(expected_type)} {expected_type}"


def _parse_item_token(token: str) -> tuple[int, str | None]:
    """Parse a CLI item token into ``(sequence_number, prefix_or_None)``.

    Accepts bare numbers (``"35"``, ``"000035"``) and full IDs (``"PREFIX-000035"``).
    Returns ``(seq, None)`` for bare numbers and ``(seq, head_upper)`` for full IDs.
    Raises :class:`SquadsError` on unparseable input.

    Used by :func:`resolve_item_id_typed` and :func:`resolve_item_id_any` to avoid
    duplicating the lexical munging.
    """
    t = token.strip()
    if t.isdigit():
        return int(t), None
    head, sep, num = t.rpartition("-")
    if sep and num.isdigit():
        return int(num), head.upper()
    raise SquadsError(
        f"invalid item id {token!r} (use a bare number or a full ID like TYPE-NNNNNN)"
    )


async def resolve_item_id_typed(token: str, item_type: str, svc: Service) -> str:
    """Resolve a CLI token and verify the item's **actual type** in the live DB.

    Accepts ``35`` / ``000035`` / ``PREFIX-000035``.  Raises a friendly
    :class:`SquadsError` on type mismatch (naming the real item and type) or on an
    unknown item (mentioning both accepted forms — full ID and bare number).

    ``item_type`` is a plain string — every type (built-in or custom) resolves the same
    way.  The prefix is resolved from the per-invocation spec (``get_active_spec()``) so
    custom types that declare their own prefix in ``.overrides/workflow.toml`` get the
    correct validation.

    Mirrors :func:`resolve_slug_or_raise` in shape — takes ``svc`` as a second argument.
    One DB read per call.
    """
    # Resolve the prefix from the active spec — the sole vocabulary source.
    from squads._models._vocab import prefix_for
    from squads._workflow import dropped_via_selected

    spec = get_active_spec()
    if item_type not in spec.items and dropped_via_selected(item_type, spec):
        # `prefix_for`'s own "declare it or check for a typo" message is accurate for a type
        # that was never bundled or declared, but false for one an adopter's own override
        # dropped — this is the read-path counterpart of the create-path membership gate in
        # `_services/_base.py`, which the CLI's own dispatch already lets reach this message
        # for the analogous case (`sq create <type>`).
        raise SquadsError(
            f"unknown item type {item_type!r}: {item_type!r} was dropped from a "
            "[selected] list (selected.items) in .overrides/workflow.toml, not left "
            "undeclared — add it back to selected.items to restore it"
        )
    prefix = prefix_for(item_type, spec)
    t = token.strip()
    seq, given_prefix = _parse_item_token(token)
    if given_prefix is not None and given_prefix != prefix:
        # Full ID with wrong prefix — look up the actual item so we can name it.
        db = await svc.store.load()
        item = db.get(str(seq))
        if item is None:
            hint = format_item_id(prefix, seq, DISPLAY_ID_PADDING)  # display width
            raise SquadsError(f"no item with number {seq} (use {hint} or bare {seq})")
        raise SquadsError(_mismatch_msg(token, item.id, item.type, item_type))

    db = await svc.store.load()
    item = db.get(str(seq))
    if item is None:
        hint = format_item_id(prefix, seq, DISPLAY_ID_PADDING)  # display, not filename
        raise SquadsError(f"no item with number {seq} (use {hint} or bare {seq})")
    if item.type != item_type:
        raise SquadsError(_mismatch_msg(t, item.id, item.type, item_type))
    return item.id


async def resolve_item_id_any(token: str, svc: Service) -> str:
    """Resolve a CLI token to the full ID of **whatever item owns that sequence number**.

    Accepts a bare number (``35`` / ``000035``) or a full ID (``PREFIX-000035``).  The type
    word in a full ID is validated against the item that actually owns the number; a
    mismatched prefix raises a :class:`SquadsError`.  Unknown items mention both accepted
    forms in the error.

    Used by type-less surfaces (``sq tree``, ``--parent``, ``ref add`` targets, …) where the
    command has no intrinsic item type.  One DB read per call.
    """
    seq, given_prefix = _parse_item_token(token)
    db = await svc.store.load()
    item = db.get(str(seq))

    if item is None:
        hint = format_item_id("TYPE", seq, DISPLAY_ID_PADDING)  # display width
        raise SquadsError(f"no item with number {seq} (use a full ID like {hint} or bare {seq})")

    if given_prefix is not None:
        expected_prefix = effective_prefix(item.prefix)
        if given_prefix != expected_prefix:
            raise SquadsError(f"{token} is {item.id} ({item.type})")

    return item.id


def is_full_id_shape(token: str) -> bool:
    """Return True when *token* looks like a full item ID (``TYPE-NNNNNN``)."""
    _, sep, tail = token.rpartition("-")
    return bool(sep) and tail.isdigit()


async def resolve_agent_addr(token: str, item_type: str, svc: Service) -> str:
    """Resolve a CLI address token for role/skill/operator to a full item ID.

    Resolution order (exact match only — no fuzzy):
    1. Full-ID shape (``ROLE-000001``) → ``resolve_item_id_typed``
    2. Bare number (``"1"``) → ``resolve_item_id_typed``
    3. Exact slug match via the service's per-type slug lookup

    Raises :class:`SquadsError` with a descriptive message when nothing matches.
    """
    t = token.strip()
    # Paths 1 and 2: numeric or full-ID token — let the typed resolver handle it.
    if t.isdigit() or is_full_id_shape(t):
        return await resolve_item_id_typed(token, item_type, svc)
    # Path 3: treat as a slug — delegate to the service's authoritative slug lookup.
    item = await svc.roster_item(item_type, t)
    if item is not None:
        return item.id
    raise SquadsError(f"no {item_type} with slug, ID, or number {token!r}")


class AddressDispatchGroup(typer.core.TyperGroup):
    """A TyperGroup that routes unknown command tokens to a hidden ``_addr`` subgroup.

    Named commands (e.g. ``catalog``, ``activate``, ``add``) dispatch normally.
    Any other token is treated as an item address (slug / full-ID / bare number)
    and routed to ``_addr`` with the full original args list so the subgroup's
    callback can consume the address token as its ``ADDR`` positional argument.

    Used by ``role_app``, ``skill_app``, and ``operator_app`` to provide the
    ``sq role <addr> show|regen|rm`` surface alongside group-level verbs.

    Set ``_ADDR_VERBS`` to the pipe-separated verb list used in missing-verb error messages.

    Note: a role/skill/operator slugged exactly like a named group verb (``add``,
    ``catalog``, ``activate``) is unaddressable by slug — the named verb wins in
    ``get_command`` before ``_addr`` is tried.  Number/full-ID always work as the
    escape hatch.
    """

    _ADDR_VERBS: ClassVar[str] = "show|regen|rm|status"

    def _click_resolve_command(self, ctx: Any, args: list[str]) -> Any:  # type: ignore[override]
        cmd_name = args[0]

        # Try named commands first (catalog / activate / add / _addr itself).
        cmd = self.get_command(ctx, cmd_name)
        if cmd is not None:
            return cmd_name, cmd, args[1:]

        # Unknown token — treat as an item address and route to _addr.
        addr_cmd = self.get_command(ctx, "_addr")
        if addr_cmd is not None and not ctx.resilient_parsing:
            # If no verb follows the address token, give a helpful error immediately
            # rather than falling through to _addr's "Missing command" usage error.
            remaining = args[1:]
            has_verb = any(a for a in remaining if not a.startswith("-"))
            if not has_verb and "--help" not in remaining:
                err_console.print(
                    f"[red]error:[/red] missing verb after address {cmd_name!r}. "
                    f"Usage: sq {ctx.info_name} <slug|id|n> {self._ADDR_VERBS}",
                    soft_wrap=True,
                )
                raise typer.Exit(1)
            # Use a readable display name instead of "_addr" so help/error output shows
            # "sq role <slug|id|n>" rather than "sq role _addr".
            return "<slug|id|n>", addr_cmd, args
        return super()._click_resolve_command(ctx, args)


def spec_aware_command_cls(
    refresh_help: Callable[[list[Any]], None],
) -> type[typer.core.TyperCommand]:
    """Build a one-off ``TyperCommand`` subclass whose ``--help`` re-derives specific
    parameters' help text from the *live* per-invocation spec at render time, instead of
    whatever spec was active when the command object was constructed.

    Statically-registered built-in commands (``sq <type> update``, ``sq <type> retype``,
    the per-type ``sq create <type>``) are built once, at import time — before any squad
    or override is known — so a plain ``help=`` string computed then is permanently the
    bundled spec's answer (e.g. ``--priority``'s enumerated codes, retype's target list).
    Click always renders ``--help`` through ``get_params(ctx)``, which fires only once the
    root callback has already bound the per-invocation spec (the group-callback chain
    resolves — and so runs ``main_callback`` — before the leaf command's own ``--help``
    short-circuits), so refreshing there — and only there — makes a statically-registered
    command's help as spec-aware as the lazily-built custom-type equivalent, without moving
    *when* or *from which spec* it's registered. A non-customized squad resolves the same
    (bundled) spec at render time as at import time, so output stays byte-identical.

    *refresh_help* receives the command's already-resolved parameter list and mutates the
    ``.help`` of whichever ones it recognizes (by ``.name``) in place.

    **The refresh is fail-soft, and it has to be.** ``get_params`` runs during Click's own
    parameter resolution — before the command body, and therefore outside the ``@handle_errors``
    / ``@command`` boundary that turns a ``SquadsError`` into a clean message. A refresh that
    raised there escaped as a traceback, which is the one thing the refusal contract rules out;
    it surfaced the moment ``get_active_spec`` started refusing on an unresolvable override,
    because ``sq create <type>``'s ``--priority`` help reads the active spec. Help text is
    presentation, not an answer about the squad: when the spec cannot be resolved the baked
    text simply stands, and the real refusal fires from the command body a moment later, once
    there is somewhere to report it. Same division as :func:`resolve_spec_for_ctx` — the parser
    degrades, the answering surfaces refuse.
    """

    class _SpecAwareCommand(typer.core.TyperCommand):
        def get_params(self, ctx: Any) -> list[Any]:
            params = super().get_params(ctx)
            # see the docstring: presentation degrades, it never raises out of parse
            with contextlib.suppress(Exception):
                refresh_help(params)
            return params

    return _SpecAwareCommand


def register_status_verb(
    addr_app: typer.Typer, id_from_ctx: Callable[[typer.Context], str]
) -> None:
    """Register a ``status`` verb on an addressed roster subgroup (``role``/``skill``/``operator``).

    Mirrors ``_cmd_status`` in ``_cli/_items.py`` verb-for-verb (a ``STATUS`` positional,
    ``--force``, the ``{id} → {status}`` confirmation line) but is shared across the three
    roster modules instead of copied, since it needs no work-item-only machinery — it drives
    ``Service.set_roster_status`` instead of the generic ``Service.set_status``, the roster
    entry point that also reports what ``--unlink`` severed.

    ``--unlink`` is offered here and nowhere else: only a roster-category type carries the
    config-integrity clauses (``_services/_retirement.py``) it satisfies, and every caller of
    this helper is already one of the three roster types.

    ``id_from_ctx`` extracts the resolved item id from ``ctx.obj`` using the caller's own
    convention: role's ``_require_id`` (raises the "activate it first" error for a
    bundled-only slug) vs skill/operator's strict ``ctx.obj["id"]``. This keeps that
    per-module fallback logic out of this shared helper.
    """

    @addr_app.command("status")
    @command
    async def status(  # pyright: ignore[reportUnusedFunction] — registered via the decorator above
        ctx: typer.Context,
        new_status: str = typer.Argument(..., metavar="STATUS"),
        force: bool = typer.Option(
            False,
            "--force",
            help=(
                "Override the lifecycle's own disallowed transition edge. Never overrides a "
                "refusal that the resulting config would be invalid."
            ),
        ),
        unlink: bool = typer.Option(
            False,
            "--unlink",
            help=(
                "On a retirement, remove the scoping the refusal named — a custom skill's "
                "link to a role — then re-run the check, rather than overriding it. Refused "
                "on any other transition."
            ),
        ),
    ) -> None:
        """Transition the entity's status (shortcut for the work-item `status` verb)."""
        item_id = id_from_ctx(ctx)
        result = await get_service().set_roster_status(
            item_id, parse_status(new_status), force=force, unlink=unlink
        )
        console.print(f"{result.item.id} → [bold]{result.item.status}[/bold]")
        if unlink:
            if result.severed:
                for sev in result.severed:
                    console.print(f"  severed {e(sev.referrer)} → {e(sev.target)} ({sev.kind})")
            else:
                console.print("  --unlink: no references severed (nothing was severable)")
        for warning in result.warnings:
            console.print(f"[yellow]warning:[/yellow] {e(warning)}", soft_wrap=True)


def resolve_local_id(token: str, kind: str) -> str:
    """A CLI sub-entity token → canonical local id: ``2`` → ``STn``/``USn``/``Fn``."""
    return discussion.local_id_for(kind, token, get_active_spec())


def require_as(as_: str | None) -> str:
    """Validate ``--as`` was supplied and return it.

    ``--as`` has no default: attribution is only knowable at the moment the command is
    typed, so a missing flag must fail loudly rather than silently recording the
    comment/notice in the operator's voice.
    """
    if not as_:
        raise SquadsError("--as is required: the actor's slug")
    return as_


async def resolve_slug_or_raise(slug: str, svc: Service, *, live_only: bool = True) -> str:
    """Validate ``slug`` against the roster (agents + operators) and return it normalised.

    Mirrors :func:`resolve_item_id` in shape: one validation idiom for slugs, one for item IDs.
    Raises :class:`SquadsError` (exit 1) naming valid slugs when the slug is unknown.
    ``"operator"`` is the legacy anonymous sentinel — it is not validated (kept for compat).

    ``live_only`` (default ``True``) is what makes a retired entry stop being **live**
    while its history stays intact: the interactive entry points that *write* a
    participant — ``--as``/``--author``/``--assignee`` on create/comment/update — accept only
    a live slug, which this default gives them for free by reading ``svc.roster()`` /
    ``svc.operators()`` (already live-only). Pass ``live_only=False`` for a caller that
    *reads* or *filters* by a participant slug rather than attributing new authorship to one —
    ``--assignee`` on `sq list`/`sq tree`, `sq mine`, `sq inbox` — since a retired role's
    already-assigned items and past @mentions must stay reachable; those read
    ``svc.roster_all()``/``svc.operators_all()`` instead.

    A slug that is well known but merely retired reads as retired, not unknown: when
    ``live_only`` rejects it, a second lookup against the full roster names the entry and the
    one command that undoes it, rather than sending the operator after a typo or a missing
    activation (see :func:`_retired_participant_hint`).
    """
    normalised = slug.lstrip("@").lower()
    if normalised == "operator":
        return normalised
    if live_only:
        agent_slugs = [r.slug for r in await svc.roster()]
        operator_slugs = [o.slug for o in await svc.operators()]
        if normalised in agent_slugs or normalised in operator_slugs:
            return normalised
        retired = await _retired_participant_hint(svc, normalised)
        if retired is not None:
            raise SquadsError(retired)
    else:
        agent_slugs = [r.slug for r in await svc.roster_all()]
        operator_slugs = [o.slug for o in await svc.operators_all()]
        if normalised in agent_slugs or normalised in operator_slugs:
            return normalised
    valid = sorted(agent_slugs + operator_slugs)
    hint = ", ".join(valid) if valid else "(none registered — run `sq init` or `sq operator add`)"
    raise SquadsError(f"unknown slug {slug!r}; valid slugs: {hint}")


async def _retired_participant_hint(svc: Service, slug: str) -> str | None:
    """``slug``'s retired-but-known message for :func:`resolve_slug_or_raise`, or ``None`` when
    *slug* is not in the full roster either (genuinely unknown).

    Looks the slug up against the full (not live-only) roster/operator vocabulary — the one
    extra call ``live_only`` skips when the slug already resolved — and names the entry plus
    the reactivating command rather than leaving the operator to guess it.
    """
    role = await svc.roster_item(ROSTER_ROLE, slug)
    if role is not None:
        target = svc.spec.live_initial(ROSTER_ROLE)
        return (
            f"{slug!r} ({role.id}) is retired; reactivate it with `sq role {slug} status {target}`"
        )
    op = await svc.roster_item(ROSTER_OPERATOR, slug)
    if op is not None:
        target = svc.spec.live_initial(ROSTER_OPERATOR)
        return (
            f"{slug!r} ({op.id}) is retired; reactivate it with `sq operator {slug} status "
            f"{target}`"
        )
    return None


def parse_type(value: str) -> str:
    """Validate *value* is a known item type and return it as a plain string.

    Reads the per-invocation WorkflowSpec (bound by the root callback); falls back to the
    bundled spec when called before the callback fires or outside a squad.
    """
    _spec = get_active_spec()
    if value in _spec.items:
        return value
    choices = ", ".join(sorted(_spec.items))
    raise SquadsError(f"unknown type {value!r} (one of: {choices})") from None


def parse_status(value: str) -> str:
    """Validate *value* is a known status and return it as a plain string.

    Accepts either the canonical value ("InProgress") or a loose form ("in_progress",
    "inprogress").  Reads the per-invocation WorkflowSpec (bound by the root callback);
    falls back to the bundled spec when called before the callback fires or outside a squad.
    """
    _spec = get_active_spec()
    # Exact match first (fast path).
    if value in _spec.statuses:
        return value
    # Loose match: strip separators, lower-case compare.
    norm = value.replace("_", "").replace("-", "").lower()
    for s in _spec.statuses:
        if s.lower() == norm:
            return s
    choices = ", ".join(sorted(_spec.statuses))
    raise SquadsError(f"unknown status {value!r} (one of: {choices})") from None


def parse_category(value: str) -> str:
    """Validate *value* against the fixed roster/work/records category catalog.

    The category axis is a closed, code-level catalog (``squads._workflow.CATEGORIES``) —
    not spec vocabulary — so this validates against that constant, never the active spec's
    declared types.
    """
    normalised = value.strip().lower()
    if normalised in CATEGORIES:
        return normalised
    choices = ", ".join(CATEGORIES)
    raise SquadsError(f"unknown category {value!r} (one of: {choices})") from None


def parse_badge_code(collection_code: str, value: str, spec: WorkflowSpec | None = None) -> str:
    """Validate/normalize *value* against the named collection's badge codes.

    The one generic value-parser for every flat badge axis (priority/severity/a project's
    own custom axis) — replaces the former hand-written pair of per-axis parsers.
    ``collection_code`` is usually a field's own ``.collection`` (resolved via
    :func:`squads._badges.resolve_collection` at the call site).
    """
    active_spec = spec if spec is not None else get_active_spec()
    coll = active_spec.collections.get(collection_code)
    code = value.strip().lower()
    if coll is None or code not in coll.badge_codes:
        choices = ", ".join(b.code for b in coll.badges) if coll else ""
        raise SquadsError(f"unknown {collection_code} {value!r} (one of: {choices})")
    return code


def parse_filter_badge_code(field_code: str, value: str, spec: WorkflowSpec | None = None) -> str:
    """Validate/normalize a **cross-type filter** value for badge field *field_code*.

    ``sq list``/``sq tree`` filter over every type at once, so there is no single bound
    collection to validate against — accept any code declared by *any* type's binding of
    the field (:func:`squads._badges.field_badge_codes`) and let ``ItemFilter`` do the
    per-item, per-type match. Validating against the collection literally *named*
    ``priority`` instead made the filter unusable for a squad that binds task's priority to a
    ``tshirt`` collection: ``--priority m`` was refused outright.

    For the bundled spec the union is exactly the ``priority`` collection, so the accepted
    values and the refusal text are unchanged.
    """
    active_spec = spec if spec is not None else get_active_spec()
    codes = badges.field_badge_codes(field_code, active_spec)
    code = value.strip().lower()
    if code not in codes:
        raise SquadsError(f"unknown {field_code} {value!r} (one of: {', '.join(codes)})")
    return code
