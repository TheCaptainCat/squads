"""Shared CLI helpers: console, error handling, service resolution, value parsing."""

import contextlib
import copy
import enum
import functools
import io
import json
import os
import sys
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Any, cast

import anyio
import typer
import typer._click as _click  # underscore is upstream's own private module path, not ours
import typer._click.globals as _click_globals  # ditto — upstream's, not ours
import typer.core
import typer.main
from rich.console import Console, Group, RenderableType
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from squads import __version__, _pronouns
from squads import _actor as actor
from squads import _badges as badges
from squads import _discussion as discussion
from squads._cli._markup import escape_markup
from squads._cli._render._style import intent_style
from squads._context import get_context, rebind
from squads._errors import (
    NotInitializedError,
    RoleNotFoundError,
    SquadsError,
)
from squads._index._store import enter_read_scope, exit_read_scope
from squads._interactions._role_guidance import allowed_create_types
from squads._interactions._skills import role_origin
from squads._language import resolve_working_language
from squads._models import _attributes as attrs
from squads._models._attributes import AttributeKey
from squads._models._item import (
    DISPLAY_ID_PADDING,
    Item,
    format_item_id,
    parse_item_token,
    split_ref,
)
from squads._models._omission import Omission
from squads._models._participants import refuse_system_actor
from squads._models._schema import SCHEMA_VERSION, schema_tuple
from squads._models._subentity import SubEntity
from squads._paths import SquadPaths, process_dir, resolve
from squads._roles._catalog import RoleDef
from squads._roles._models import CatalogSource
from squads._roles._resolver import (
    materialised_base,
    resolve_pronouns,
    resolve_role_with_base,
    stored_values,
)
from squads._services._results import BlockResult, SelfRemedied, SubentityDetail
from squads._services._service import (
    BYPASS_FALLBACKS,
    MIGRATE_FALLBACKS,
    Service,
    compose_first_of,
    open_service,
)
from squads._spec_documents import SpecSources, spec_sources
from squads._specload import override_present
from squads._util import article
from squads._workflow import CATEGORIES, bundled_spec
from squads._workflow._models import RESERVED_CLI_ALIASES, WorkflowSpec, reserved_alias_owner


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


def set_active_spec(spec: WorkflowSpec | None) -> None:
    rebind(active_spec=spec)


def get_active_spec() -> WorkflowSpec:
    """Return the per-invocation spec, or the bundled spec if none has been bound yet.

    Raises ``SquadsError`` when the squad has a workflow override that failed to resolve
    (``RequestContext.spec_error``): the bundled spec would describe vocabulary the project did not
    declare, indistinguishably from a correct answer. Every read surface refuses with the text
    ``open_service`` raises (``_workflow._loader.spec_refusal``). ``sq workflow lint`` never calls
    this, so the diagnostic stays reachable; ``sq check`` and ``sq repair`` take the refusal from
    ``open_service`` and report it as a finding.
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
    to the answering surfaces, :func:`get_active_spec` and ``open_service``.
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


def stale_static_aliases(spec: WorkflowSpec) -> frozenset[str]:
    """Static type aliases whose owner is still declared but no longer declares them.

    That is a rename. A dropped owner type is excluded: its aliases keep dispatching into the
    membership gate, whose "unknown item type" message names the type rather than the alias typed
    (see ``_dropped_static_names``). Empty for a non-customized squad.
    """
    return frozenset(
        alias
        for alias, owner in RESERVED_CLI_ALIASES
        if (owner_spec := spec.items.get(owner)) is not None and alias not in owner_spec.aliases
    )


def static_alias_is_stale(ctx: Any, cmd_name: str) -> bool:
    """True when *cmd_name* is a static type alias the resolved spec no longer declares.

    The root table binds every bundled alias at import time, so after an override renames
    ``feature``'s aliases, ``sq feat 9 show`` would still dispatch and exit 0. Unlike a dropped
    type name, a stale alias has no accurate downstream refusal (its type is usually still
    valid), so the caller substitutes :func:`stale_alias_command`. Any spec-resolution error
    returns ``False``.
    """
    if reserved_alias_owner(cmd_name) is None:
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


def bind_active_spec(client_cwd: Path | None) -> tuple[WorkflowSpec | None, str | None]:
    """Resolve the spec for this invocation, merging the squad's override as ``open_service`` does.

    Returns ``(spec, spec_error)`` without binding it; the caller binds it in the per-invocation
    ``RequestContext``.

    - No squad or no override file: ``(bundled spec, None)``, or ``(None, None)`` when
      ``resolve()`` itself failed; both mean "use the bundled spec".
    - An override file that will not load: ``(None, refusal)``, never a fall back to bundled. A
      catalog rendered from a spec the project did not declare is not an honest answer to "what
      types do I have", and a client could not tell it apart from a correct one.

    ``client_cwd`` goes straight to ``resolve()``, so every resolution path shares one base.
    """
    from squads._paths import resolve
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

    Returns ``None`` when the spec is fine. A name absent from the static table is checked
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


async def warn_duplicate_id(svc: Service, item: Item) -> None:
    """Warn on stderr when more than one file carries *item*'s id: the file shown is the
    indexed one, and only `sq check` says which files the others are."""
    message = await svc.duplicate_id_error(item)
    if message is not None:
        err_console.print(
            f"[yellow]warning:[/yellow] {e(message)} -- showing the indexed file; run `sq check`",
            soft_wrap=True,
        )


def unreadable_report(msg: str) -> str:
    """One ``repair``/``adopt``/``migrate`` line for an unreadable file. A line that carries its
    own remedy is printed as is; every other file gets the generic carried-forward note."""
    if isinstance(msg, SelfRemedied):
        return f"[red]error[/red]: {e(msg)}"
    return (
        f"[red]error[/red]: {e(msg)} — its previous index entry, if any, was carried "
        "forward as-is; fix the file and repair again"
    )


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


def depth_option(default: int | None, *flags: str) -> Any:
    return typer.Option(
        default,
        "--depth",
        *flags,
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


def view_disable_result_message(
    item_id: str, name: str, *, was_present: bool, changed: bool
) -> str:
    """The one print line of ``view disable``, worded for what happened.

    ``disable_view`` is ungated and writes one of three outcomes: a fresh disabled tag where none
    was placed, an enabled tag turned off, or a conflicting pair collapsed to one disabled copy.
    ``was_present`` (read before the write, via ``ViewsMixin.view_tag_present``) tells the first
    apart, since nothing was there to disable.
    """
    if not changed:
        return f"{item_id}: view {e(name)} already disabled, unchanged"
    if not was_present:
        return f"{item_id}: view {e(name)} had no existing tag — placed disabled in sq:body"
    return f"{item_id}: view {e(name)} disabled in sq:body"


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


def print_block(parent_id: str, res: BlockResult, json_out: bool) -> None:
    """Report a scaffolded story/subtask/finding block + where the agent should write its body."""
    if json_out:
        data: dict[str, object] = {
            "local_id": res.local_id,
            "path": str(res.path),
            "region": res.body_tag,
            "start_line": res.start_line,
            "end_line": res.end_line,
        }
        if res.title_advisory is not None:
            data["title_advisory"] = res.title_advisory
        print_json_clean(json.dumps(data))
        return
    console.print(f"added [bold]{res.local_id}[/bold] to {parent_id}")
    console.print(
        f"  set its body:  [cyan]{e(res.body_command)}[/cyan]"
        "  [dim](or --file body.md / --file -)[/dim]",
        soft_wrap=True,
    )
    if res.title_advisory is not None:
        console.print(e(res.title_advisory))


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


def _milestone_target_date_row(it: Item) -> str | None:
    """The panel row for a milestone's ``target_date``, or ``None`` when unset.

    A one-off: declared attributes carry no label or formatting in the spec, so a generic renderer
    would need vocabulary the codebase does not have.
    """
    if it.type != "milestone":
        return None
    target_date = it.attribute(AttributeKey.TARGET_DATE)
    return f"[bold]target date:[/bold] {e(str(target_date))}" if target_date else None


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
    milestone_row = _milestone_target_date_row(it)
    if milestone_row:
        rows.append(milestone_row)
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
            rid if not kind else f"{rid} ({kind})" for rid, kind in (split_ref(r) for r in it.refs)
        )
        rows.append(f"[bold]refs:[/bold] {e(rendered)}")
    rows.append(f"[bold]file:[/bold] {it.path}")
    return rows


def _subentity_badge_line(sub: SubEntity, kind: str, carrier_title: str | None = None) -> str:
    """The badges for a sub-entity, joined for a single display line: status, then one per
    declared field with a stored value, then the assignee, then the mapped story iff the kind
    declares ``maps_parent_story``, then the item that carries its deferred work.

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
    if sub.deferred_to:
        parts.append(
            f"Deferred to {sub.deferred_to} — {carrier_title}"
            if carrier_title
            else f"Deferred to {sub.deferred_to}"
        )
    return "  ".join(parts)


def _subentity_pane_title_raw(sub: SubEntity, kind: str, carrier_title: str | None = None) -> str:
    """Build the raw (un-escaped) pane title for a sub-entity.

    Returns plain text with no Rich markup escaping applied.  Callers that need to pass the title
    into a Rich Panel (styled path) must apply e() themselves; callers printing with markup=False
    (plain path) use this value directly so no backslashes leak.
    """
    return f"{sub.local_id} — {sub.title}  {_subentity_badge_line(sub, kind, carrier_title)}"


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
        raw_title = _subentity_pane_title_raw(sub, kind, detail.carrier_title)
        body_text = detail.body or ""

        if styled:
            inner_renderables: list[RenderableType] = []
            if body_text:
                inner_renderables.append(Markdown(body_text))
            if comments:
                sub_cmts = detail.comments
                if sub_cmts:
                    for cmt, short in zip(sub_cmts, discussion.short_hashes(sub_cmts), strict=True):
                        cmt_title = (
                            f"{e(short)}  {e(cmt.timestamp)}  {e(discussion.author_label(cmt))}"
                            f"{e(discussion.edited_suffix(cmt))}"
                        )
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
                sub_cmts = detail.comments
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
        console.print(f"[dim]{e(hint)}[/dim]")


def render_body_text(body_text: str, *, raw: bool = False, empty_hint: str | None = None) -> None:
    """Render a body to the console: styled Markdown on a TTY, plain otherwise.

    Always starts with a blank line. For role/skill/operator ``show``; item output passes a
    precomputed ``styled`` flag to :func:`_render_body`. ``empty_hint`` overrides the empty-body
    hint, e.g. ``sq sync`` for groups whose bodies are template-managed and have no ``body`` verb.
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
    cmt_list = discussion.split_discussion(
        await svc.read_discussion(it.id), sequence_id=it.sequence_id
    )
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
    if it.type == "milestone":  # one-off; see _build_item_panel_rows' comment on why
        target_date = it.attribute(AttributeKey.TARGET_DATE)
        if target_date:
            lines.append(f"- **target date:** {target_date}")
    if it.assignee:
        lines.append(f"- **assignee:** {it.assignee}")
    if it.parent:
        lines.append(f"- **parent:** {it.parent}")
    if it.author:
        lines.append(f"- **author:** {it.author}")
    if it.refs:
        rendered_refs = ", ".join(
            rid if not kind else f"{rid} ({kind})" for rid, kind in (split_ref(r) for r in it.refs)
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
            _subentity_badge_line(sub, kind, detail.carrier_title),
            "",
            detail.body or "",
        ]
    return lines


async def _print_item_raw(svc: Service, it: Item, *, comments: bool, full: bool) -> None:
    """The ``--raw`` dossier: a markdown document with no Rich chrome.

    ``# TYPE-N — <title>``, a metadata bullet block, then the body verbatim; ``--full`` appends one
    section per sub-entity and ``--comments`` a Discussion section. Printed once with
    ``markup=False, soft_wrap=True`` so nothing is escaped or reflowed.
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
        cmts = discussion.split_discussion(
            await svc.read_discussion(it.id), sequence_id=it.sequence_id
        )
        lines += ["", "## Discussion"]
        if cmts:
            for cmt, short in zip(cmts, discussion.short_hashes(cmts), strict=True):
                head = f"### {short} {discussion.author_label(cmt)} — {cmt.timestamp}"
                lines += ["", head + discussion.edited_suffix(cmt), "", cmt.body]
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
    """Render an item's metadata and body for ``sq <type> <num> show``.

    ``--raw`` prints the clean-markdown dossier (:func:`_print_item_raw`); otherwise a Rich panel
    and summary table, with the body as styled Markdown on a color TTY and plain text when piped
    or under ``NO_COLOR``. ``--comments`` appends the discussion as per-comment panes; ``--full``
    adds one pane per sub-entity, which embeds its own comments when combined with ``--comments``.
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
    # Every declared field for this kind, so a custom badge field shows up too.
    for field in get_active_spec().fields_for(kind):
        value = info.badge_value(field.code)
        if value:
            meta.append(f"{field.label.lower()}: {e(value)}")
    if info.story:
        meta.append(f"story: {e(info.story)}")
    if info.deferred_to:
        meta.append(
            f"deferred to: {e(info.deferred_to)}"
            + (f" — {e(detail.carrier_title)}" if detail.carrier_title else "")
        )
    console.print("  " + "   ".join(meta))
    console.print()
    console.print(e(detail.body) if detail.body else "[dim](no body yet)[/dim]")
    console.print("\n[bold]Discussion[/bold]")
    if detail.comments:
        (_render_comments_styled if _is_styled() else _render_comments_plain)(detail.comments)
    else:
        console.print(e(detail.discussion) if detail.discussion else "[dim](none)[/dim]")


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


@dataclass(frozen=True)
class ItemRowFields:
    """The per-record inputs :func:`build_item_row_json` needs — taken generically off
    whatever carries them (an ``Item``, or a view source's own resolved record) rather than a
    literal ``Item`` type, so ``sq tree``'s own node builder and a ``ref``/``subtree`` view's
    ``--json`` dispatch (``squads._cli._workflow_cmd``) can build one from either without
    either needing the other's concrete type."""

    id: str
    type: str
    title: str
    status: str
    priority: str | None
    assignee: str | None
    badge_value: Callable[[str], str | None]


def build_item_row_json(
    fields: ItemRowFields,
    *,
    spec: WorkflowSpec,
    blocked_ids: set[str],
    anchor: bool = False,
    children: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """One node of ``sq tree --json``, built by both ``sq tree`` and the ``--json`` of a view.

    A ``ref``/``subtree`` view shares the field list so the two cannot drift. ``anchor`` and
    ``children`` default to the flat-record answer (no forced root, no nesting).
    """
    return {
        "id": fields.id,
        "type": fields.type,
        "title": fields.title,
        "status": fields.status,
        "priority": fields.priority,
        "assignee": fields.assignee,
        "blocked": fields.id in blocked_ids,
        "badges": badges.resolve_badges(spec, fields.type, fields.badge_value),
        "anchor": anchor,
        "children": children if children is not None else [],
    }


def build_subentity_row_json(
    *,
    local_id: str,
    title: str,
    status: str,
    assignee: str | None,
    severity: str | None,
    story: str | None,
    deferred_to: str | None,
) -> dict[str, Any]:
    """One row of the per-kind ``sq <type> <n> <kind>s --json`` shape: ``local_id``/``title``/
    ``status``/``assignee``/``severity``/``story``/``deferred_to``. Shared by that list command
    (``squads._cli._items``) and a ``subentity`` view's ``--json`` dispatch
    (``squads._cli._workflow_cmd``), the same way :func:`build_item_row_json` is shared for the
    tree shape."""
    return {
        "local_id": local_id,
        "title": title,
        "status": status,
        "assignee": assignee,
        "severity": severity,
        "story": story,
        "deferred_to": deferred_to,
    }


def build_subentity_json(spec: WorkflowSpec, kind: str, detail: SubentityDetail) -> dict[str, Any]:
    """The sub-entity JSON object, shared by ``build_item_json`` and a sub-entity ``show --json``.

    Frontmatter fields (``local_id``/``title``/``status``/``assignee``/``severity``/``story``/
    ``extra``), ``body``, the per-field ``badges`` map and a ``discussion`` array shaped like the
    item-level one.
    """
    data: dict[str, Any] = json.loads(detail.info.model_dump_json())
    data["body"] = detail.body
    data["badges"] = badges.resolve_badges(spec, kind, detail.info.badge_value)
    data["discussion"] = discussion.comments_json(detail.comments)
    return data


async def build_item_json(svc: Service, it: Item) -> str:
    """The ``show --json`` payload: frontmatter fields plus additive keys.

    Adds ``body`` (stored markdown, view tags left as tags), ``views`` (the transform output of
    each placed, enabled view that declares one), ``discussion`` (``{author, author_slug, ts,
    edited_ts, hash, short_hash, body}`` list), ``badges`` (keyed by field code), and per
    ``subentities`` entry the shape from :func:`build_subentity_json`. Always present, not gated
    by ``--comments``/``--full``, so the payload is identical across ``--raw``/``--comments``/
    ``--full``.
    """
    spec = get_active_spec()
    payload: dict[str, Any] = it.to_row()
    payload["body"] = await svc.read_stored_body(it.id)
    payload["views"] = await svc.view_data(it.id)
    payload["discussion"] = discussion.comments_json(await svc.comments(it.id))
    payload["badges"] = badges.resolve_badges(spec, it.type, it.badge_value)
    kind = spec.item_subentity_kind(it.type)
    if kind:
        subentities: list[dict[str, Any]] = []
        for sub_data in payload["subentities"]:
            detail = await svc.get_block(it.id, kind, sub_data["local_id"])
            subentities.append(build_subentity_json(spec, kind, detail))
        payload["subentities"] = subentities
    return json.dumps(payload)


def role_base_for_show(slug: str, it: Item | None, catalog: CatalogSource) -> RoleDef | None:
    """The merge base for a role card: the base the item in hand stores (``materialised_base``).

    A slug with no item has no base and resolves through the catalog. Shared by ``sq role <slug>
    show`` and a ``role`` source's ``--json`` dispatch so both build from the same base.
    """
    if it is not None:
        return materialised_base(it, catalog)
    return None


def origin_json(value: str | None) -> dict[str, str]:
    """The ``origin`` key of a ``--json`` payload, absent when the item stores no valid one."""
    return {} if value is None else {"origin": value}


def named_markup(svc: Service, name: str, pronouns: str | None, *, style: str = "") -> str:
    """:func:`~squads._pronouns.named` under the squad's display setting, as Rich markup for a
    line that is assembled from strings."""
    return _pronouns.named(
        name, pronouns, enabled=svc.paths.config.display.pronouns, style=style
    ).markup


async def build_role_json_payload(
    svc: Service,
    slug: str,
    item_id: str | None,
    it: Item | None,
    base_role: RoleDef | None,
    addr: str,
) -> dict[str, object]:
    """The ``--json`` payload for a resolved role, shared by ``sq role <slug> show`` and a view.

    ``skills`` is resolved once, ahead of the branch, because it is a projection over the index
    (:meth:`Service.resolved_skills_for_role`), never a field of the ``RoleDef`` or the stored
    item. It is live-only: an activated role resolves its full preload set, a bundled-only or
    retired slug the system-only fallback.
    """
    data: dict[str, object] = {"slug": slug, "id": item_id, "activated": item_id is not None}
    data.update(origin_json(role_origin(slug) if it is None else attrs.origin(it)))
    skills = await svc.resolved_skills_for_role(slug)
    pronouns = resolve_pronouns(_pronouns.pronouns(it) if it is not None else None, svc.catalog)
    try:
        r = resolve_role_with_base(
            slug,
            svc.paths.squad_dir,
            base=base_role,
            catalog=svc.catalog,
            stored=stored_values(it),
        )
    except RoleNotFoundError:
        raise SquadsError(f"no role with slug, ID, or number {addr!r}") from None
    data.update(
        {
            "full_name": r.full_name,
            "pronouns": pronouns,
            "title": r.title,
            "mission": r.mission,
            "model": r.model,
            "is_default": r.is_default,
            "can_spawn": r.can_spawn,
            "capabilities": list(r.capabilities),
            "create_lane": sorted(allowed_create_types(r, svc.spec, svc.playbook)),
            "responsibilities": list(r.responsibilities),
            "skills": skills,
        }
    )
    return data


#: ``click.Context.meta`` key marking that an earlier ``command``-wrapped call in this
#: invocation opened the read scope and it is still open, so a later call must not open another.
_READ_SCOPE_META_KEY = "squads.read_scope_token"

#: ``click.Context.meta`` key for the ``Service`` memo of :func:`get_service`, filled only by the
#: cross-checked ``open_service`` path so a plain caller is never handed a bypass-built instance.
_SERVICE_META_KEY = "squads.service_memo"

#: ``click.Context.meta`` key for the bypass-built ``Service`` memo, filled only once the plain
#: path has raised (see :func:`get_service_bypassing_index_cross_check`).
_BYPASS_SERVICE_META_KEY = "squads.service_memo_bypass"


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
    """The current Click invocation's root context, or ``None`` outside of one.

    ``command``-wrapped functions are only ever invoked *by* Click, so this only returns
    ``None`` in the one case that matters: a stray direct call with no Click dispatch at all
    (defensive; never observed in practice).
    """
    ctx = _click_globals.get_current_context(silent=True)
    return ctx.find_root() if ctx is not None else None


def get_service() -> Service:
    """Build (or reuse) the invocation's ``Service``.

    ``sq <type> <n> <verb>`` crosses the sync/async bridge twice (the group's id-resolving callback,
    then the leaf verb; see :func:`command`) and both must share one ``Service`` and ``IndexStore``,
    so the read scope's per-store cache holds and one invocation observes one index state. The memo
    lives on the Click root context's ``meta`` and is gated on :data:`_READ_SCOPE_META_KEY`, the
    marker that opens the scope; ``sq ui`` never passes through :func:`command`, so it gets neither.
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
    """Compose the invocation's ``Service`` in the normal mode, from the spec the root callback's
    :func:`bind_active_spec` already resolved and checked for this invocation.

    ``RequestContext.spec_error`` is the refusal that earlier resolution cached: it is raised
    as it is, rather than composing again just to reproduce the identical error. Outside a squad
    both fields are ``None`` and ``open_service`` raises its own "not a squad" error.
    """
    ctx = get_context()
    if ctx.spec_error is not None:
        raise SquadsError(ctx.spec_error)
    sources = invocation_sources(resolve(client_cwd=ctx.client_cwd).squad_dir)
    return open_service(client_cwd=ctx.client_cwd, resolved_spec=ctx.active_spec, sources=sources)


def get_service_bypassing_index_cross_check(*, bundled_fallback: bool = True) -> Service:
    """Like :func:`get_service`, for a command that must not be blocked by the index cross-check.

    A maintenance command exists to fix what ``open_service``'s cross-check refuses over (a
    corpus/spec conflict, or an index stale against the frontmatter). On a ``SquadsError`` it
    falls back through :data:`BYPASS_FALLBACKS`: the merged spec without the index check, then
    the bundled spec. With ``bundled_fallback=False`` (``sq migrate up``, which must run under
    the declared vocabulary or not at all) the only fallback is :data:`MIGRATE_FALLBACKS`, which
    refuses with the file and cause. The fallback instance is memoized under
    :data:`_BYPASS_SERVICE_META_KEY`, so a plain caller never sees a cross-check-skipping one.
    """
    root = _click_root_context()
    if root is not None and _READ_SCOPE_META_KEY in root.meta:
        cached: Service | None = root.meta.get(_BYPASS_SERVICE_META_KEY)
        if cached is not None:
            return cached
        try:
            return get_service()
        except SquadsError:
            svc = _build_bypass_fallback_service(bundled_fallback=bundled_fallback)
            root.meta[_BYPASS_SERVICE_META_KEY] = svc
            return svc
    try:
        return get_service()
    except SquadsError:
        return _build_bypass_fallback_service(bundled_fallback=bundled_fallback)


def _build_bypass_fallback_service(*, bundled_fallback: bool = True) -> Service:
    ctx = get_context()
    paths = resolve(client_cwd=ctx.client_cwd)
    return compose_first_of(
        paths,
        BYPASS_FALLBACKS if bundled_fallback else MIGRATE_FALLBACKS,
        resolved_spec=ctx.active_spec,
        sources=invocation_sources(paths.squad_dir),
    )


def handle_errors[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return fn(*args, **kwargs)
        except SquadsError as exc:
            err_console.print(f"[red]error:[/red] {e(error_text(exc))}", soft_wrap=True)
            raise typer.Exit(1) from exc

    return wrapper


def command[**P](fn: Callable[P, Awaitable[None]]) -> Callable[P, None]:
    """The single sync-to-async bridge for CLI commands.

    Wraps an ``async def`` Typer command so Typer sees a sync callable with one ``anyio.run`` per
    call, and a ``SquadsError`` becomes a clean message and ``typer.Exit(1)``.

    It also opens the invocation's request-scoped index read (``enter_read_scope`` and
    ``exit_read_scope``) and makes the :func:`get_service` memo live, both keyed on one marker on
    the Click root context's ``meta`` (:data:`_READ_SCOPE_META_KEY`). ``sq <type> <n> <verb>``
    crosses this bridge twice, in two sequential ``anyio.run`` calls (the group's
    ``@item.callback()``, then the leaf verb) that share one root ``Context``: the first call
    opens the scope and records the marker, later calls reuse the scope and the ``Service``, so
    the addressed form reads the index once. The root context's ``call_on_close``, fired once
    after every nested command, closes the scope.
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
            err_console.print(f"[red]error:[/red] {e(error_text(exc))}", soft_wrap=True)
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


def working_language_notice() -> None:
    """Warn on stderr when ``working_language`` is not a language tag; English applies."""
    try:
        sp = resolve(client_cwd=get_context().client_cwd)
    except SquadsError:
        return  # not in a squad, or an unreadable config
    _, problem = resolve_working_language(sp.config.working_language)
    if problem is not None:
        printed_notices().add(problem)
        err_console.print(f"[yellow]warning:[/yellow] {e(problem)}", soft_wrap=True)


class Ground(enum.StrEnum):
    """Why a command may run on a squad whose schema differs from the package's."""

    #: It is the migration: it advances the corpus, so it runs only on a squad that is behind.
    MIGRATION = "is the migration"
    #: It reads the package's own registry and touches no squad state.
    NO_SQUAD_STATE = "touches no squad state"
    #: It holds the reconcile licence. The reconcile is a routine, not a command.
    LICENCE = "holds the reconcile licence"


@dataclass(frozen=True)
class GateGrant:
    """A command's declaration: the ground it gets past the gate on, and the directions."""

    ground: Ground
    behind: bool
    ahead: bool

    def covers(self, *, behind: bool) -> bool:
        return self.behind if behind else self.ahead


_GRANT_ATTR = "__sq_gate_grant__"


def past_the_gate[F: Callable[..., Any]](
    ground: Ground, *, behind: bool = False, ahead: bool = False
) -> Callable[[F], F]:
    """Declare that a command runs on a squad whose schema differs from the package's, on
    *ground*, for the directions given. A command without the declaration is refused there."""

    def _mark(fn: F) -> F:
        setattr(fn, _GRANT_ATTR, GateGrant(ground, behind, ahead))
        return fn

    return _mark


def gate_grant(fn: Callable[..., Any]) -> GateGrant | None:
    """The declaration on *fn*, or ``None``."""
    grant = getattr(fn, _GRANT_ATTR, None)
    return grant if isinstance(grant, GateGrant) else None


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


def apply_gate(grant: GateGrant | None) -> None:
    """Hard-stop when the squad's on-disk schema mismatches this build, unless *grant* covers the
    direction. Behind: tell the user to run ``sq migrate up``; ahead: tell them to upgrade."""
    root = _click_root_context()
    if help_requested(sys.argv[1:], root.command if root is not None else None):
        return
    try:
        sp = resolve(client_cwd=get_context().client_cwd)
    except SquadsError:
        return  # not initialized yet — nothing to gate
    disk = sp.config.schema_version
    if disk == SCHEMA_VERSION:
        return
    behind = schema_tuple(disk) < schema_tuple(SCHEMA_VERSION)
    if grant is not None and grant.covers(behind=behind):
        return
    if behind:
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


#: The command groups that decide the gate for each of their own commands, by the grants those
#: commands declare. Every other command is refused by the root gate.
GATED_GROUPS: frozenset[str] = frozenset({"migrate", "override"})


def grants_by_command(group: typer.Typer) -> dict[str, GateGrant]:
    """The grant each command of *group* declares, by command name."""
    found: dict[str, GateGrant] = {}
    for info in group.registered_commands:
        grant = gate_grant(info.callback) if info.callback is not None else None
        if info.name is not None and grant is not None:
            found[info.name] = grant
    return found


def gate_group_command(ctx: typer.Context, group: typer.Typer) -> None:
    """Gate the invoked command of *group* by the grant it declares; one without a grant is
    refused on a squad whose schema differs from the package's."""
    if ctx.invoked_subcommand is not None:
        apply_gate(grants_by_command(group).get(ctx.invoked_subcommand))


def require_current_schema(subcommand: str | None) -> None:
    """The root gate: every command outside the :data:`GATED_GROUPS` is refused on a squad whose
    schema differs from this build. Those groups decide for their own commands, by the grants
    they declare (see their group callbacks)."""
    if subcommand is None or subcommand in GATED_GROUPS:
        return
    apply_gate(None)


def get_squad_paths() -> SquadPaths:
    """The active squad's paths, resolved without opening its corpus, for a command that reads
    only files beside the index."""
    return resolve(client_cwd=get_context().client_cwd)


def _mismatch_msg(label: str, actual_id: str, actual_type: str, expected_type: str) -> str:
    """Build a uniform type-mismatch error: ``"<label> is <id> (<type>), not a/an <type>"``."""
    return f"{label} is {actual_id} ({actual_type}), not {article(expected_type)} {expected_type}"


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


async def resolve_item_id_typed(token: str, item_type: str, svc: Service) -> str:
    """Resolve a token (``35``, ``000035``, ``PREFIX-000035``) and verify the item's type.

    Raises :class:`SquadsError` naming the real item and type on a mismatch, or naming both
    accepted forms on an unknown item. The prefix comes from the per-invocation spec, so custom
    types that declare their own prefix validate correctly. Takes ``svc`` like
    :func:`resolve_slug_or_raise`; one DB read per call.
    """
    prefix = item_prefix(item_type)
    t = token.strip()
    seq, given_prefix = parse_item_token(token)
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
    """Resolve a token to the full ID of whatever item owns that sequence number.

    A bare number or a full ID is accepted; the type word of a full ID is validated against the
    actual owner. For type-less surfaces (``sq tree``, ``--parent``, ``ref add`` targets).
    """
    return await svc.resolve_any_id(token)


def is_full_id_shape(token: str) -> bool:
    """Return True when *token* looks like a full item ID (``TYPE-NNNNNN``)."""
    _, sep, tail = token.rpartition("-")
    return bool(sep) and tail.isdigit()


async def resolve_agent_addr(token: str, item_type: str, svc: Service) -> str:
    """Resolve a role/skill/operator address to a full item ID, by exact match only.

    In order: a full-ID shape (``ROLE-000001``) and a bare number go through
    :func:`resolve_item_id_typed`; anything else is an exact slug in the service's per-type lookup.
    Raises :class:`SquadsError` when nothing matches.
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


async def address_obj(ctx: typer.Context, resolve: Callable[[], Awaitable[str]]) -> dict[str, Any]:
    """``{"id": <resolved>}`` for an addressed group's ``ctx.obj``. A failed resolution is raised,
    unless help was requested for the verb below, when it is deferred to the first read."""
    try:
        return {"id": await resolve()}
    except SquadsError as exc:
        if not verb_help_requested(ctx):
            raise
        return UnresolvedAddress(exc)


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

    A statically registered command is built at import time, before any squad is known, so a
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


def register_status_verb(
    addr_app: typer.Typer, id_from_ctx: Callable[[typer.Context], str]
) -> None:
    """Register a ``status`` verb on an addressed roster subgroup (``role``/``skill``/``operator``).

    Mirrors ``_cmd_status`` in ``_cli/_items.py`` (``STATUS`` positional, ``--force``, the
    ``{id} → {status}`` line) but drives ``Service.set_roster_status``, which also reports what
    ``--unlink`` severed. ``--unlink`` is offered only here, since only roster types carry the
    config-integrity clauses (``_services/_retirement.py``) it satisfies. ``id_from_ctx``
    extracts the resolved id from ``ctx.obj`` by the caller's convention: role's
    ``_require_id`` raises the "activate it first" error for a bundled-only slug, skill and
    operator read ``ctx.obj["id"]``.
    """

    @addr_app.command("status")
    @command
    async def status(  # pyright: ignore[reportUnusedFunction] — registered via the decorator above
        ctx: typer.Context,
        new_status: str = typer.Argument(..., metavar="STATUS", help=MOVE_STATUS_HELP),
        force: bool = force_transition_option(
            "Make a transition the lifecycle does not allow; a change that would leave "
            "the config invalid is still refused."
        ),
        unlink: bool = typer.Option(
            False,
            "--unlink",
            help=(
                "On a retirement, remove the skill-to-role link the refusal names, then "
                "check again; refused on any other transition."
            ),
        ),
        as_: str | None = edit_as_option(),
    ) -> None:
        """Move this entry to another status."""
        item_id = id_from_ctx(ctx)
        svc = get_service()
        await apply_edit_actor(as_, svc)
        result = await svc.set_roster_status(
            item_id, parse_status(new_status), force=force, unlink=unlink
        )
        console.print(f"{result.item.id} → [bold]{result.item.status}[/bold]")
        if unlink:
            if result.severed:
                for sev in result.severed:
                    console.print(f"  severed {e(sev.referrer)} → {e(sev.target)} ({sev.kind})")
            else:
                console.print("  --unlink: no references severed (nothing was severable)")
        print_warnings(result.warnings)


def register_remove_verb(
    addr_app: typer.Typer,
    id_from_ctx: Callable[[typer.Context], str],
    *,
    refresh_managed: bool = False,
) -> None:
    """Register ``remove`` on an addressed roster subgroup, with ``rm`` as its hidden alias.

    Both names are one command: ``Service.remove_item`` with the ``--purge`` guard, the same
    confirmation line and the same warnings. ``refresh_managed`` re-renders the managed
    ``CLAUDE.md`` roster afterwards (roles and operators appear in it; skills do not).
    ``id_from_ctx`` is the caller's address convention, as for :func:`register_status_verb`.
    """

    @command
    async def remove(
        ctx: typer.Context,
        purge: bool = typer.Option(
            False, "--purge", help="Delete the file too; remove refuses without it."
        ),
        as_: str | None = edit_as_option(),
    ) -> None:
        """Delete this entry for good; it needs `--purge`.

        To keep it on record instead, move it to its archived status
        (see `sq workflow lifecycles`).
        """
        item_id = id_from_ctx(ctx)
        svc = get_service()
        await apply_edit_actor(as_, svc)
        removal = await svc.remove_item(item_id, purge=purge)
        if refresh_managed:
            await svc.refresh_managed()
        console.print(f"removed {item_id}")
        print_warnings(removal.warnings)

    addr_app.command("remove")(remove)
    addr_app.command("rm", hidden=True)(remove)


def register_body_verb(addr_app: typer.Typer, id_from_ctx: Callable[[typer.Context], str]) -> None:
    """Register ``body`` on an addressed roster subgroup: one body for roles, skills and
    operators, driving ``Service.set_body`` so every write meets the same refusals.
    ``id_from_ctx`` is the caller's address convention, as for :func:`register_status_verb`."""

    @command
    async def body(
        ctx: typer.Context,
        message: list[str] = message_option(),
        file: str | None = file_option(),
        append: bool = append_option(),
        force: bool = replace_body_option(),
        as_: str | None = edit_as_option(),
    ) -> None:
        """Set or append to the body.

        Replacing a body someone has already written is refused unless `--force`.
        A role takes prose beside its generated definition. A body generated from a
        declared view (a system or per-type skill) is refused even with `--force`;
        an operator body is never refused for it.
        """
        item_id = id_from_ctx(ctx)
        text = resolve_body(message or None, file)
        svc = get_service()
        await apply_edit_actor(as_, svc)
        await svc.set_body(item_id, text, append=append, force=force)
        console.print(f"{item_id}: body {'appended' if append else 'set'}")

    addr_app.command("body")(body)


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


type CommentTarget = Callable[[typer.Context], tuple[str, tuple[str, str] | None]]
"""A caller's address convention: the item id and, for a sub-entity, its ``(kind, local_id)``."""


def _comment_label(item_id: str, sub: tuple[str, str] | None) -> str:
    return item_id if sub is None else f"{item_id} {sub[1]}"


def _first_line(cmt: discussion.Comment) -> str:
    return (cmt.body.splitlines() or [""])[0]


def _register_comment_append(comment_app: typer.Typer, target: CommentTarget) -> None:
    @comment_app.callback(invoke_without_command=True)
    @command
    async def comment(  # pyright: ignore[reportUnusedFunction] — registered by the decorator
        ctx: typer.Context,
        message: list[str] = message_option(COMMENT_POINT_HELP),
        file: str | None = file_option(),
        as_: str | None = as_option(),
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

        if ctx.invoked_subcommand is not None:
            if message or file or as_:
                err_console.print(
                    "[red]error:[/red] -m, --file and --as go after the verb: "
                    "comment HASH edit -m TEXT --as SLUG",
                    soft_wrap=True,
                )
                raise typer.Exit(2)
            return
        svc = get_service()
        slug = await resolve_actor_or_raise(require_as(as_), svc)
        actor.set_actor(slug)
        item_id, sub = target(ctx)
        await svc.comment(
            item_id, resolve_comment_messages(message or None, file), as_slug=slug, sub=sub
        )
        console.print(f"commented on {_comment_label(item_id, sub)} as {slug}")


def _register_comment_show(addr_app: typer.Typer, target: CommentTarget) -> None:
    @addr_app.command("show")
    @command
    async def show(  # pyright: ignore[reportUnusedFunction] — registered by the decorator
        ctx: typer.Context,
        json_out: bool = typer.Option(False, "--json", help="Print one JSON object: the comment."),
        raw: bool = raw_option(),
    ) -> None:
        """Show one comment."""
        item_id, sub = target(ctx)
        found = await get_service().find_comment(item_id, ctx.obj["hash"], sub=sub)
        first = found.group[0]
        if json_out:
            payload = {
                **discussion.comment_json(first, found.shown),
                "item": found.item.id,
                "scope": found.scope or None,
                "copies": len(found.group),
            }
            print_json_clean(json.dumps(payload))
            return
        where = found.item.id if sub is None else f"{found.item.id} · {sub[0]} {sub[1]}"
        console.print(where, markup=False, highlight=False)
        render = _render_comments_styled if _is_styled() and not raw else _render_comments_plain
        render([first], [found.shown])


def _register_comment_edit(addr_app: typer.Typer, target: CommentTarget) -> None:
    @addr_app.command("edit")
    @command
    async def edit(  # pyright: ignore[reportUnusedFunction] — registered by the decorator
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
        svc = get_service()
        slug = await resolve_actor_or_raise(require_as(as_), svc)
        actor.set_actor(slug)
        item_id, sub = target(ctx)
        messages = resolve_comment_messages(message or None, file)
        res = await svc.edit_comment(item_id, ctx.obj["hash"], messages, as_slug=slug, sub=sub)
        label = _comment_label(item_id, sub)
        if json_out:
            print_json_clean(json.dumps(discussion.comment_json(res.new, res.new_shown)))
        elif res.changed:
            console.print(
                f"edited {res.old_shown} on {label} ({slug}, {res.old.timestamp}); "
                f"now {res.new_shown}",
                markup=False,
                highlight=False,
            )
        else:
            console.print(f"{res.old_shown} on {label} is unchanged; nothing written")


def _register_comment_remove(addr_app: typer.Typer, target: CommentTarget) -> None:
    @addr_app.command("remove")
    @command
    async def remove(  # pyright: ignore[reportUnusedFunction] — registered by the decorator
        ctx: typer.Context,
        as_: str | None = as_option(COMMENT_AUTHOR_AS_HELP),
        yes: bool = yes_option(),
        json_out: bool = typer.Option(
            False, "--json", help="Print a JSON array, one object per removed copy."
        ),
    ) -> None:
        """Delete a comment, and every copy of it if it was written twice."""
        svc = get_service()
        slug = await resolve_actor_or_raise(require_as(as_), svc)
        actor.set_actor(slug)
        item_id, sub = target(ctx)
        found = await svc.find_comment(item_id, ctx.obj["hash"], sub=sub, as_slug=slug)
        if not yes:
            for cmt in found.group:
                console.print(
                    f"{cmt.timestamp} {cmt.author_slug}: {_first_line(cmt)}",
                    markup=False,
                    highlight=False,
                )
            n = len(found.group)
            typer.confirm(
                f"Remove {'this comment' if n == 1 else f'these {n} comments'}?", abort=True
            )
        res = await svc.remove_comment(item_id, ctx.obj["hash"], as_slug=slug, sub=sub)
        if json_out:
            print_json_clean(
                json.dumps([discussion.comment_json(c, res.shown) for c in res.removed])
            )
            return
        count = "" if len(res.removed) == 1 else f" ({len(res.removed)} copies)"
        console.print(f"removed {res.shown} from {_comment_label(item_id, sub)}{count}")


def register_comment_group(app: typer.Typer, target: CommentTarget) -> None:
    """Register ``comment`` on an addressed subgroup as the group of :class:`CommentGroup`.

    One body for every level (a work item, a sub-entity, a role, skill or operator), so a comment
    has the same author, header and ``@mention`` rules wherever it is written or changed.
    """
    comment_app = typer.Typer(cls=CommentGroup, add_completion=False)
    addr_app = typer.Typer(cls=_HashGroup, add_completion=False)

    _register_comment_append(comment_app, target)

    @addr_app.callback()
    def _hash(  # pyright: ignore[reportUnusedFunction] — registered by the decorator
        ctx: typer.Context,
        hash_value: str = typer.Argument(
            ..., metavar="HASH", help="4 or more leading hex characters."
        ),
    ) -> None:
        """Show, edit or remove one comment, addressed by its hash."""
        ctx.obj = extend_obj(ctx.obj, hash=hash_value)

    _register_comment_show(addr_app, target)
    _register_comment_edit(addr_app, target)
    _register_comment_remove(addr_app, target)
    comment_app.add_typer(addr_app, name="_addr", hidden=True)
    app.add_typer(comment_app, name="comment")


def register_comment_verbs(app: typer.Typer, id_from_ctx: Callable[[typer.Context], str]) -> None:
    """Register ``comment`` and ``comments`` on an addressed subgroup: a work item's, or a
    role's, skill's or operator's. ``id_from_ctx`` is the caller's own address convention, as for
    :func:`register_status_verb`."""

    register_comment_group(app, lambda ctx: (id_from_ctx(ctx), None))

    @app.command("comments")
    @command
    async def comments(  # pyright: ignore[reportUnusedFunction] — registered by the decorator
        ctx: typer.Context,
        json_out: bool = typer.Option(
            False, "--json", help="Print a JSON array, one object per comment."
        ),
    ) -> None:
        """Print the top-level discussion."""
        cmt_list = await get_service().comments(id_from_ctx(ctx))
        if json_out:
            print_json_clean(json.dumps(discussion.comments_json(cmt_list)))
            return
        print_comments(cmt_list)


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


def require_as(as_: str | None) -> str:
    """Validate ``--as`` was supplied and return it.

    ``--as`` has no default: attribution is only knowable at the moment the command is
    typed, so a missing flag must fail loudly rather than silently recording the
    comment/notice in the operator's voice.
    """
    if not as_:
        raise SquadsError("--as is required: the actor's slug")
    return as_


async def resolve_actor_or_raise(slug: str, svc: Service) -> str:
    """:func:`resolve_slug_or_raise` for a slug that writes a comment or notice: the system slug
    is refused before the roster is read, so no roster entry can make it resolve."""
    refuse_system_actor(slug)
    return await resolve_slug_or_raise(slug, svc)


def declare_actor(as_: str | None) -> None:
    """Declare an optional ``--as`` as the actor of the call that follows, which checks it
    against the roster; the system slug is refused here, before anything is read."""
    if as_ is not None:
        refuse_system_actor(as_)
        actor.set_actor(as_)


async def apply_edit_actor(as_: str | None, svc: Service) -> None:
    """Record an optional ``--as`` as the actor of the edit that follows, validated as a
    comment's is; without it the actor stays ``system``. Call it before any write."""
    if as_ is not None:
        actor.set_actor(await resolve_actor_or_raise(as_, svc))


async def resolve_slug_or_raise(slug: str, svc: Service, *, live_only: bool = True) -> str:
    """Validate ``slug`` against the roster (agents and operators) and return it normalised (see
    :meth:`~squads._services._base.ServiceCore.resolve_participant`)."""
    return await svc.resolve_participant(slug, live_only=live_only)


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
