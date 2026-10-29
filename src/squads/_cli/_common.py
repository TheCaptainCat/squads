"""Shared CLI helpers: console, error handling, service resolution, value parsing."""

import contextlib
import copy
import functools
import io
import json
import os
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Any, cast

import typer
import typer._click as _click  # underscore is upstream's own private module path, not ours
import typer._click.globals as _click_globals  # ditto — upstream's, not ours
import typer.core
import typer.main
from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from squads import _actor as actor
from squads import _badges as badges
from squads import _discussion as discussion
from squads._api import _ops as ops
from squads._api._api import Operation
from squads._api._dto._comment_writes import (
    CommentAdded,
    CommentAddRequest,
    CommentEdited,
    CommentEditRequest,
    CommentRequest,
    CommentSelection,
    CommentShown,
    RosterCommentAddRequest,
    RosterCommentEditRequest,
    RosterCommentRequest,
)
from squads._api._dto._comments import Comments, CommentsRequest
from squads._api._dto._roster import RosterAddress
from squads._cli._markup import escape_markup
from squads._cli._render import _comments as comment_render
from squads._cli._render import _writes as write_render
from squads._cli._render._style import intent_style
from squads._context import get_context
from squads._errors import (
    NotInitializedError,
    SquadsError,
)
from squads._models._item import (
    DISPLAY_ID_PADDING,
    format_item_id,
    parse_item_token,
)
from squads._models._omission import Omission
from squads._models._participants import refuse_system_actor
from squads._paths import process_dir, resolve
from squads._spec_documents import SpecSources, spec_sources
from squads._specload import override_present
from squads._util import article
from squads._workflow import CATEGORIES, bundled_spec
from squads._workflow._models import WorkflowSpec


def build_consoles() -> tuple[Console, Console]:
    """The stdout and stderr consoles of one invocation."""
    return Console(), Console(stderr=True)


class _ConsoleHandle:
    """A name for one of the invocation's consoles: every use resolves to the console the current
    invocation built, or to a fresh one when none is bound, so no console outlives its command."""

    __slots__ = ("_stderr",)

    def __init__(self, *, stderr: bool) -> None:
        self._stderr = stderr

    def __getattr__(self, name: str) -> Any:
        ctx = get_context()
        if ctx.consoles is not None:
            target = ctx.consoles[1 if self._stderr else 0]
        else:
            target = Console(stderr=self._stderr)
        return getattr(target, name)


console = cast(Console, _ConsoleHandle(stderr=False))
err_console = cast(Console, _ConsoleHandle(stderr=True))


def print_json_clean(s: str) -> None:
    """Emit JSON to stdout with no ANSI codes, unconditionally.

    Uses plain ``print()`` so FORCE_COLOR / CLICOLOR_FORCE / PY_COLORS have no effect.
    The indent matches Rich's ``print_json`` default (2 spaces).  All ``--json`` output
    must go through this function — never through ``console.print_json()``.
    """
    print(json.dumps(json.loads(s), indent=2))


def report_omissions(omissions: list[Omission], *, json_out: bool) -> None:
    """The shared tail of every partial-read command: name what the read left out, then exit ``4``.

    Used by ``inbox``, ``search``, ``board list``, ``memory list`` and ``memory search`` after
    their own results are printed; a no-op when *omissions* is empty. Human mode prints one
    ``error: <message>`` line per omission on stderr. ``--json`` mode instead prints one compact
    line of stderr holding ``{"omitted": [{"code", "source", "message"}, ...]}`` via plain
    ``print()`` (no ANSI), so a consumer can find it as the one stderr line that parses as a JSON
    object; it replaces the prose rather than accompanying it. Exit ``4`` means the command did
    what was asked and stdout is a valid payload with entries missing; ``1``/``2``/``3`` raise
    before this point and outrank it.
    """
    if not omissions:
        return
    if json_out:
        payload = {
            "omitted": [
                {"code": o.code, "source": o.source, "message": o.message} for o in omissions
            ]
        }
        print(json.dumps(payload, separators=(",", ":")), file=sys.stderr)
    else:
        for o in omissions:
            err_console.print(f"[red]error[/red]: {e(o.message)}", soft_wrap=True)
    raise typer.Exit(4)


# The per-invocation WorkflowSpec and client working directory are ambient RequestContext
# fields (squads._context), set once per invocation by the root callback's single
# bind_context(RequestContext(...)) call.


#: The root command's parameter name for ``-C``, read from the parsed params before the root
#: callback runs.
CHANGE_DIR_PARAM = "change_dir"

_ROOT_CALLBACK_RAN_KEY = "squads.root_callback_ran"


class ChangeDirError(Exception):
    """A ``-C`` value that ``chdir`` would refuse; the message names the path and the reason."""


def _enter(path: Path, part: str) -> Path:
    """Step from *path* into *part* the way ``chdir`` does, one component at a time."""
    if part == "..":
        return path.parent
    candidate = path / part
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError:
        raise ChangeDirError(f"{candidate} does not exist") from None
    except OSError as exc:
        reason = "permission denied" if isinstance(exc, PermissionError) else exc.strerror
        raise ChangeDirError(f"{candidate} cannot be entered: {reason}") from None
    if not resolved.is_dir():
        raise ChangeDirError(f"{candidate} is not a directory")
    if not os.access(resolved, os.X_OK):
        raise ChangeDirError(f"{candidate} cannot be entered: permission denied")
    return resolved


def effective_dir(values: Sequence[str]) -> Path:
    """The directory ``-C`` selects: the process directory, then each value entered in order
    as ``chdir`` would (an absolute value replaces what came before, an empty one changes
    nothing, a link is followed before a ``..``). Raises :class:`ChangeDirError` for a
    component that is missing, not a directory, or not searchable. A request that carries its
    own starting directory begins there instead of at the process directory."""
    start = get_context().start_dir
    path = (start if start is not None else process_dir()).resolve()
    for value in values:
        pure = PurePath(value)
        parts = pure.parts
        if pure.is_absolute():
            path, parts = Path(pure.anchor), parts[1:]
        for part in parts:
            if part != ".":
                path = _enter(path, part)
    return path


def root_effective_dir(ctx: Any) -> Path:
    """The effective directory for the invocation *ctx* belongs to, from the root command's
    parsed ``-C`` values — usable before the root callback has bound a context."""
    root = ctx.find_root() if ctx is not None and hasattr(ctx, "find_root") else None
    values = root.params.get(CHANGE_DIR_PARAM) if root is not None else None
    return effective_dir(values or [])


def check_change_dir(ctx: typer.Context, values: list[str] | None) -> list[str]:
    """Option callback for ``-C``: refuse, with exit 2, a directory ``chdir`` would refuse.
    Silent while the shell is completing, which must not write to the terminal."""
    if ctx.resilient_parsing:
        return values or []
    try:
        effective_dir(values or [])
    except ChangeDirError as exc:
        err_console.print(f"[red]error:[/red] -C {e(exc)}", soft_wrap=True)
        raise typer.Exit(2) from None
    return values or []


def refuse_dir_option(ctx: typer.Context, value: str | None) -> None:
    """Option callback for the removed ``--dir``: refuse naming its replacement, exit 2.
    Silent while the shell is completing."""
    if value is not None and not ctx.resilient_parsing:
        err_console.print(
            "[red]error:[/red] --dir is no longer supported; use -C <path> to run sq as if "
            "started in <path> (the project directory, or any folder inside it)",
            soft_wrap=True,
        )
        raise typer.Exit(2)


def mark_root_callback_ran(ctx: Any) -> None:
    """Record on the Click invocation that the root callback has bound this invocation's
    context, so the ambient context is known not to be a previous invocation's."""
    ctx.meta[_ROOT_CALLBACK_RAN_KEY] = True


def _root_callback_ran(ctx: Any) -> bool:
    return bool(ctx.meta.get(_ROOT_CALLBACK_RAN_KEY)) if hasattr(ctx, "meta") else False


def error_text(exc: SquadsError) -> str:
    """The message for *exc*, naming the searched directory when ``-C`` chose it."""
    if isinstance(exc, NotInitializedError):
        return exc.describe(named=get_context().client_cwd_chosen)
    return str(exc)


def get_active_spec() -> WorkflowSpec:
    """Return the per-invocation spec, or the bundled spec if none has been bound yet.

    Raises ``SquadsError`` when the squad has a workflow override that failed to resolve
    (``RequestContext.spec_error``): the bundled spec would describe vocabulary the project did not
    declare, indistinguishably from a correct answer. Every read surface refuses with the text
    ``compose_service`` raises (``_workflow._loader.spec_refusal``). ``sq workflow lint`` never
    calls this, so the diagnostic stays reachable; ``sq check`` and ``sq repair`` take the refusal
    from ``compose_service`` and report it as a finding.
    """
    ctx = get_context()
    if ctx.spec_error is not None:
        raise SquadsError(ctx.spec_error)
    active = ctx.active_spec
    return active if active is not None else bundled_spec()


class SpecKeyedCache[T]:
    """One value per name, each valid only for the spec object it was built from: asking with
    another spec misses, so a command built from one squad's spec never answers for another."""

    def __init__(self) -> None:
        self._entries: dict[str, tuple[WorkflowSpec, T]] = {}

    def get(self, name: str, spec: WorkflowSpec) -> T | None:
        entry = self._entries.get(name)
        return entry[1] if entry is not None and entry[0] is spec else None

    def put(self, name: str, spec: WorkflowSpec, value: T) -> T:
        self._entries[name] = (spec, value)
        return value

    def clear(self) -> None:
        self._entries.clear()


#: ``click.Context.meta`` key for the spec :func:`resolve_spec_for_ctx` read from disk, so the
#: help and completion path resolves the squad's override once per invocation.
_RESOLVED_SPEC_META_KEY = "squads.resolved_spec_memo"


def resolve_spec_for_ctx(ctx: Any) -> WorkflowSpec:
    """Resolve the spec for a Click context where the root callback may not have run.

    Tries, in order: the already-bound spec (:func:`get_active_spec`); the squad found from the
    root group's own ``-C`` values (``sq --help`` and shell completion walk the tree without
    invoking the callback chain); the bundled spec. The disk read is memoised on the root context.

    Never raises, even under a broken override: this only shapes help text and the command table,
    and a completion that raised is worse than one listing the built-in set. The refusal belongs
    to the answering surfaces, :func:`get_active_spec` and ``compose_service``.
    """
    try:
        if ctx is None or _root_callback_ran(ctx):
            active = get_context().active_spec
            if active is not None:
                return active
    except Exception:  # pylint: disable=broad-except
        return bundled_spec()
    root = ctx.find_root() if ctx is not None and hasattr(ctx, "find_root") else None
    if root is not None and _RESOLVED_SPEC_META_KEY in root.meta:
        memo: WorkflowSpec = root.meta[_RESOLVED_SPEC_META_KEY]
        return memo
    resolved = _read_spec_from_disk(ctx)
    if root is not None:
        root.meta[_RESOLVED_SPEC_META_KEY] = resolved
    return resolved


def _read_spec_from_disk(ctx: Any) -> WorkflowSpec:
    """The squad's merged spec read from disk, or the bundled spec when it has no override
    or the override does not resolve."""
    try:
        from squads._paths import resolve
        from squads._workflow._loader import (
            WORKFLOW_OVERRIDE_FILENAME,
            load_workflow_spec,
            validate_against_index_fail_closed,
        )

        sp = resolve(client_cwd=root_effective_dir(ctx))
        override_path = sp.squad_dir / WORKFLOW_OVERRIDE_FILENAME
        if not override_present(override_path):
            return bundled_spec()
        merged = load_workflow_spec(squad_dir=sp.squad_dir)
        validate_against_index_fail_closed(merged, sp.squad_dir, bundled=bundled_spec())
    except Exception:  # pylint: disable=broad-except
        # Deliberately the bundled spec, not get_active_spec() — that one refuses under a
        # broken override, and this path must not raise (see resolve_spec_for_ctx).
        return bundled_spec()
    else:
        return merged


def bundled_alias_owner(name: str) -> str | None:
    """The bundled type that declares *name* as an alias, or ``None`` when no bundled type does."""
    return next(
        (t for t, ts in bundled_spec().items.items() if name in ts.aliases),
        None,
    )


def retargeted_type(ctx: Any, cmd_name: str) -> str | None:
    """The type the active spec routes the root token *cmd_name* to when that is not the bundled
    type the root table registers it for (a type name or alias the spec gives to another type),
    else ``None``. Any spec-resolution error returns ``None``."""
    bundled = bundled_spec()
    registered = cmd_name if cmd_name in bundled.items else bundled_alias_owner(cmd_name)
    if registered is None:
        return None
    try:
        spec = resolve_spec_for_ctx(ctx)
    except Exception:  # pylint: disable=broad-except
        return None
    declared = cmd_name if cmd_name in spec.non_roster_types() else spec.alias_to_type.get(cmd_name)
    if declared is None or declared == registered or declared not in spec.non_roster_types():
        return None
    return declared


def stale_static_aliases(spec: WorkflowSpec) -> frozenset[str]:
    """Static type aliases whose owner is still declared but no longer declares them.

    That is a rename. A dropped owner type is excluded: its aliases keep dispatching into the
    membership gate, whose "unknown item type" message names the type rather than the alias typed
    (see ``_dropped_static_names``). Empty for a non-customized squad.
    """
    return frozenset(
        alias
        for owner, owner_bundled in bundled_spec().items.items()
        for alias in owner_bundled.aliases
        if (owner_spec := spec.items.get(owner)) is not None
        and alias not in owner_spec.aliases
        and alias not in spec.alias_to_type
    )


def static_alias_is_stale(ctx: Any, cmd_name: str) -> bool:
    """True when *cmd_name* is a static type alias the resolved spec no longer declares.

    The root table lists every bundled alias, so after an override renames
    ``feature``'s aliases, ``sq feat 9 show`` would still dispatch and exit 0. Unlike a dropped
    type name, a stale alias has no accurate downstream refusal (its type is usually still
    valid), so the caller substitutes :func:`stale_alias_command`. Any spec-resolution error
    returns ``False``.
    """
    if bundled_alias_owner(cmd_name) is None:
        return False
    try:
        spec = resolve_spec_for_ctx(ctx)
    except Exception:  # pylint: disable=broad-except
        return False
    return cmd_name in stale_static_aliases(spec)


def stale_alias_command(ctx: Any, cmd_name: str) -> _click.Command:
    """A one-off Click command that refuses a stale static alias with exit 1, naming the fix.

    Returning ``None`` from ``get_command`` would hand the refusal to Typer's did-you-mean, which is
    built from the raw ``self.commands`` table and would suggest the stale string just typed. The
    command swallows every trailing token and its own ``--help``.
    """
    owner = bundled_alias_owner(cmd_name) or ""
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


def bind_active_spec(client_cwd: Path | None) -> tuple[WorkflowSpec | None, str | None]:
    """Resolve the spec for this invocation, merging the squad's override as ``compose_service``
    does.

    Returns ``(spec, spec_error)`` without binding it; the caller binds it in the per-invocation
    ``RequestContext``.

    - No squad or no override file: ``(bundled spec, None)``, or ``(None, None)`` when
      ``resolve()`` itself failed; both mean "use the bundled spec".
    - An override file that will not load: ``(None, refusal)``, never a fall back to bundled. A
      catalog rendered from a spec the project did not declare is not an honest answer to "what
      types do I have", and a client could not tell it apart from a correct one.

    ``client_cwd`` goes straight to ``resolve()``, so every resolution path shares one base.
    """
    from squads._workflow import bundled_spec
    from squads._workflow._loader import WORKFLOW_OVERRIDE_FILENAME, spec_refusal

    try:
        sp = resolve(client_cwd=client_cwd)
        override_path = sp.squad_dir / WORKFLOW_OVERRIDE_FILENAME
        has_override = override_present(override_path)
    except Exception:  # pylint: disable=broad-except
        # Outside a squad, unreadable config, … — nothing was declared here to honour.
        return None, None
    if not has_override:
        return bundled_spec(), None

    from squads._workflow._loader import validate_against_index_fail_closed

    try:
        merged_spec = invocation_sources(sp.squad_dir).workflow()
        validate_against_index_fail_closed(merged_spec, sp.squad_dir, bundled=bundled_spec())
    except Exception as exc:  # pylint: disable=broad-except
        return None, spec_refusal(override_path, exc)
    else:
        return merged_spec, None


def _pending_spec_error(ctx: Any) -> str | None:
    """The workflow-override refusal in force for this invocation, or ``None``.

    Reads the bound ``RequestContext`` first; below the root group the root callback has already
    resolved it. At the root group Click resolves a subcommand name before the callback runs, so
    ``sq widget 19 show`` reaches ``get_command`` with nothing bound: the override is then resolved
    through :func:`bind_active_spec` itself, so the refusal text is the one every surface prints. A
    squad with no override, or one that cannot be located, yields ``None``.
    """
    from squads._context import get_context

    bound = get_context()
    if ctx is None or _root_callback_ran(ctx):
        return bound.spec_error  # the callback ran: its verdict is the whole answer
    try:
        _spec, error = bind_active_spec(root_effective_dir(ctx))
    except Exception:  # pylint: disable=broad-except
        return None
    return error


def spec_error_command(cmd_name: str, ctx: Any = None) -> _click.Command | None:
    """A refusal command for a name the parser cannot classify because the override failed to load.

    Returns ``None`` when the spec is fine. A name absent from the command table is checked
    against the bundled spec (the parser must not raise); for a squad whose override declares
    ``widget``, "No such command" would be a wrong claim about that squad's vocabulary. So when
    the override is known to have failed (``RequestContext.spec_error``), the name dispatches
    into the refusal ``sq list`` gives, at the same exit code, not to Click's did-you-mean, which
    would suggest a bundled type. On a healthy squad a typo keeps Click's message. See
    :func:`_pending_spec_error` for how the refusal is found at the root group.
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


# Shared options: each flag that more than one command takes is declared here, with one
# wording per meaning, so a description changes in one place.

PARAGRAPH_HELP = "A paragraph of text; repeat for several."
COMMENT_POINT_HELP = "One point of the comment; repeat for several."
FILE_HELP = "Read the text from a file instead of `-m`; `-` reads stdin."
MOVE_STATUS_HELP = "Status to move to (see `sq workflow lifecycles`)."
AUTHOR_AS_HELP = "Author: a role slug or `op-<slug>` (required)."
COMMENT_AUTHOR_AS_HELP = "The comment's author (required)."
EDIT_AS_HELP = (
    "Attribute the edit in the reflog to this role slug or `op-<slug>`; default `system`."
)
_FORCE_TRANSITION_HELP = "Make a transition the lifecycle does not allow."


def message_option(help: str = PARAGRAPH_HELP) -> Any:
    return typer.Option(None, "-m", "--message", help=help)


#: The two `--file` wordings of the role verbs: a full definition to create a role from, and a
#: field-wise delta to edit one with.
ROLE_DEFINITION_FILE_HELP = (
    "A role definition in the `.overrides/roles/<slug>.toml` grammar; flags win over it. "
    "The `responsibilities` and `agreements` lists are set only here."
)
ROLE_DELTA_FILE_HELP = (
    "A definition delta in the `.overrides/roles/<slug>.toml` grammar, merged field by field. "
    '`responsibilities` and `agreements` are set only here: `["$(*self)", "more"]` appends, '
    "`[]` clears."
)


def file_option(help: str = FILE_HELP, metavar: str | None = None) -> Any:
    return typer.Option(None, "--file", help=help, metavar=metavar)


def append_option() -> Any:
    return typer.Option(False, "--append", help="Append to the body instead of replacing it.")


def replace_body_option() -> Any:
    return typer.Option(
        False, "--force", help="Replace a body already written; what it held is lost."
    )


def force_transition_option(help: str = _FORCE_TRANSITION_HELP) -> Any:
    return typer.Option(False, "--force", help=help)


def raw_option() -> Any:
    return typer.Option(False, "--raw", help="Print plain text instead of rendered markdown.")


def desc_option(default: str | None = "") -> Any:
    return typer.Option(default, "--desc", help="Short summary shown in listings; not the body.")


def author_option(default: Any = ...) -> Any:
    return typer.Option(default, "--author", help="Author: a registered role slug or `op-<slug>`.")


def as_option(help: str = AUTHOR_AS_HELP) -> Any:
    return typer.Option(None, "--as", help=help)


def edit_as_option() -> Any:
    return as_option(EDIT_AS_HELP)


def yes_option() -> Any:
    return typer.Option(False, "--yes", help="Skip the confirmation prompt.")


def closed_option() -> Any:
    return typer.Option(False, "--all", "-a", help="Include closed items.")


def _refuse_negative_depth(value: int | None) -> int | None:
    if value is not None and value < 0:
        raise typer.BadParameter("must be 0 or more")
    return value


def depth_option(default: int | None, *flags: str) -> Any:
    return typer.Option(
        default,
        "--depth",
        *flags,
        callback=_refuse_negative_depth,
        help="How many levels below the root to show; 0 shows only the root.",
    )


def tech_option(default: Any = None) -> Any:
    return typer.Option(default, "--tech", help="Technology, such as `python` or `react`.")


def model_option() -> Any:
    return typer.Option(
        None,
        "--model",
        help="Model the agent runs on, for example `sonnet`, `opus`, `haiku` or `inherit`.",
    )


def pronouns_option() -> Any:
    return typer.Option(
        None, "--pronouns", help="Pronouns, such as they/them; one line, up to 40 characters."
    )


def parent_option() -> Any:
    return typer.Option(None, "--parent", help="Parent item ID or number.")


def label_option() -> Any:
    return typer.Option(None, "--label", help="Label to add (repeatable).")


def assignee_option() -> Any:
    return typer.Option(None, "--assignee", help="Role or operator slug to assign.")


def assignee_filter_option() -> Any:
    return typer.Option(
        None, "--assignee", help="Show only items assigned to this role or operator slug."
    )


def type_filter_option() -> Any:
    return typer.Option(
        None, "--type", "-t", help="Show only items of this type (see `sq workflow types`)."
    )


def status_filter_option() -> Any:
    return typer.Option(
        None,
        "--status",
        "-s",
        help="Show only items in this status, closed or not (see `sq workflow statuses`).",
    )


def move_status_option() -> Any:
    return typer.Option(None, "--status", help=MOVE_STATUS_HELP)


def type_group_help(item_type: str) -> str:
    """The summary of ``sq <type>``, for a bundled or a declared type alike."""
    return f"Operate on {article(item_type)} {item_type} by number or ID."


def e(value: object) -> str:
    """Escape a dynamic string so Rich does not interpret ``[...]`` as markup."""
    return escape_markup(str(value))


def status_style(status: str, spec: WorkflowSpec) -> str:
    """The concrete `rich` style for *status*: its role's colour intent, uncoloured when this
    build does not know the intent."""
    return intent_style(spec.role_for(status).color)


def status_text(status: str, spec: WorkflowSpec) -> Text:
    """A ``Text`` renderable for *status*, coloured by its role's colour intent.

    Applies the style via Rich's ``style=`` parameter rather than interpolating
    ``[colour]...[/]`` markup around the string — the same escaping discipline as :func:`e`,
    so colouring a status never opens a markup-injection path.
    """
    return Text(status, style=status_style(status, spec))


def _is_styled() -> bool:
    """True when Rich will actually render markup (TTY + color enabled)."""
    # Console.is_terminal is False when stdout is piped; NO_COLOR collapses markup too.
    return console.is_terminal and not console.no_color


def _render_comments_plain(
    comments: list[discussion.Comment], shorts: list[str] | None = None
) -> None:
    """Render comments as plain delimited text (piped / NO_COLOR / --raw degradation).

    Uses raw (un-escaped) values because markup=False is in effect — e() escaping must not be
    applied here or it will leak backslashes into the plain output. ``shorts`` are the displayed
    hashes, one per comment (the scope's, when the list is a part of it).
    """
    for cmt, short in zip(comments, shorts or discussion.short_hashes(comments), strict=True):
        label = discussion.author_label(cmt)
        header = f"--- {short} [{cmt.timestamp}] {label}{discussion.edited_suffix(cmt)} ---"
        console.print(header, markup=False, highlight=False)
        console.print(cmt.body, markup=False, highlight=False)
        console.print()


def _render_comments_styled(
    comments: list[discussion.Comment], shorts: list[str] | None = None
) -> None:
    """Render each comment as a Rich Panel (TTY, color enabled, not --raw)."""
    from rich.markdown import Markdown

    for cmt, short in zip(comments, shorts or discussion.short_hashes(comments), strict=True):
        title = (
            f"{e(short)}  {e(cmt.timestamp)}  {e(discussion.author_label(cmt))}"
            f"{e(discussion.edited_suffix(cmt))}"
        )
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


def client_path(file: str) -> Path:
    """*file* as a path: a relative one is taken against the client's working directory."""
    base = get_context().client_cwd
    return base / file if base is not None else Path(file)


def _decode(raw: bytes, encoding: str) -> str:
    """*raw* read through a text stream, so newlines translate as a file read would."""
    return io.TextIOWrapper(io.BytesIO(raw), encoding=encoding).read()


def not_text_refusal(exc: UnicodeDecodeError, file: str, what: str) -> SquadsError:
    """The refusal for a *what* named *file* whose bytes do not decode."""
    return SquadsError(
        f"cannot read {what} {file!r}: not valid {exc.encoding} ({exc.reason} at byte {exc.start})"
    )


def read_client_text(file: str, *, what: str = "file") -> str:
    """The text of *file* as the command line names it: ``-`` is stdin, anything else a path
    under the client's directory, read as UTF-8. Every failure is a :class:`SquadsError` naming
    *file*."""
    try:
        if file == "-":
            return sys.stdin.read()
        return _decode(client_path(file).read_bytes(), "utf-8")
    except UnicodeDecodeError as exc:
        raise not_text_refusal(exc, file, what) from exc
    except OSError as exc:
        raise SquadsError(f"cannot read {what} {file!r}: {exc.strerror or exc}") from exc


def _read_source_file(file: str) -> str:
    """Read --file content: '-' reads stdin, anything else a real path. Shared by every
    content-source resolver (body, comment) so '-' and read errors behave identically."""
    return read_client_text(file).strip("\n")


def resolve_body_optional(messages: list[str] | None, file: str | None) -> str | None:
    """Body from repeatable -m paragraphs or a --file path ('-' = stdin); at most one source."""
    if messages and file:
        raise SquadsError("provide the body via -m or --file, not both")
    if file is not None:
        return _read_source_file(file)
    if messages:
        return "\n\n".join(messages)
    return None


def resolve_body(messages: list[str] | None, file: str | None) -> str:
    body = resolve_body_optional(messages, file)
    if body is None:
        raise SquadsError("provide the body via -m (repeatable) or --file PATH ('-' for stdin)")
    return body


def resolve_comment_messages(messages: list[str] | None, file: str | None) -> list[str]:
    """Comment content from repeatable ``-m`` messages or a ``--file`` path (``-`` is stdin).

    Shares :func:`_read_source_file` and the mutual exclusion with ``resolve_body``, but a file is
    exactly one comment, returned as a single-element list whose continuation lines carry the file
    verbatim, blank lines and code fences included. An empty or whitespace-only file is refused,
    since a comment has no meaningful empty form.
    """
    if messages and file:
        raise SquadsError("provide the comment via -m or --file, not both")
    if file is not None:
        content = _read_source_file(file)
        if not content.strip():
            raise SquadsError("--file must not be empty")
        return [content]
    if messages:
        return messages
    raise SquadsError("provide the comment via -m (repeatable) or --file PATH ('-' for stdin)")


#: ``click.Context.meta`` key for the documents this invocation has read, by squad directory (see
#: :func:`invocation_sources`).
_SPEC_SOURCES_META_KEY = "squads.spec_sources"


def invocation_sources(squad_dir: Path) -> SpecSources:
    """The documents this invocation has read for *squad_dir*: kept on the Click root context so
    the root callback, a service the cross-check refused and its fallback share one read of each
    override. Outside a Click invocation they are fresh."""
    root = _click_root_context()
    if root is None:
        return spec_sources(squad_dir)
    memo: dict[str, SpecSources] = root.meta.setdefault(_SPEC_SOURCES_META_KEY, {})
    key = str(squad_dir)
    if key not in memo:
        memo[key] = spec_sources(squad_dir)
    return memo[key]


def _click_root_context() -> _click.core.Context | None:
    """The current Click invocation's root context, or ``None`` outside of one, as when the
    local API's sources are read by a caller that is not a command."""
    ctx = _click_globals.get_current_context(silent=True)
    return ctx.find_root() if ctx is not None else None


def handle_errors[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return fn(*args, **kwargs)
        except SquadsError as exc:
            print_notices(exc.warnings)
            err_console.print(f"[red]error:[/red] {e(error_text(exc))}", soft_wrap=True)
            raise typer.Exit(1) from exc

    return wrapper


def print_notices(warnings: Sequence[str]) -> None:
    """Each notice on stderr, once per invocation: a response's, or those a refused call carries
    before its error."""
    printed = printed_notices()
    for warning in warnings:
        if warning not in printed:
            printed.add(warning)
            err_console.print(f"[yellow]warning:[/yellow] {e(warning)}", soft_wrap=True)


#: ``click.Context.meta`` key for the notices this invocation has printed (see
#: :func:`printed_notices`).
_PRINTED_NOTICES_META_KEY = "squads.printed_notices"


def printed_notices() -> set[str]:
    """The notices this invocation has printed on stderr, so a response that carries one again
    does not print it twice. Outside a Click invocation the set is fresh."""
    root = _click_root_context()
    if root is None:
        return set()
    printed: set[str] = root.meta.setdefault(_PRINTED_NOTICES_META_KEY, set())
    return printed


def _value_options_of(root: _click.Command) -> frozenset[str]:
    """Every option spelling, across *root* and all its subcommands, that consumes the next
    token."""
    from typer.core import TyperGroup, TyperOption

    names: set[str] = set()
    pending: list[_click.Command] = [root]
    while pending:
        command = pending.pop()
        for param in command.params:
            if isinstance(param, TyperOption) and not param.is_flag and not param.count:
                names.update(param.opts, param.secondary_opts)
        if isinstance(command, TyperGroup):
            pending.extend(command.commands.values())
    return frozenset(names)


@functools.cache
def value_options() -> frozenset[str]:
    """Every option spelling, across the whole static command tree, that consumes the next
    token. The tree is built from the bundled spec and does not vary by squad, so the result
    is computed once per process."""
    import typer.main

    from squads._cli import app

    return _value_options_of(typer.main.get_command(app))


def help_requested(argv: list[str], root: _click.Command | None = None) -> bool:
    """Whether *argv* carries ``--help`` as an option of its own: before any ``--`` and not the
    value of an option that takes one. ``-h`` is not a help option of this CLI. Pass the
    invocation's *root* command to read its value options off the tree Click already built."""
    if "--help" not in argv:
        return False
    values = value_options() if root is None else _value_options_of(root)
    consumed = False
    for token in argv:
        if consumed:
            consumed = False
        elif token == "--":
            return False
        elif token == "--help":
            return True
        else:
            consumed = token in values
    return False


def item_prefix(item_type: str) -> str:
    """The id prefix of *item_type* in the active spec, refused for a type the spec does not
    declare."""
    from squads._models._vocab import prefix_for
    from squads._workflow import dropped_via_selected

    spec = get_active_spec()
    if item_type not in spec.items and dropped_via_selected(item_type, spec):
        # `prefix_for`'s "declare it or check for a typo" message is false for a type the
        # adopter's override dropped; this is the read-path twin of the create-path gate in
        # `_services/_base.py`.
        raise SquadsError(
            f"unknown item type {item_type!r}: {item_type!r} was dropped from a "
            "[selected] list (selected.items) in .overrides/workflow.toml, not left "
            "undeclared — add it back to selected.items to restore it"
        )
    return prefix_for(item_type, spec)


def item_address(token: str, item_type: str) -> dict[str, str]:
    """The address of an item a command names by *token*, parsed but not looked up: its id (the
    number under the token's own prefix, or the type's), the type and the token as typed."""
    prefix = item_prefix(item_type)
    seq, given_prefix = parse_item_token(token)
    item_id = format_item_id(given_prefix or prefix, seq, DISPLAY_ID_PADDING)
    return {"id": item_id, "type": item_type, "address": token}


def parsed_address(ctx: typer.Context, parse: Callable[[], dict[str, str]]) -> dict[str, Any]:
    """An addressed group's ``ctx.obj`` from *parse*; a failure is raised unless help was
    requested for the verb below, when it is deferred to the first read."""
    try:
        return parse()
    except SquadsError as exc:
        if not verb_help_requested(ctx):
            raise
        return UnresolvedAddress(exc)


ADDRESS_METAVAR = "<slug|id|n>"

_HELP_REQUESTED_META_KEY = "squads.help_requested"


class HelpAwareGroup(typer.core.TyperGroup):
    """A group that records whether help was requested on the verb it dispatches to, so an
    address-resolving callback can skip resolution (see :func:`verb_help_requested`)."""

    def resolve_command(self, ctx: Any, args: list[str]) -> Any:  # type: ignore[override]
        ctx.meta[_HELP_REQUESTED_META_KEY] = help_requested(args[1:], ctx.find_root().command)
        return super().resolve_command(ctx, args)


def verb_help_requested(ctx: typer.Context) -> bool:
    """Whether the verb below this group was invoked with ``--help``, which renders without an
    address, so the group's callback must not resolve one."""
    return bool(ctx.meta.get(_HELP_REQUESTED_META_KEY))


class UnresolvedAddress(dict[str, Any]):
    """The ``ctx.obj`` of an addressed group whose address did not resolve while help looked to
    be requested. Help renders without reading it; any other read of a key it lacks raises the
    resolution error, so a call that is not a help request never runs without its address."""

    def __init__(self, error: SquadsError, **items: Any) -> None:
        super().__init__(items)
        self.error = error

    def __missing__(self, key: str) -> Any:
        raise self.error

    def extended(self, **items: Any) -> UnresolvedAddress:
        """A copy carrying *items* as well, with the same deferred error."""
        return UnresolvedAddress(self.error, **{**self, **items})


def extend_obj(obj: dict[str, Any], **items: Any) -> dict[str, Any]:
    """*obj* with *items* added, keeping an :class:`UnresolvedAddress` deferred."""
    if isinstance(obj, UnresolvedAddress):
        return obj.extended(**items)
    return {**obj, **items}


class AddressedGroup(HelpAwareGroup):
    """The group behind ``sq <roster> <slug|id|n> <verb>``; its usage names the address once."""

    def get_params(self, ctx: Any) -> list[Any]:
        return [
            _without_usage_piece(p) if p.metavar == ADDRESS_METAVAR else p
            for p in super().get_params(ctx)
        ]


def _without_usage_piece(param: Any) -> Any:
    """A copy of *param* that still parses and is described, but adds nothing to usage lines."""

    def no_pieces(_ctx: Any) -> list[str]:
        return []

    clone = copy.copy(param)
    clone.get_usage_pieces = no_pieces
    return clone


def address_epilog(group: str, noun: str, examples: Sequence[str], group_verbs: str) -> str:
    """The epilog of a roster group: how to address one entry, with examples, one per line
    (Rich renders each blank-line-separated paragraph of an epilog on its own line). The
    ``{verbs}`` marker is filled in once the addressed verbs are registered."""
    one = f"{article(noun)} {noun}"
    paragraphs = [
        f"Address {one}: sq {group} {ADDRESS_METAVAR} VERB, where VERB is one of {{verbs}}.",
        "Examples:",
        *examples,
        f"A slug matching a group verb ({group_verbs}) cannot address {one} by slug; "
        "use the full ID or bare number instead.",
    ]
    return "\n\n".join(paragraphs)


class AddressDispatchGroup(typer.core.TyperGroup):
    """A TyperGroup that routes an unknown command token to a hidden ``_addr`` subgroup.

    Named commands (``catalog``, ``activate``, ``add``) dispatch normally; any other token (slug,
    full ID or bare number) goes to ``_addr`` with the original args, so its callback consumes it
    as ``ADDR``. Used by ``role_app``, ``skill_app`` and ``operator_app``. A slug equal to a named
    verb is unaddressable by slug (the verb wins in ``get_command``); the number or full ID still
    works.
    """

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
            registered: dict[str, Any] = getattr(addr_cmd, "commands", {})
            verbs = "|".join(n for n, c in registered.items() if not c.hidden)
            has_verb = any(a for a in remaining if not a.startswith("-"))
            if not has_verb and "--help" not in remaining:
                err_console.print(
                    f"[red]error:[/red] missing verb after address {cmd_name!r}. "
                    f"Usage: sq {ctx.info_name} {ADDRESS_METAVAR} "
                    f"{verbs}",
                    soft_wrap=True,
                )
                raise typer.Exit(1)
            # Use a readable display name instead of "_addr" so help/error output shows
            # "sq role <slug|id|n>" rather than "sq role _addr".
            return ADDRESS_METAVAR, addr_cmd, args
        return super()._click_resolve_command(ctx, args)


def addr_verbs(addr_app: typer.Typer, sep: str = "|") -> str:
    """The verbs registered on an addressed subgroup, hidden aliases left out, joined by *sep*
    (``a|b|c`` by default; the help epilog uses ``, `` so the list wraps)."""
    names = [c.name for c in addr_app.registered_commands if c.name and not c.hidden]
    names += [g.name for g in addr_app.registered_groups if g.name and not g.hidden]
    return sep.join(names)


def spec_aware_command_cls(
    refresh_help: Callable[[list[Any]], None],
) -> type[typer.core.TyperCommand]:
    """Build a ``TyperCommand`` subclass that re-derives chosen parameters' help at render time.

    A bundled command is built from the bundled spec, before any squad is known, so a
    plain ``help=`` string is the bundled spec's answer. Click renders ``--help`` through
    ``get_params(ctx)`` after the root callback has bound the per-invocation spec, so refreshing
    there makes the help spec-aware without changing when the command is registered.
    *refresh_help* receives the resolved parameter list and mutates the ``.help`` of the ones it
    recognises, by ``.name``.

    The refresh is fail-soft: ``get_params`` runs outside the ``@command`` boundary that turns a
    ``SquadsError`` into a message, so a raise would escape as a traceback. Help is presentation,
    so on an unresolvable spec the baked text stands and the command body issues the refusal.
    """

    class _SpecAwareCommand(typer.core.TyperCommand):
        def get_params(self, ctx: Any) -> list[Any]:
            params = super().get_params(ctx)
            # see the docstring: presentation degrades, it never raises out of parse
            with contextlib.suppress(Exception):
                refresh_help(params)
            return params

    return _SpecAwareCommand


class CommentGroup(typer.core.TyperGroup):
    """The ``comment`` group: appends when given ``-m``/``--file``, and routes a leading hash to
    the hidden ``_addr`` subgroup carrying ``show``, ``edit`` and ``remove``.

    Only a bare positional token is read as a hash; a message arrives as an option value, which
    the parser has consumed by then.
    """

    def _click_resolve_command(self, ctx: Any, args: list[str]) -> Any:  # type: ignore[override]
        token = args[0]
        addr_cmd = self.get_command(ctx, "_addr")
        if addr_cmd is None or ctx.resilient_parsing:
            return super()._click_resolve_command(ctx, args)
        if not discussion.is_hash_token(token):
            err_console.print(
                f"[red]error:[/red] {e(repr(token))} is not a comment hash (4 or more hex "
                "characters); a new comment takes -m or --file",
                soft_wrap=True,
            )
            raise typer.Exit(2)
        registered: dict[str, Any] = getattr(addr_cmd, "commands", {})
        verbs = [n for n, c in registered.items() if not c.hidden]
        if len(args) < 2 or not (args[1].startswith("-") or args[1] in verbs):
            err_console.print(
                f"[red]error:[/red] missing verb after {e(token)}: {'|'.join(verbs)}",
                soft_wrap=True,
            )
            raise typer.Exit(2)
        return "HASH", addr_cmd, args


class _HashGroup(typer.core.TyperGroup):
    """The group behind a hash: its name is the hash in usage, so the argument is not repeated."""

    def collect_usage_pieces(self, ctx: Any) -> list[str]:
        return [self.subcommand_metavar]

    def get_params(self, ctx: Any) -> list[Any]:
        # a verb's usage path is built from this group's params: the name already shows the hash
        return [] if ctx.command is not self else super().get_params(ctx)


@dataclass(frozen=True)
class CommentHost:
    """A discussion host's comment operations and request types, and how it reads its address
    off the Click context: a work item's, a sub-entity's, or a role's, skill's or operator's."""

    add: Operation[Any, CommentAdded]
    show: Operation[Any, CommentShown]
    edit: Operation[Any, CommentEdited]
    removal: Operation[Any, CommentSelection]
    remove: Operation[Any, CommentSelection]
    add_request: type[BaseModel]
    hash_request: type[BaseModel]
    edit_request: type[BaseModel]
    address: Callable[[typer.Context], dict[str, Any]]
    #: The host's ``comments`` listing and its request; ``None`` where the host has no such verb.
    listing: tuple[Operation[Any, Comments], type[BaseModel]] | None = None


def _register_comment_append(comment_app: typer.Typer, host: CommentHost) -> None:
    @comment_app.callback(invoke_without_command=True)
    @handle_errors
    def comment(  # pyright: ignore[reportUnusedFunction] — registered by the decorator
        ctx: typer.Context,
        message: list[str] = message_option(COMMENT_POINT_HELP),
        file: str | None = file_option(),
        as_: str | None = as_option(),
        json_out: bool = typer.Option(
            False, "--json", help="Print one JSON object: the comment added."
        ),
    ) -> None:
        """Add a comment to the discussion, or act on one by its hash.

        Add:
          comment -m TEXT [-m TEXT ...] --as SLUG
          comment --file PATH --as SLUG
        By hash:
          comment HASH show|edit|remove

        HASH is any 4 or more leading hex characters. -m, --file and --as go after
        the verb. Only a comment's author can edit or remove it.
        """
        from squads._cli import _calls as calls  # _calls imports this module

        if ctx.invoked_subcommand is not None:
            if message or file or as_:
                err_console.print(
                    "[red]error:[/red] -m, --file and --as go after the verb: "
                    "comment HASH edit -m TEXT --as SLUG",
                    soft_wrap=True,
                )
                raise typer.Exit(2)
            if json_out:
                err_console.print(
                    "[red]error:[/red] --json goes after the verb: comment HASH show --json",
                    soft_wrap=True,
                )
                raise typer.Exit(2)
            return
        slug = require_as(as_)
        texts = resolve_comment_messages(message or None, file)
        declare_actor(slug)
        response = calls.call(host.add, host.add_request(**host.address(ctx), texts=texts))
        if json_out:
            calls.print_json(host.add, response)
        else:
            calls.print_warnings(response)
            write_render.render_comment_added(response.data, console)
        calls.finish(response, json_out=json_out)


def _register_comment_show(addr_app: typer.Typer, host: CommentHost) -> None:
    @addr_app.command("show")
    @handle_errors
    def show(  # pyright: ignore[reportUnusedFunction] — registered by the decorator
        ctx: typer.Context,
        json_out: bool = typer.Option(False, "--json", help="Print one JSON object: the comment."),
        raw: bool = raw_option(),
    ) -> None:
        """Show one comment."""
        from squads._cli import _calls as calls  # _calls imports this module

        request = host.hash_request(**host.address(ctx), hash=ctx.obj["hash"])
        response = calls.call(host.show, request)
        if json_out:
            calls.print_json(host.show, response)
        else:
            calls.print_warnings(response)
            write_render.render_comment_shown(response.data, console, raw=raw)
        calls.finish(response, json_out=json_out)


def _register_comment_edit(addr_app: typer.Typer, host: CommentHost) -> None:
    @addr_app.command("edit")
    @handle_errors
    def edit(  # pyright: ignore[reportUnusedFunction] — registered by the decorator
        ctx: typer.Context,
        message: list[str] = message_option(COMMENT_POINT_HELP),
        file: str | None = file_option(),
        as_: str | None = as_option(COMMENT_AUTHOR_AS_HELP),
        json_out: bool = typer.Option(
            False, "--json", help="Print one JSON object: the edited comment."
        ),
    ) -> None:
        """Replace a comment's text; its header gains an edit mark.

        The header keeps the comment's time and author.
        """
        from squads._cli import _calls as calls  # _calls imports this module

        slug = require_as(as_)
        texts = resolve_comment_messages(message or None, file)
        declare_actor(slug)
        request = host.edit_request(**host.address(ctx), hash=ctx.obj["hash"], texts=texts)
        response = calls.call(host.edit, request)
        if json_out:
            calls.print_json(host.edit, response)
        else:
            calls.print_warnings(response)
            write_render.render_comment_edited(response.data, console)
        calls.finish(response, json_out=json_out)


def _register_comment_remove(addr_app: typer.Typer, host: CommentHost) -> None:
    @addr_app.command("remove")
    @handle_errors
    def remove(  # pyright: ignore[reportUnusedFunction] — registered by the decorator
        ctx: typer.Context,
        as_: str | None = as_option(COMMENT_AUTHOR_AS_HELP),
        yes: bool = yes_option(),
        json_out: bool = typer.Option(
            False, "--json", help="Print a JSON array, one object per removed copy."
        ),
    ) -> None:
        """Delete a comment, and every copy of it if it was written twice."""
        from squads._cli import _calls as calls  # _calls imports this module

        declare_actor(require_as(as_))
        token: str = ctx.obj["hash"]
        if not yes:
            # The user confirms the comments shown, so the removal names them by their full hash:
            # a comment changed since no longer resolves, and nothing is removed.
            preview = calls.call(host.removal, host.hash_request(**host.address(ctx), hash=token))
            # Under --json, stdout carries only the document.
            write_render.render_comment_removal(preview.data, err_console if json_out else console)
            n = len(preview.data.items)
            confirm(
                f"Remove {'this comment' if n == 1 else f'these {n} comments'}?",
                json_out=json_out,
            )
            token = preview.data.items[0].hash
        response = calls.call(host.remove, host.hash_request(**host.address(ctx), hash=token))
        if json_out:
            calls.print_json(host.remove, response)
        else:
            calls.print_warnings(response)
            write_render.render_comment_removed(response.data, console)
        calls.finish(response, json_out=json_out)


def register_comment_group(app: typer.Typer, host: CommentHost) -> None:
    """Register ``comment`` on an addressed subgroup as the group of :class:`CommentGroup`.

    One body for every level (a work item, a sub-entity, a role, skill or operator), so a comment
    has the same author, header and ``@mention`` rules wherever it is written or changed.
    """
    comment_app = typer.Typer(cls=CommentGroup, add_completion=False)
    addr_app = typer.Typer(cls=_HashGroup, add_completion=False)

    _register_comment_append(comment_app, host)

    @addr_app.callback()
    def _hash(  # pyright: ignore[reportUnusedFunction] — registered by the decorator
        ctx: typer.Context,
        hash_value: str = typer.Argument(
            ..., metavar="HASH", help="4 or more leading hex characters."
        ),
    ) -> None:
        """Show, edit or remove one comment, addressed by its hash."""
        ctx.obj = extend_obj(ctx.obj, hash=hash_value)

    _register_comment_show(addr_app, host)
    _register_comment_edit(addr_app, host)
    _register_comment_remove(addr_app, host)
    comment_app.add_typer(addr_app, name="_addr", hidden=True)
    app.add_typer(comment_app, name="comment")


def register_comment_verbs(app: typer.Typer, host: CommentHost) -> None:
    """Register ``comment`` and ``comments`` on an addressed subgroup: a work item's, or a
    role's, skill's or operator's."""

    register_comment_group(app, host)
    assert host.listing is not None  # a host with a `comments` verb names its listing
    listing, listing_request = host.listing

    @app.command("comments")
    @handle_errors
    def comments(  # pyright: ignore[reportUnusedFunction] — registered by the decorator
        ctx: typer.Context,
        json_out: bool = typer.Option(
            False, "--json", help="Print a JSON array, one object per comment."
        ),
    ) -> None:
        """Print the top-level discussion."""
        from squads._cli import _calls as calls  # _calls imports this module

        response = calls.call(listing, listing_request(**host.address(ctx)))
        if json_out:
            calls.print_json(listing, response)
        else:
            calls.print_warnings(response)
            comment_render.print_comments(console, response.data.items)
        calls.finish(response, json_out=json_out)


#: A work item's discussion.
ITEM_COMMENTS = CommentHost(
    add=ops.ITEM_COMMENT_ADD,
    show=ops.ITEM_COMMENT_SHOW,
    edit=ops.ITEM_COMMENT_EDIT,
    removal=ops.ITEM_COMMENT_REMOVAL,
    remove=ops.ITEM_COMMENT_REMOVE,
    add_request=CommentAddRequest,
    hash_request=CommentRequest,
    edit_request=CommentEditRequest,
    address=lambda ctx: {key: ctx.obj[key] for key in ("id", "type", "address")},
    listing=(ops.ITEM_COMMENTS, CommentsRequest),
)


def roster_comments(
    kind_ops: tuple[
        Operation[Any, Comments],
        Operation[Any, CommentAdded],
        Operation[Any, CommentShown],
        Operation[Any, CommentEdited],
        Operation[Any, CommentSelection],
        Operation[Any, CommentSelection],
    ],
    address: Callable[[typer.Context], str],
) -> CommentHost:
    """A roster entry's discussion, from its kind's operations (listing, add, show, edit, removal,
    remove) and the address its group parsed."""
    listing, add, show, edit, removal, remove = kind_ops
    return CommentHost(
        add=add,
        show=show,
        edit=edit,
        removal=removal,
        remove=remove,
        add_request=RosterCommentAddRequest,
        hash_request=RosterCommentRequest,
        edit_request=RosterCommentEditRequest,
        address=lambda ctx: {"addr": address(ctx)},
        listing=(listing, RosterAddress),
    )


def require_update_fields(**given: object) -> None:
    """Refuse an ``update`` that names no field, listing the options it takes."""
    if all(v is None for v in given.values()):
        options = [f"--{k.replace('_', '-')}" for k in given]
        wanted = options[0] if len(options) == 1 else f"at least one of {', '.join(options)}"
        raise SquadsError(f"nothing to update (pass {wanted})")


def print_warnings(warnings: list[str]) -> None:
    """One ``warning:`` line per notice."""
    for warning in warnings:
        console.print(f"[yellow]warning:[/yellow] {e(warning)}", soft_wrap=True)


def resolve_local_id(token: str, kind: str) -> str:
    """A CLI sub-entity token → canonical local id: ``2`` → ``STn``/``USn``/``Fn``."""
    return discussion.local_id_for(kind, token, get_active_spec())


def confirm(text: str, *, json_out: bool) -> None:
    """Ask *text* and abort unless the answer is yes. Under ``--json`` the prompt goes to stderr
    and the answer is read from stdin directly, so stdout carries the document alone."""
    if not json_out:
        typer.confirm(text, abort=True)
        return
    while True:
        err_console.print(f"{text} [y/N]: ", end="", markup=False, highlight=False)
        line = sys.stdin.readline()
        if not line:
            raise typer.Abort()
        answer = line.strip().lower()
        if answer in ("y", "yes"):
            return
        if answer in ("", "n", "no"):
            raise typer.Abort()
        err_console.print("Error: invalid input", markup=False, highlight=False)


def require_as(as_: str | None) -> str:
    """Validate ``--as`` was supplied and return it.

    ``--as`` has no default: attribution is only knowable at the moment the command is
    typed, so a missing flag must fail loudly rather than silently recording the
    comment/notice in the operator's voice.
    """
    if not as_:
        raise SquadsError("--as is required: the actor's slug")
    return as_


def declare_actor(as_: str | None) -> None:
    """Declare an optional ``--as`` as the actor of the call that follows, which checks it
    against the roster; the system slug is refused here, before anything is read."""
    if as_ is not None:
        refuse_system_actor(as_)
        actor.set_actor(as_)


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
    own custom axis). ``collection_code`` is usually a field's own ``.collection`` (resolved via
    :func:`squads._badges.resolve_collection` at the call site).
    """
    active_spec = spec if spec is not None else get_active_spec()
    coll = active_spec.collections.get(collection_code)
    code = value.strip().lower()
    if coll is None or code not in coll.badge_codes:
        choices = ", ".join(b.code for b in coll.badges) if coll else ""
        raise SquadsError(f"unknown {collection_code} {value!r} (one of: {choices})")
    return code


def parse_badge_field(
    field_code: str, *, ordered: bool = False, spec: WorkflowSpec | None = None
) -> str:
    """Validate *field_code* as a badge field some non-roster type declares.

    With *ordered*, only a field bound to an ordered collection is accepted (the ones that rank).
    """
    active_spec = spec if spec is not None else get_active_spec()
    codes = [f.code for f in badges.filterable_fields(active_spec, ordered=ordered)]
    code = field_code.strip()
    if code not in codes:
        kind = "sort field" if ordered else "badge field"
        raise SquadsError(f"unknown {kind} {field_code!r} (one of: {', '.join(codes)})")
    return code


def parse_filter_badge_code(field_code: str, value: str, spec: WorkflowSpec | None = None) -> str:
    """Validate a cross-type filter value for badge field *field_code*.

    ``sq list``/``sq tree`` filter every type at once, so any code declared by any type's
    binding of the field is accepted (:func:`squads._badges.field_badge_codes`) and
    ``ItemFilter`` matches per item. Validating against a collection named ``priority`` would
    refuse ``--priority m`` for a squad that binds task priority to a ``tshirt`` collection.
    """
    active_spec = spec if spec is not None else get_active_spec()
    codes = badges.field_badge_codes(field_code, active_spec)
    code = value.strip().lower()
    if code not in codes:
        raise SquadsError(f"unknown {field_code} {value!r} (one of: {', '.join(codes)})")
    return code
