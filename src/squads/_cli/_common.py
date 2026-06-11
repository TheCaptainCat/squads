"""Shared CLI helpers: console, error handling, service resolution, value parsing."""

import functools
import json
import sys
from collections.abc import Callable
from pathlib import Path

import typer
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel

from squads import __version__, _clock
from squads import _discussion as discussion
from squads._errors import SquadsError
from squads._models._enums import (
    PREFIX_BY_TYPE,
    PRIORITY_EMOJI,
    SEVERITY_EMOJI,
    ItemType,
    Priority,
    Severity,
    Status,
)
from squads._models._extras import ExtraKey as X
from squads._models._item import Item, split_ref
from squads._models._schema import SCHEMA_VERSION, schema_tuple
from squads._paths import resolve
from squads._services._results import BlockResult, SubentityDetail
from squads._services._service import Service, open_service

console = Console()
err_console = Console(stderr=True)

# The active squad folder from the global --dir option, set once by the root callback.
_active_dir: str | None = None


def set_active_dir(value: str | None) -> None:
    global _active_dir
    _active_dir = value


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
        console.print_json(
            json.dumps(
                {
                    "local_id": res.local_id,
                    "file": str(res.path),
                    "region": res.body_tag,
                    "start_line": res.start_line,
                    "end_line": res.end_line,
                }
            )
        )
        return
    kind = res.body_tag.split(":")[0]  # e.g. "subtask:ST1:body" → "subtask"
    console.print(f"added [bold]{res.local_id}[/bold] to {parent_id}")
    console.print(
        f'  set its body:  [cyan]sq {kind} body {parent_id} {res.local_id} -m "…"[/cyan]'
        "  [dim](or --file body.md / --file -)[/dim]"
    )


def print_item(svc: Service, it: Item) -> None:
    """Render an item's metadata panel + its body (for `sq <type> <num> show`)."""
    rows = [
        f"[bold]{it.id}[/bold]  ({it.type.value})",
        f"[bold]title:[/bold] {e(it.title)}",
        f"[bold]status:[/bold] {it.status.value}",
    ]
    if it.priority:
        rows.append(f"[bold]priority:[/bold] {e(priority_badge(it.priority))}")
    sev = it.extra.get(X.SEVERITY) if it.type is ItemType.BUG else None
    if sev:
        rows.append(f"[bold]severity:[/bold] {e(f'{SEVERITY_EMOJI[Severity(sev)]} {sev}')}")
    if it.description:
        rows.append(f"[bold]summary:[/bold] {e(it.description)}")
    if it.parent:
        rows.append(f"[bold]parent:[/bold] {it.parent}")
    if it.author:
        rows.append(f"[bold]author:[/bold] {e(it.author)}")
    if it.assignee:
        rows.append(f"[bold]assignee:[/bold] {e(it.assignee)}")
    if it.labels:
        rows.append(f"[bold]labels:[/bold] {e(', '.join(it.labels))}")
    if it.refs:
        rendered = ", ".join(
            rid if kind == "related" else f"{rid} ({kind})"
            for rid, kind in (split_ref(r) for r in it.refs)
        )
        rows.append(f"[bold]refs:[/bold] {e(rendered)}")
    rows.append(f"[bold]file:[/bold] {it.path}")
    console.print(Panel("\n".join(rows), expand=False))
    if it.type not in (ItemType.ROLE, ItemType.SKILL):
        body = svc.read_body(it.id)
        console.print()
        console.print(e(body) if body else "[dim](empty — set it with `body`)[/dim]")


def print_subentity(detail: SubentityDetail, kind: str) -> None:
    """Render a sub-entity's meta + body + discussion for `sq <kind> show`."""
    info = detail.info
    console.print(f"[bold]{info.local_id}[/bold] — {e(info.title)}  [dim]({kind})[/dim]")
    meta = [f"status: {e(info.status)}"]
    if info.assignee:
        meta.append(f"assignee: {e(info.assignee)}")
    if info.severity:
        meta.append(f"severity: {e(info.severity)}")
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


def get_service() -> Service:
    return open_service(_active_dir)


def handle_errors[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return fn(*args, **kwargs)
        except SquadsError as exc:
            err_console.print(f"[red]error:[/red] {exc}")
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

    Accepts bare numbers (``"35"``, ``"000035"``) and full IDs (``"TASK-000035"``).
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


def resolve_item_id_typed(token: str, item_type: ItemType, svc: Service) -> str:
    """Resolve a CLI token and verify the item's **actual type** in the live DB.

    Accepts ``35`` / ``000035`` / ``TASK-000035``.  Raises a friendly
    :class:`SquadsError` on type mismatch (naming the real item and type) or on an
    unknown item (mentioning both accepted forms — full ID and bare number).

    Mirrors :func:`resolve_slug_or_raise` in shape — takes ``svc`` as a second argument.
    One DB read per call.
    """
    prefix = PREFIX_BY_TYPE[item_type]
    t = token.strip()
    seq, given_prefix = _parse_item_token(token)
    if given_prefix is not None and given_prefix != prefix:
        # Full ID with wrong prefix — look up the actual item so we can name it.
        db = svc.store.load()
        item = db.get(str(seq))
        if item is None:
            raise SquadsError(f"no item with number {seq} (use {prefix}-{seq:06d} or bare {seq})")
        raise SquadsError(_mismatch_msg(token, item.id, item.type.value, item_type.value))

    db = svc.store.load()
    item = db.get(str(seq))
    if item is None:
        raise SquadsError(f"no item with number {seq} (use {prefix}-{seq:06d} or bare {seq})")
    if item.type is not item_type:
        raise SquadsError(_mismatch_msg(t, item.id, item.type.value, item_type.value))
    return item.id


def resolve_item_id_any(token: str, svc: Service) -> str:
    """Resolve a CLI token to the full ID of **whatever item owns that sequence number**.

    Accepts a bare number (``35`` / ``000035``) or a full ID (``FEAT-000013``).  The type word in a
    full ID is validated against the item that actually owns the number; a mismatched prefix raises
    a :class:`SquadsError`.  Unknown items mention both accepted forms in the error.

    Used by type-less surfaces (``sq tree``, ``--parent``, ``ref add`` targets, …) where the
    command has no intrinsic item type — TASK-000047 wires this in across those surfaces.
    One DB read per call.
    """
    seq, given_prefix = _parse_item_token(token)
    db = svc.store.load()
    item = db.get(str(seq))

    if item is None:
        raise SquadsError(
            f"no item with number {seq} (use a full ID like TYPE-{seq:06d} or bare {seq})"
        )

    if given_prefix is not None:
        expected_prefix = PREFIX_BY_TYPE[item.type]
        if given_prefix != expected_prefix:
            raise SquadsError(f"{token} is {item.id} ({item.type.value})")

    return item.id


def resolve_local_id(token: str, kind: str) -> str:
    """A CLI sub-entity token → canonical local id: ``2`` → ``ST2``/``US2``/``F2``."""
    return discussion.local_id_for(kind, token)


def resolve_slug_or_raise(slug: str, svc: Service) -> str:
    """Validate ``slug`` against the roster (agents + operators) and return it normalised.

    Mirrors :func:`resolve_item_id` in shape: one validation idiom for slugs, one for item IDs.
    Raises :class:`SquadsError` (exit 1) naming valid slugs when the slug is unknown.
    ``"operator"`` is the legacy anonymous sentinel — it is not validated (kept for compat).
    """
    normalised = slug.lstrip("@").lower()
    if normalised == "operator":
        return normalised
    agent_slugs = [r.slug for r in svc.roster()]
    operator_slugs = [o.slug for o in svc.operators()]
    if normalised in agent_slugs or normalised in operator_slugs:
        return normalised
    valid = sorted(agent_slugs + operator_slugs)
    hint = ", ".join(valid) if valid else "(none registered — run `sq init` or `sq operator add`)"
    raise SquadsError(f"unknown slug {slug!r}; valid slugs: {hint}")


def parse_type(value: str) -> ItemType:
    try:
        return ItemType(value)
    except ValueError:
        choices = ", ".join(t.value for t in ItemType)
        raise SquadsError(f"unknown type {value!r} (one of: {choices})") from None


def parse_status(value: str) -> Status:
    # accept either the canonical value ("InProgress") or a loose form ("in_progress", "inprogress")
    norm = value.replace("_", "").replace("-", "").lower()
    for s in Status:
        if s.value.lower() == norm or s.value == value:
            return s
    choices = ", ".join(s.value for s in Status)
    raise SquadsError(f"unknown status {value!r} (one of: {choices})") from None


def parse_severity(value: str) -> Severity:
    try:
        return Severity(value.strip().lower())
    except ValueError:
        choices = ", ".join(s.value for s in Severity)
        raise SquadsError(f"unknown severity {value!r} (one of: {choices})") from None


def parse_priority(value: str) -> Priority:
    try:
        return Priority(value.strip().lower())
    except ValueError:
        choices = ", ".join(p.value for p in Priority)
        raise SquadsError(f"unknown priority {value!r} (one of: {choices})") from None


def priority_badge(priority: Priority) -> str:
    """A colored badge + label for a priority, e.g. ``🟠 high`` (already Rich-safe)."""
    return f"{PRIORITY_EMOJI[priority]} {priority.value}"
