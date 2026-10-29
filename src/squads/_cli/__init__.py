"""The Typer application, exposed as both `squads` and `sq`."""

import contextvars
import io
import sys
from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime
from typing import Any, ClassVar

import typer
import typer._click as _click  # underscore is upstream's own private module path, not ours
import typer.core
import typer.main

from squads import _actor as actor
from squads import version_line
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


class _CustomTypeGroup(typer.core.TyperGroup):
    """Root TyperGroup that builds item sub-apps for custom work types on demand.

    Built-in commands are registered statically at import time. An unknown name is resolved
    against the active spec and, if it is a declared custom type, gets a ``build_item_app``
    sub-app; ``list_commands`` lists those types in ``sq --help``. Spec-resolution errors fall
    back to the built-in set, so the built-in ``--help`` and ``get_command`` path never raise.
    """

    # Lazily-built custom-type Click commands, keyed by canonical type and the spec they were
    # built from, so repeated ``get_command`` calls (e.g. during completion introspection)
    # return the same command and another squad's spec never reuses it.
    _custom_cmd_cache: ClassVar[common.SpecKeyedCache[_click.Command]] = common.SpecKeyedCache()

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
        # The static table binds every bundled alias at import time, so one the active spec no
        # longer declares must be refused here (see `common.static_alias_is_stale`).
        if common.static_alias_is_stale(ctx, cmd_name):
            return common.stale_alias_command(ctx, cmd_name)

        # Fast path: try the statically-built command table first.
        cmd = super().get_command(ctx, cmd_name)
        if cmd is not None:
            return cmd

        # Errors resolving the spec are swallowed so `sq --help` degrades gracefully: either
        # `canonical` is a declared custom non-roster type, or Click answers "No such command".
        # A known-failed override instead gets `common.spec_error_command`'s accurate refusal.
        try:
            from squads._cli._items import build_item_app

            if cmd_name in _STATIC_TYPES:
                # Statically-registered types are always in the static table; if we're here,
                # it's genuinely unknown (shouldn't happen, but guard so we never shadow them).
                return None

            spec = self._resolve_spec_for_ctx(ctx)

            # Resolve the canonical type name: check direct type name first, then
            # spec's alias_to_type map (covers custom aliases like "inc" → "incident").
            canonical = cmd_name
            if cmd_name not in spec.non_roster_types():
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
        metavar="PATH",
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
        metavar="WHEN",
    ),
    version: bool = typer.Option(
        False, "--version", callback=_version_cb, is_eager=True, help="Show version and exit."
    ),
):
    from squads._context import bind_context, get_context

    # Bind one fresh RequestContext per invocation, from -C/--at plus the clock that
    # `_resolve_clock_override` carries forward; the request's own starting directory,
    # attachments, terminal and documents pass through, and the consoles are built here.
    prior = get_context()
    session_id, parent_session_id = actor.session_from_env()
    client_cwd = common.effective_dir(change_dir)
    active_spec, spec_error = common.bind_active_spec(client_cwd)
    bind_context(
        RequestContext(
            clock_override=_resolve_clock_override(at, prior),
            actor_override="system",
            session_id=session_id,
            parent_session_id=parent_session_id,
            active_spec=active_spec,
            client_cwd=client_cwd,
            client_cwd_chosen=bool(change_dir),
            spec_error=spec_error,
            start_dir=prior.start_dir,
            attachments=prior.attachments,
            terminal=prior.terminal,
            documents=prior.documents,
            consoles=common.build_consoles(prior.terminal),
        )
    )
    common.mark_root_callback_ran(ctx)
    common.require_current_schema(ctx.invoked_subcommand)
    common.working_language_notice()


# Register commands (imported after `app` is defined; they decorate it). `_main` is a side-effect
# import — its `@app.command()`s attach the top-level commands but it's never referenced by name.
from squads._cli import (  # noqa: E402
    _board,
    _create,
    _dev,
    _items,
    _memory,
    _migrate,
    _operator,
    _override,
    _role,
    _skill,
    _workflow_cmd,
)
from squads._cli import _import as _import  # noqa: E402
from squads._cli import _main as _main  # noqa: E402
from squads._cli import _ui as _ui  # noqa: E402

app.add_typer(_create.create_app, name="create", help="Create a tracked item.")
app.add_typer(_role.role_app, name="role", help="Manage agent roles.")
app.add_typer(_dev.dev_app, name="dev", help="Manage developer roles.")
app.add_typer(_operator.operator_app, name="operator", help="Manage human operators.")
app.add_typer(_skill.skill_app, name="skill", help="Manage agent skills.")
app.add_typer(
    _memory.memory_app,
    name="memory",
    help="Read and write a role's memory notebook.",
)
app.add_typer(
    _board.board_app,
    name="board",
    help="Post, list and take down notices on the team board.",
)
app.add_typer(
    _migrate.migrate_app, name="migrate", help="Run schema migrations and read their steps."
)
app.add_typer(
    _override.override_app,
    name="override",
    help="Manage project-level template and role overrides.",
)
app.add_typer(
    _workflow_cmd.workflow_app,
    name="workflow",
    help="Show the team workflow and the active spec's vocabulary.",
)

# Resource-oriented item groups: `sq <type> <num> <verb> …`, one sub-app per bundled type,
# registered under its canonical name and hidden aliases. Types an override adds are not in
# the bundled spec at import time; `_CustomTypeGroup.get_command` builds them lazily.
_spec = bundled_spec()
# Registration order is ItemSpec.order (type name breaking ties; a missing order sorts last),
# so neither the TOML table order nor an override can reorder `sq --help`.
_STATIC_TYPES: list[str] = sorted(_spec.non_roster_types(), key=lambda t: (_spec.items[t].order, t))

for _type_str in _STATIC_TYPES:
    _type_app = _items.build_item_app(_type_str)
    app.add_typer(
        _type_app,
        name=_type_str,
        help=common.type_group_help(_type_str),
    )
    # Aliases come from the spec's ItemSpec.aliases — the single source of truth.
    for _alias in _spec.items[_type_str].aliases:
        app.add_typer(_type_app, name=_alias, hidden=True)

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


def _run_in_scope(args: list[str], seed: RequestContext | None) -> int:
    if seed is not None:
        from squads._context import bind_context, get_context

        bind_context(
            replace(
                get_context(),
                start_dir=seed.start_dir,
                attachments=seed.attachments,
                terminal=seed.terminal,
                documents=seed.documents,
            )
        )
    try:
        app(args=_hoist_global_options(args))
    except SystemExit as exc:
        return _exit_code(exc.code)
    return 0


def run(argv: Sequence[str], *, seed: RequestContext | None = None) -> int:
    """Run one command line (the arguments after ``sq``) and return its exit code.

    The command runs in a copy of the current context, so nothing it binds (clock, actor,
    index read, consoles) is visible to the next call. *seed* carries a request's starting
    directory, attachments, terminal facts and documents. A prompt in a request that has no
    terminal raises :class:`~squads._errors.NeedsTerminal`.
    """
    return contextvars.copy_context().run(_run_in_scope, list(argv), seed)


def main() -> None:
    """Console-script entry point: run the process's arguments and exit with the code."""
    sys.exit(run(sys.argv[1:]))
