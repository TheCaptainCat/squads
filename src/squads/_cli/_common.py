"""Shared CLI helpers: console, error handling, service resolution, value parsing."""

import functools
import json
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, ClassVar

import anyio
import typer
import typer.core
from rich.console import Console, Group, RenderableType
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel

from squads import __version__, _clock
from squads import _badges as badges
from squads import _discussion as discussion
from squads._errors import SquadsError
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
from squads._workflow import bundled_spec
from squads._workflow._models import WorkflowSpec

console = Console()
err_console = Console(stderr=True)


def print_json_clean(s: str) -> None:
    """Emit JSON to stdout with no ANSI codes, unconditionally.

    Uses plain ``print()`` so FORCE_COLOR / CLICOLOR_FORCE / PY_COLORS have no effect.
    The indent matches Rich's ``print_json`` default (2 spaces).  All ``--json`` output
    must go through this function — never through ``console.print_json()``.
    """
    print(json.dumps(json.loads(s), indent=2))


# The active squad folder from the global --dir option, set once by the root callback.
_active_dir: str | None = None


def set_active_dir(value: str | None) -> None:
    global _active_dir
    _active_dir = value


# The per-invocation WorkflowSpec, resolved once by the root callback after the squad is
# located.  Falls back to the bundled spec when no squad can be resolved (e.g. outside a
# squad, or before the callback fires for parse-time validators).
_active_spec: WorkflowSpec | None = None


def set_active_spec(spec: WorkflowSpec | None) -> None:
    global _active_spec
    _active_spec = spec


def get_active_spec() -> WorkflowSpec:
    """Return the per-invocation spec, or the bundled spec if none has been bound yet."""
    return _active_spec if _active_spec is not None else bundled_spec()


def apply_timestamp(at: str | None) -> None:
    """Honour the global ``--at`` option: forge `clock.now()` for this invocation (or clear it)."""
    if at is None:
        _clock.set_now(None)
        return
    try:
        _clock.set_now(_clock.parse_iso(at))
    except ValueError:
        err_console.print(
            f"[red]error:[/red] invalid --at timestamp {at!r} "
            "(use ISO 8601, e.g. 2024-01-15 or 2024-01-15T09:30:00Z)"
        )
        raise typer.Exit(2) from None


def e(value: object) -> str:
    """Escape a dynamic string so Rich does not interpret ``[...]`` as markup."""
    return escape(str(value))


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
        "  [dim](or --file body.md / --file -)[/dim]"
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


async def build_item_json(svc: Service, it: Item) -> str:
    """The ``show --json`` payload: frontmatter fields plus body/discussion — additive only.

    Adds top-level ``body`` (raw body markdown), ``discussion`` (ordered ``{author, ts,
    body}`` list), and ``badges`` (the generic per-item badge map, keyed by field
    code — see :func:`squads._badges.resolve_badges`); plus a ``body`` and ``badges`` key on
    each ``subentities`` entry (a sub-entity carries fields too, e.g. severity on a finding).
    Added unconditionally — not gated by ``--comments``/``--full`` — so the existing
    invariant that ``show --json`` is byte-identical across ``--raw``/``--comments``/
    ``--full`` still holds. Nothing existing is renamed or removed.
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
        for sub_data, sub in zip(payload["subentities"], it.subentities, strict=True):
            detail = await svc.get_block(it.id, kind, sub_data["local_id"])
            sub_data["body"] = detail.body
            sub_data["badges"] = badges.resolve_badges(spec, kind, sub.badge_value)
    return json.dumps(payload)


def get_service() -> Service:
    return open_service(_active_dir)


def handle_errors[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return fn(*args, **kwargs)
        except SquadsError as exc:
            err_console.print(f"[red]error:[/red] {e(exc)}")
            raise typer.Exit(1) from exc

    return wrapper


def command[**P](fn: Callable[P, Awaitable[None]]) -> Callable[P, None]:
    """The single sync→async bridge for CLI commands.

    Wraps an ``async def`` Typer command so Typer sees a sync callable, there is exactly one
    ``anyio.run`` per invocation, and ``SquadsError`` becomes a clean message + ``typer.Exit(1)``
    (subsuming the old ``@handle_errors``).
    """

    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
        try:
            anyio.run(functools.partial(fn, *args, **kwargs))
        except SquadsError as exc:
            err_console.print(f"[red]error:[/red] {e(exc)}")
            raise typer.Exit(1) from exc

    return wrapper


def version_tuple(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for p in version.split("."):
        num = "".join(c for c in p if c.isdigit())
        parts.append(int(num) if num else 0)
    return tuple(parts)


def version_notice() -> None:
    """Print a non-fatal notice if the installed squads is newer than the managed files."""
    try:
        sp = resolve(_active_dir)
    except SquadsError:
        return  # not initialized yet (e.g. before `sq init`)
    recorded = sp.config.squads_version
    if recorded and version_tuple(__version__) > version_tuple(recorded):
        err_console.print(
            f"[yellow]squads {__version__} detected (managed files at {recorded}). "
            f"Run `sq sync` to refresh them.[/yellow]"
        )


def require_current_schema(subcommand: str | None) -> None:
    """Hard-stop when the squad's on-disk schema mismatches this build — except for migrate/help.

    Behind → tell the user to run ``sq migrate``; ahead → tell them to upgrade the package.
    """
    if subcommand in (None, "migrate") or "--help" in sys.argv or "-h" in sys.argv:
        return
    try:
        sp = resolve(_active_dir)
    except SquadsError:
        return  # not initialized yet — nothing to gate
    disk = sp.config.schema_version
    if disk == SCHEMA_VERSION:
        return
    if schema_tuple(disk) < schema_tuple(SCHEMA_VERSION):
        err_console.print(
            f"[red]error:[/red] this squad is at schema v{disk}; squads {__version__} "
            f"expects v{SCHEMA_VERSION}. Run [bold]sq migrate up[/bold] to upgrade it "
            "(see `sq migrate help`)."
        )
    else:
        err_console.print(
            f"[red]error:[/red] this squad is at schema v{disk}, newer than squads "
            f"{__version__} (v{SCHEMA_VERSION}). Upgrade the squads package."
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

    spec = get_active_spec()
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


def _is_full_id_shape(token: str) -> bool:
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
    if t.isdigit() or _is_full_id_shape(t):
        return await resolve_item_id_typed(token, item_type, svc)
    # Path 3: treat as a slug — delegate to the service's authoritative slug lookup.
    _SLUG_LOOKUP = {
        "role": svc._role_item,  # pyright: ignore[reportPrivateUsage]
        "skill": svc._skill_item,  # pyright: ignore[reportPrivateUsage]
        "operator": svc._operator_item,  # pyright: ignore[reportPrivateUsage]
    }
    lookup = _SLUG_LOOKUP.get(item_type)
    if lookup is not None:
        item = await lookup(t)
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

    _ADDR_VERBS: ClassVar[str] = "show|regen|rm"

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
                    f"Usage: sq {ctx.info_name} <slug|id|n> {self._ADDR_VERBS}"
                )
                raise typer.Exit(1)
            # Use a readable display name instead of "_addr" so help/error output shows
            # "sq role <slug|id|n>" rather than "sq role _addr".
            return "<slug|id|n>", addr_cmd, args
        return super()._click_resolve_command(ctx, args)


def resolve_local_id(token: str, kind: str) -> str:
    """A CLI sub-entity token → canonical local id: ``2`` → ``STn``/``USn``/``Fn``."""
    return discussion.local_id_for(kind, token, get_active_spec())


async def resolve_slug_or_raise(slug: str, svc: Service) -> str:
    """Validate ``slug`` against the roster (agents + operators) and return it normalised.

    Mirrors :func:`resolve_item_id` in shape: one validation idiom for slugs, one for item IDs.
    Raises :class:`SquadsError` (exit 1) naming valid slugs when the slug is unknown.
    ``"operator"`` is the legacy anonymous sentinel — it is not validated (kept for compat).
    """
    normalised = slug.lstrip("@").lower()
    if normalised == "operator":
        return normalised
    agent_slugs = [r.slug for r in await svc.roster()]
    operator_slugs = [o.slug for o in await svc.operators()]
    if normalised in agent_slugs or normalised in operator_slugs:
        return normalised
    valid = sorted(agent_slugs + operator_slugs)
    hint = ", ".join(valid) if valid else "(none registered — run `sq init` or `sq operator add`)"
    raise SquadsError(f"unknown slug {slug!r}; valid slugs: {hint}")


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
