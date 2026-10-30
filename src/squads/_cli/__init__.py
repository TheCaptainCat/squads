"""The Typer application, exposed as both `squads` and `sq`."""

import contextlib
import contextvars
import functools
import gc
import importlib
import io
import sys
from collections.abc import Callable, Iterator, MutableMapping, Sequence
from datetime import datetime
from typing import Any, ClassVar, NamedTuple

import typer
import typer._click as _click  # underscore is upstream's own private module path, not ours
import typer.core
import typer.main

from squads import _actor as actor
from squads import _spans as spans
from squads import version_line
from squads._cli import _calls as calls
from squads._cli import _common as common
from squads._context import RequestContext
from squads._workflow import bundled_spec
from squads._workflow._models import WorkflowSpec

# The generated output (workflow cheatsheet, tables, panels) contains → • — and box-drawing
# characters. On a legacy Windows console (cp1252) Rich would crash encoding them, so force UTF-8.
if sys.platform == "win32":  # pragma: no cover
    for _stream in (sys.stdout, sys.stderr):
        if isinstance(_stream, io.TextIOWrapper):
            _stream.reconfigure(encoding="utf-8", errors="replace")


class LazyGroup(NamedTuple):
    """A command group the root builds on first use: its name, the module and attribute that
    hold its Typer, and its summary line."""

    name: str
    module: str
    attr: str
    help: str


#: The root's command groups, in the order ``sq --help`` lists them. A group's module is
#: imported, and its Typer converted, only when the group is looked up.
LAZY_GROUPS: tuple[LazyGroup, ...] = (
    LazyGroup("create", "squads._cli._create", "create_app", "Create a tracked item."),
    LazyGroup("role", "squads._cli._role", "role_app", "Manage agent roles."),
    LazyGroup("dev", "squads._cli._dev", "dev_app", "Manage developer roles."),
    LazyGroup("operator", "squads._cli._operator", "operator_app", "Manage human operators."),
    LazyGroup("skill", "squads._cli._skill", "skill_app", "Manage agent skills."),
    LazyGroup(
        "memory", "squads._cli._memory", "memory_app", "Read and write a role's memory notebook."
    ),
    LazyGroup(
        "board",
        "squads._cli._board",
        "board_app",
        "Post, list and take down notices on the team board.",
    ),
    LazyGroup(
        "migrate",
        "squads._cli._migrate",
        "migrate_app",
        "Run schema migrations and read their steps.",
    ),
    LazyGroup(
        "override",
        "squads._cli._override",
        "override_app",
        "Manage project-level template and role overrides.",
    ),
    LazyGroup(
        "workflow",
        "squads._cli._workflow_cmd",
        "workflow_app",
        "Show the team workflow and the active spec's vocabulary.",
    ),
)


def _group_command(sub: typer.Typer, name: str, **options: Any) -> Any:
    """The Click group *sub* makes under *name*, as ``add_typer`` with *options* would register
    it."""
    host = typer.Typer(add_completion=False)
    host.add_typer(sub, name=name, **options)
    return typer.main.get_command(host).commands[name]  # type: ignore[attr-defined]


class _LazyCommands(MutableMapping[str, _click.Command]):
    """The root group's commands: the ones registered up front, and the lazy ones, each built
    when first read. Names keep one order whether or not a command has been built."""

    def __init__(
        self,
        eager: MutableMapping[str, _click.Command],
        lazy: dict[str, Callable[[], _click.Command]],
    ) -> None:
        self._built: dict[str, _click.Command] = dict(eager)
        self._builders = lazy
        self._names: dict[str, None] = dict.fromkeys([*eager, *lazy])

    def __getitem__(self, name: str) -> _click.Command:
        if name not in self._built:
            if name not in self._builders:
                raise KeyError(name)
            self._built[name] = self._builders[name]()
        return self._built[name]

    def __setitem__(self, name: str, command: _click.Command) -> None:
        self._built[name] = command
        self._names[name] = None

    def __delitem__(self, name: str) -> None:
        del self._names[name]
        self._built.pop(name, None)
        self._builders.pop(name, None)

    def __iter__(self) -> Iterator[str]:
        return iter(self._names)

    def __len__(self) -> int:
        return len(self._names)


class _CustomTypeGroup(typer.core.TyperGroup):
    """Root TyperGroup that builds item sub-apps for custom work types on demand.

    Built-in commands and bundled types are looked up through the root's command table, built
    from the bundled spec on first use. An unknown name is resolved
    against the active spec and, if it is a declared custom type, gets a ``build_item_app``
    sub-app; ``list_commands`` lists those types in ``sq --help``. Spec-resolution errors fall
    back to the built-in set, so the built-in ``--help`` and ``get_command`` path never raise.
    """

    # Lazily-built custom-type Click commands, keyed by canonical type and the spec they were
    # built from, so repeated ``get_command`` calls (e.g. during completion introspection)
    # return the same command and another squad's spec never reuses it.
    _custom_cmd_cache: ClassVar[common.SpecKeyedCache[_click.Command]] = common.SpecKeyedCache()

    def __init__(self, **attrs: Any) -> None:
        super().__init__(**attrs)
        self.commands = _LazyCommands(self.commands, _lazy_builders())

    @staticmethod
    def _resolve_spec_for_ctx(ctx: Any) -> Any:
        """Resolve the spec for this Click context (never raises).

        Shared with ``_CustomCreateGroup``.
        """
        return common.resolve_spec_for_ctx(ctx)

    def format_help(self, ctx: Any, formatter: Any) -> None:
        """Rebuild the root epilog from the resolved spec (the built one is the bundled spec's).

        Both ``--help`` and bare ``sq`` render through this method, so refreshing here covers them.
        """
        self.epilog = root_epilog(self._resolve_spec_for_ctx(ctx))
        super().format_help(ctx, formatter)

    def _dropped_static_names_for_ctx(self, ctx: Any) -> frozenset[str]:
        """Static command and alias names whose built-in type the active spec dropped.

        ``get_command`` does not consult this set: a dropped type name must still dispatch so the
        read path's own "unknown item type" refusal answers, not Click's did-you-mean. Stale aliases
        are included because ``get_command`` refuses them and a listed one would be suggested back.
        Any spec-resolution error returns the empty set.
        """
        try:
            spec = self._resolve_spec_for_ctx(ctx)
        except Exception:  # pylint: disable=broad-except
            return frozenset()
        dropped: set[str] = set(common.stale_static_aliases(spec))
        for name in _STATIC_TYPES:
            if name not in spec.items:
                dropped.add(name)
                dropped.update(_spec.items[name].aliases)
        return frozenset(dropped)

    def _custom_non_roster_types_for_ctx(self, ctx: Any) -> frozenset[str]:
        """Non-roster types the resolved spec adds beyond _STATIC_TYPES (empty on error)."""
        try:
            spec = self._resolve_spec_for_ctx(ctx)
            return frozenset(t for t in spec.non_roster_types() if t not in _STATIC_TYPES)
        except Exception:  # pylint: disable=broad-except
            return frozenset()

    def list_commands(self, ctx: Any) -> list[str]:
        """Built-in commands first, then custom non-roster types sorted by name."""
        dropped = self._dropped_static_names_for_ctx(ctx)
        base: list[str] = [c for c in super().list_commands(ctx) if c not in dropped]
        custom = sorted(self._custom_non_roster_types_for_ctx(ctx))
        # Custom types are never in the built-in set, so no dedup is needed.
        return base + custom

    def get_command(self, ctx: Any, cmd_name: str) -> _click.Command | None:
        # The table lists every bundled alias whatever the active spec says, so one the spec no
        # longer declares must be refused here (see `common.static_alias_is_stale`).
        retargeted = common.retargeted_type(ctx, cmd_name)
        if retargeted is None and common.static_alias_is_stale(ctx, cmd_name):
            return common.stale_alias_command(ctx, cmd_name)

        # Fast path: the root's command table, which builds a bundled command on first lookup.
        cmd = super().get_command(ctx, cmd_name) if retargeted is None else None
        if cmd is not None:
            return cmd

        # Errors resolving the spec are swallowed so `sq --help` degrades gracefully: either
        # `canonical` is a declared custom non-roster type, or Click answers "No such command".
        # A known-failed override instead gets `common.spec_error_command`'s accurate refusal.
        try:
            from squads._cli._items import build_item_app

            if retargeted is None and cmd_name in _STATIC_TYPES:
                # Bundled types are always in the command table; if we're here,
                # it's genuinely unknown (shouldn't happen, but guard so we never shadow them).
                return None

            spec = self._resolve_spec_for_ctx(ctx)

            # Resolve the canonical type name: check direct type name first, then
            # spec's alias_to_type map (covers custom aliases like "inc" → "incident").
            canonical = retargeted or cmd_name
            if retargeted is None and cmd_name not in spec.non_roster_types():
                # Check if it's an alias for a custom type.
                resolved = spec.alias_to_type.get(cmd_name)
                if resolved is not None and resolved in spec.non_roster_types():
                    canonical = resolved
                else:
                    # Not a custom type or alias — fall through to Click's "No such command" error.
                    return common.spec_error_command(cmd_name, ctx)
        except Exception:  # pylint: disable=broad-except
            # Spec resolution failed (e.g. corrupt override, path error) — degrade gracefully.
            return common.spec_error_command(cmd_name, ctx)

        # `canonical` is a declared custom type, so build errors propagate rather than
        # becoming "No such command".
        cached = self._custom_cmd_cache.get(canonical, spec)
        if cached is None:
            # Build from the spec resolved above: on a cold first dispatch the root callback
            # has not bound the active spec yet, so `common.get_active_spec()` is the bundled one.
            type_app = build_item_app(canonical, spec=spec)
            # Give the app a name so help output uses it.
            type_app.info.name = canonical
            cached = self._custom_cmd_cache.put(canonical, spec, typer.main.get_command(type_app))
        return cached


def _alias_summary(spec: WorkflowSpec) -> str:
    """``"e/f/t/b/d/r/g, feat/dec/rev"``-shaped summary of every non-roster type's aliases,
    single-letter ones grouped first — the parenthesized clause in :func:`root_epilog`.
    Type order matches the resource-group registration loop below (``ItemSpec.order``, type
    name breaking ties), so the summary's own left-to-right order is stable and spec-derived,
    not a hand-maintained list. Empty groups are dropped rather than rendered as ``", "``."""
    types = sorted(spec.non_roster_types(), key=lambda t: (spec.items[t].order, t))
    shorts = [a for t in types for a in spec.items[t].aliases if len(a) == 1]
    longs = [a for t in types for a in spec.items[t].aliases if len(a) != 1]
    groups = [g for g in ("/".join(shorts), "/".join(longs)) if g]
    return ", ".join(groups)


def root_epilog(spec: WorkflowSpec) -> str:
    """Root ``--help`` epilog text, with the alias-set clause derived from *spec* rather than
    a fixed literal — see ``_CustomTypeGroup.format_help`` for why this is called again at
    render time, not just once at ``app = typer.Typer(...)`` construction below."""
    alias_summary = _alias_summary(spec)
    aliases_clause = f" ({alias_summary})" if alias_summary else ""
    return (
        "Team workflow: `sq workflow`  ·  full docs offline: `sq docs`  ·  "
        "per-command help: `sq <command> --help`\n\n"
        f"Type-command aliases{aliases_clause} are hidden from this list "
        "but fully supported — see the alias table in `sq workflow`."
    )


app = typer.Typer(
    name="sq",
    help=(
        "Track a team of AI agents' work: IDs, roles, lifecycles and handoffs.\n\n"
        "New here? Run `sq workflow` for how the team works, `sq docs` to read the\n"
        "full docs offline, or `sq <command> --help` for details."
    ),
    epilog=root_epilog(bundled_spec()),
    no_args_is_help=True,
    add_completion=True,
    cls=_CustomTypeGroup,
)


def _version_cb(value: bool):
    if value:
        common.console.print(version_line())
        raise typer.Exit()


def _resolve_clock_override(at: str | None, prior: RequestContext) -> datetime | None:
    """``--at`` forges the clock; without it the ambient override carries forward.

    Carrying it forward lets a frozen clock survive several invocations in one process; every
    other context field is reset per invocation.
    """
    if at is None:
        return prior.clock_override
    from squads import _clock

    try:
        return _clock.parse_iso(at)
    except ValueError:
        common.err_console.print(
            f"[red]error:[/red] invalid --at timestamp {at!r} "
            "(use ISO 8601, e.g. 2024-01-15 or 2024-01-15T09:30:00Z)",
            soft_wrap=True,
        )
        raise typer.Exit(2) from None


@app.callback()
def main_callback(
    ctx: typer.Context,
    change_dir: list[str] = typer.Option(
        [],
        "-C",
        help="Run as if sq was started in PATH (repeatable; relative to the previous -C).",
        metavar="path",
        callback=common.check_change_dir,
        is_eager=True,
    ),
    removed_dir: str | None = typer.Option(
        None, "--dir", hidden=True, callback=common.refuse_dir_option
    ),
    at: str | None = typer.Option(
        None,
        "--at",
        help="Record this ISO 8601 UTC time instead of now, to bring in past history.",
        metavar="when",
    ),
    version: bool = typer.Option(
        False, "--version", callback=_version_cb, is_eager=True, help="Show version and exit."
    ),
):
    spans.mark("startup")
    with spans.span("root_callback"):
        _bind_request(ctx, change_dir, at)


def _bind_request(ctx: typer.Context, change_dir: list[str], at: str | None) -> None:
    from squads._context import NoticeLog, bind_context, get_context

    # Bind one fresh RequestContext per invocation, from -C/--at plus the clock that
    # `_resolve_clock_override` carries forward; the request's own starting directory and
    # documents pass through, and the consoles and the API are chosen here.
    prior = get_context()
    session_id, parent_session_id = actor.session_from_env()
    client_cwd = common.effective_dir(change_dir)
    active_spec, spec_error = common.bind_active_spec(client_cwd)
    bind_context(
        RequestContext(
            clock_override=_resolve_clock_override(at, prior),
            session_id=session_id,
            parent_session_id=parent_session_id,
            active_spec=active_spec,
            client_cwd=client_cwd,
            client_cwd_chosen=bool(change_dir),
            spec_error=spec_error,
            start_dir=prior.start_dir,
            documents=prior.documents,
            consoles=common.build_consoles(),
            api=calls.select_api(),
            notices=NoticeLog(sink=common.print_notice),
        )
    )
    common.mark_root_callback_ran(ctx)


# Register commands (imported after `app` is defined; they decorate it). `_main` is a side-effect
# import — its `@app.command()`s attach the top-level commands but it's never referenced by name.
from squads._cli import _import as _import  # noqa: E402
from squads._cli import _items  # noqa: E402
from squads._cli import _main as _main  # noqa: E402
from squads._cli import _ui as _ui  # noqa: E402

# Resource-oriented item groups: `sq <type> <num> <verb> …`, one sub-app per bundled type,
# available under its canonical name and hidden aliases. Types an override adds are not in
# the bundled spec at import time; `_CustomTypeGroup.get_command` builds them on demand.
_spec = bundled_spec()
# Order is ItemSpec.order (type name breaking ties; a missing order sorts last), so neither the
# TOML table order nor an override can reorder `sq --help`.
_STATIC_TYPES: list[str] = sorted(_spec.non_roster_types(), key=lambda t: (_spec.items[t].order, t))


def _lazy_builders() -> dict[str, Callable[[], _click.Command]]:
    """Each lazy command's name, in listing order, with the call that builds it; a type and its
    aliases share the one app built for this root."""
    builders: dict[str, Callable[[], _click.Command]] = {}
    apps: dict[str, typer.Typer] = {}
    for group in LAZY_GROUPS:
        builders[group.name] = functools.partial(_build_group, group)
    for item_type in _STATIC_TYPES:
        builders[item_type] = functools.partial(_build_type_group, apps, item_type, item_type)
        for alias in _spec.items[item_type].aliases:
            builders[alias] = functools.partial(_build_type_group, apps, item_type, alias)
    return builders


def _build_type_group(apps: dict[str, typer.Typer], item_type: str, name: str) -> _click.Command:
    """``sq <type>`` under *name*: the type's own name, or a hidden alias of it."""
    if item_type not in apps:
        apps[item_type] = _items.build_item_app(item_type, spec=bundled_spec())
    if name == item_type:
        return _group_command(apps[item_type], name, help=common.type_group_help(item_type))
    return _group_command(apps[item_type], name, hidden=True)


def _build_group(group: LazyGroup) -> _click.Command:
    sub: typer.Typer = getattr(importlib.import_module(group.module), group.attr)
    return _group_command(sub, group.name, help=group.help)


# Global value-options live on the group callback, so Click only parses them *before* the
# subcommand. Hoist them so `sq create … --at <when>` works the same as `sq --at <when> create …`.
_GLOBAL_VALUE_OPTS = ("--at", "--dir")


def _hoist_global_options(args: list[str]) -> list[str]:
    """Move global value-options (--at/--dir, + their value) to the front, wherever they appear.

    Safe because no subcommand defines these names and option *values* use the ``--opt=value``
    form. A token that is the value of the option before it, or follows ``--``, is not an
    option and stays where it is. A trailing ``--dir`` with no value is hoisted as ``--dir=``
    so it reaches the same refusal.
    """
    hoisted: list[str] = []
    rest: list[str] = []
    previous = ""
    i = 0
    while i < len(args):
        tok = args[i]
        if tok == "--":
            rest += args[i:]
            break
        candidate = tok in _GLOBAL_VALUE_OPTS or tok.startswith(("--at=", "--dir="))
        if candidate and previous.startswith("-") and previous in common.value_options():
            rest.append(tok)
            previous = ""
            i += 1
            continue
        if tok in _GLOBAL_VALUE_OPTS and i + 1 < len(args):
            hoisted += [tok, args[i + 1]]
            previous = ""
            i += 2
        elif tok == "--dir":
            hoisted.append("--dir=")
            previous = ""
            i += 1
        elif tok.startswith(("--at=", "--dir=")):
            hoisted.append(tok)
            previous = ""
            i += 1
        else:
            rest.append(tok)
            previous = tok
            i += 1
    return hoisted + rest


def _exit_code(code: object) -> int:
    """The exit code a ``SystemExit`` carries, read as the interpreter would at exit."""
    if code is None:
        return 0
    if isinstance(code, int):
        return code
    print(code, file=sys.stderr)
    return 1


def _run_in_scope(args: list[str]) -> int:
    try:
        app(args=_hoist_global_options(args))
    except SystemExit as exc:
        return _exit_code(exc.code)
    return 0


def run(argv: Sequence[str]) -> int:
    """Run one command line (the arguments after ``sq``) and return its exit code.

    The command runs in a copy of the current context, so nothing it binds (clock, actor,
    index read, consoles) is visible to the next call.
    """
    return contextvars.copy_context().run(_run_in_scope, list(argv))


def main() -> None:
    """Console-script entry point: run the process's arguments and exit with the code.

    The imports are done by now: the collector (off since the launcher started) comes back on
    with their object graph set aside, so the command's own collections skip it.
    """
    gc.freeze()
    gc.enable()
    code = run(sys.argv[1:])
    spans.mark("end")
    # Output is out before the interpreter tears the object graph down; freezing it keeps the
    # shutdown collections from walking it.
    with contextlib.suppress(OSError, ValueError):
        sys.stdout.flush()
        sys.stderr.flush()
    gc.freeze()
    sys.exit(code)
