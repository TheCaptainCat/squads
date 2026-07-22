"""The Typer application, exposed as both `squads` and `sq`."""

import io
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

import typer
import typer._click as _click  # underscore is upstream's own private module path, not ours
import typer.core
import typer.main

from squads import __version__
from squads import _actor as actor
from squads._cli import _common as common
from squads._context import RequestContext
from squads._workflow._models import WorkflowSpec

# The generated output (workflow cheatsheet, tables, panels) contains → • — and box-drawing
# characters. On a legacy Windows console (cp1252) Rich would crash encoding them, so force UTF-8.
if sys.platform == "win32":  # pragma: no cover
    for _stream in (sys.stdout, sys.stderr):
        if isinstance(_stream, io.TextIOWrapper):
            _stream.reconfigure(encoding="utf-8", errors="replace")


class _CustomTypeGroup(typer.core.TyperGroup):
    """Root TyperGroup with lazy-dispatch for custom work types.

    Built-in commands are registered statically at import time (unchanged, byte-identical
    to today for non-custom squads).  When Click calls ``get_command(ctx, name)`` for an
    *unknown* name, this group resolves the active spec (bound by ``_bind_active_spec`` in
    the root callback, or the bundled spec as fallback) and, if ``name`` is a custom work
    type declared in that spec, builds and returns a ``build_item_app(name)`` sub-app on
    the fly.

    ``list_commands(ctx)`` is also overridden so ``sq --help`` enumerates custom types from
    the resolved spec — while remaining byte-identical for non-custom squads because the
    resolved spec IS the bundled spec there.

    Fail-soft contract: any error during spec resolution falls back to the built-in set —
    the built-in --help and get_command path always work and never raise from this class.
    """

    # Cache lazily-built custom-type Click commands within a single process invocation so
    # repeated ``get_command`` calls (e.g. during completion introspection) return the same
    # Click command object.
    _custom_cmd_cache: ClassVar[dict[str, _click.Command]] = {}

    @staticmethod
    def _resolve_spec_for_ctx(ctx: Any) -> Any:
        """Resolve the WorkflowSpec for the current Click context.

        Tries three sources in order:
        1. The already-bound per-invocation spec (``common.get_active_spec()``).  This is
           set by ``_bind_active_spec`` in the root callback and is the fast path for
           subcommand dispatch (callback fires before subcommand resolution).
        2. ``ctx.params["dir"]`` — the hoisted ``--dir`` value parsed on the root group's
           params before the callback fires (covers the ``sq --help`` path).
        3. Fall back to ``common.get_active_spec()`` (which returns the bundled spec when
           no per-invocation spec is bound), so ``--help`` on a non-custom squad is
           byte-identical to today.

        Always returns a ``WorkflowSpec`` (never raises).
        """
        try:
            from squads._context import get_context
            from squads._workflow import bundled_spec
            from squads._workflow._loader import (
                WORKFLOW_OVERRIDE_FILENAME,
                load_workflow_spec,
                validate_against_index_fail_closed,
            )

            # If the per-invocation spec is already bound (i.e. callback has run), use it.
            active = get_context().active_spec
            if active is not None:
                return active

            # Try to read --dir from the context params (set by Click's arg parsing before
            # the callback fires — available on the root ctx during list_commands/get_command).
            dir_override: str | None = None
            if ctx is not None and hasattr(ctx, "params"):
                dir_override = ctx.params.get("dir")

            # Resolve the spec for the given dir (same logic as _bind_active_spec).
            from squads._paths import resolve

            sp = resolve(dir_override, client_cwd=get_context().client_cwd)
            override_path = sp.squad_dir / WORKFLOW_OVERRIDE_FILENAME
            if not override_path.is_file():
                return bundled_spec()
            merged = load_workflow_spec(squad_dir=sp.squad_dir)
            validate_against_index_fail_closed(merged, sp.squad_dir)
        except Exception:  # pylint: disable=broad-except
            return common.get_active_spec()
        else:
            return merged

    def _custom_non_roster_types_for_ctx(self, ctx: Any) -> frozenset[str]:
        """Return the set of custom creatable/trackable (non-roster) type names from the
        resolved spec.

        "Custom" here means "not already registered by the static import-time loop"
        (``_STATIC_TYPES``) — i.e. anything a project's own workflow override adds on top
        of the bundled spec. Safe to call at any time; returns the empty set on any error.
        """
        try:
            spec = self._resolve_spec_for_ctx(ctx)
            return frozenset(t for t in spec.non_roster_types() if t not in _STATIC_TYPES)
        except Exception:  # pylint: disable=broad-except
            return frozenset()

    def list_commands(self, ctx: Any) -> list[str]:
        """Built-in commands first, then custom non-roster types from the resolved spec.

        For a non-custom squad the resolved spec IS the bundled spec, so the output is
        byte-identical to today.  Custom types appear after the built-in set,
        sorted alphabetically for determinism.
        """
        base: list[str] = super().list_commands(ctx)
        custom = sorted(self._custom_non_roster_types_for_ctx(ctx))
        # Custom types are never in the built-in set, so no dedup is needed.
        return base + custom

    def get_command(self, ctx: Any, cmd_name: str) -> _click.Command | None:
        # Fast path: try the statically-built command table first.
        cmd = super().get_command(ctx, cmd_name)
        if cmd is not None:
            return cmd

        # Spec-resolution region: decide whether cmd_name is a known custom type or alias.
        # Errors here (invalid spec, path resolution failures, etc.) are swallowed so that
        # `sq --help` always degrades gracefully.  The only valid outcome of this block is
        # either (a) `canonical` resolved to a declared custom non-roster type, or (b) return
        # None to let Click emit "No such command".
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
                    return None
        except Exception:  # pylint: disable=broad-except
            # Spec resolution failed (e.g. corrupt override, path error) — degrade gracefully.
            return None

        # Past this point `canonical` IS a declared custom work type.  Build errors here
        # are genuine failures for a type the user declared (and that --help lists), so they
        # must propagate rather than silently become "No such command".
        if canonical not in self._custom_cmd_cache:
            # Build from the SAME resolved spec used above to decide `canonical` is a
            # declared custom type — not whatever `common.get_active_spec()` holds, which
            # on a cold first-in-process dispatch is still the bundled fallback (the root
            # callback that binds the real spec hasn't run yet at get_command() time).
            type_app = build_item_app(canonical, spec=spec)
            # Give the app a name so help output uses it.
            type_app.info.name = canonical
            # Convert the Typer app to a Click command group.
            click_cmd = typer.main.get_command(type_app)
            # Register spec-declared aliases into the cache so subsequent look-ups find
            # them without entering this branch again.
            type_aliases: list[str] = (
                spec.items[canonical].aliases if canonical in spec.items else []
            )
            self._custom_cmd_cache[canonical] = click_cmd
            for type_alias in type_aliases:
                self._custom_cmd_cache[type_alias] = click_cmd

        return self._custom_cmd_cache.get(cmd_name)


app = typer.Typer(
    name="sq",
    help=(
        "The coordination layer for a team of AI agents: stable IDs, roles & skills, "
        "a status lifecycle, and handoffs.\n\n"
        "New here? Run `sq workflow` for how the team works, `sq docs` to read the full docs "
        "offline, or `sq <command> --help` for details."
    ),
    epilog=(
        "Team workflow: `sq workflow`  ·  full docs offline: `sq docs`  ·  "
        "per-command help: `sq <command> --help`\n\n"
        "Type-command aliases (e/f/t/b/d/r/g, feat/dec/rev) are hidden from this list "
        "but fully supported — see the alias table in `sq workflow`."
    ),
    no_args_is_help=True,
    add_completion=True,
    cls=_CustomTypeGroup,
)


def _version_cb(value: bool):
    if value:
        common.console.print(f"squads {__version__}")
        raise typer.Exit()


def _bind_active_spec(dir_override: str | None, client_cwd: Path) -> WorkflowSpec | None:
    """Resolve the WorkflowSpec for this invocation (does not bind it — the caller does, as
    part of the single per-invocation ``RequestContext``).

    Resolves and merges the squad-level workflow override (if present) exactly as
    ``open_service`` does, so parse_type/parse_status and display helpers all see the
    same spec.  Fails soft to the bundled spec on any resolution error (outside a squad,
    invalid override) — returns ``None`` only when resolution itself raised, which
    ``get_active_spec()`` also treats as "use the bundled spec".

    ``client_cwd`` is threaded straight into ``resolve()`` — the same value the sibling
    ``_CustomTypeGroup._resolve_spec_for_ctx`` path uses (``get_context().client_cwd``) —
    so both spec-resolution paths agree on their resolution base rather than one of them
    silently falling back to ``resolve()``'s own ``Path.cwd()`` default.
    """
    try:
        from squads._paths import resolve
        from squads._workflow import bundled_spec
        from squads._workflow._loader import (
            WORKFLOW_OVERRIDE_FILENAME,
            load_workflow_spec,
            validate_against_index_fail_closed,
        )

        sp = resolve(dir_override, client_cwd=client_cwd)
        override_path = sp.squad_dir / WORKFLOW_OVERRIDE_FILENAME
        if not override_path.is_file():
            return bundled_spec()

        merged_spec = load_workflow_spec(squad_dir=sp.squad_dir)
        validate_against_index_fail_closed(merged_spec, sp.squad_dir)
    except Exception:  # pylint: disable=broad-except
        # Outside a squad, invalid override, etc. — fall back to bundled spec.
        return None
    else:
        return merged_spec


def _resolve_clock_override(at: str | None, prior: RequestContext) -> datetime | None:
    """Resolve the clock override for this invocation.

    ``--at`` forges the given timestamp. Absent it, the *ambient* value carries forward
    unchanged rather than being force-cleared: a fresh process already starts with no
    override, so one-shot CLI use is unaffected either way, but this is what lets a
    forged/frozen clock (the test suite's ``frozen_time`` fixture, or a future daemon
    session) survive several invocations in one process without repeating ``--at`` on
    every one of them — the actor/session/spec/dir fields below ARE force-reset every
    invocation; the clock is the one field this edge deliberately inherits.
    """
    if at is None:
        return prior.clock_override
    from squads import _clock

    try:
        return _clock.parse_iso(at)
    except ValueError:
        common.err_console.print(
            f"[red]error:[/red] invalid --at timestamp {at!r} "
            "(use ISO 8601, e.g. 2024-01-15 or 2024-01-15T09:30:00Z)"
        )
        raise typer.Exit(2) from None


@app.callback()
def main_callback(
    ctx: typer.Context,
    dir: str | None = typer.Option(
        None,
        "--dir",
        help="Operate on the squad folder at PATH (overrides config/walk-up).",
        metavar="PATH",
    ),
    at: str | None = typer.Option(
        None,
        "--at",
        help="Forge timestamps for this command (ISO 8601, UTC) — for migrating history.",
        metavar="WHEN",
    ),
    version: bool = typer.Option(
        False, "--version", callback=_version_cb, is_eager=True, help="Show version and exit."
    ),
):
    from squads._context import bind_context, get_context

    # The CLI edge: bind ONE fresh RequestContext per invocation, assembled from this
    # invocation's inputs (--dir/--at) plus the ambient values that carry forward
    # (see _resolve_clock_override). Not a hybrid of separate set_*() mutations against
    # whatever the previous invocation left behind — every field is freshly computed here.
    prior = get_context()
    session_id, parent_session_id = actor.session_from_env()
    client_cwd = Path.cwd()
    bind_context(
        RequestContext(
            clock_override=_resolve_clock_override(at, prior),
            actor_override="system",
            session_id=session_id,
            parent_session_id=parent_session_id,
            active_spec=_bind_active_spec(dir, client_cwd),
            active_dir=dir,
            client_cwd=client_cwd,
        )
    )
    common.require_current_schema(ctx.invoked_subcommand)
    common.version_notice()


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
from squads._cli import _main as _main  # noqa: E402
from squads._cli import _ui as _ui  # noqa: E402
from squads._workflow import bundled_spec  # noqa: E402

app.add_typer(_create.create_app, name="create", help="Create a tracked item.")
app.add_typer(_role.role_app, name="role", help="Manage agent roles.")
app.add_typer(_dev.dev_app, name="dev", help="Manage developer roles.")
app.add_typer(_operator.operator_app, name="operator", help="Manage human operators.")
app.add_typer(_skill.skill_app, name="skill", help="Manage agent skills.")
app.add_typer(
    _memory.memory_app,
    name="memory",
    help="A role's committed memory notebook (list/search/show/add/forget).",
)
app.add_typer(
    _board.board_app,
    name="board",
    help="The team bulletin board (post/list/clear).",
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
    help="Workflow cheatsheet and spec validation (`sq workflow lint`).",
)

# Resource-oriented item groups: `sq <type> <num> <verb> …`.
# Build one sub-app per type declared in the BUNDLED spec — built-in and (bundled-declared)
# custom alike go through this one loop, then register each under its canonical name and any
# hidden aliases so every alias routes to the identical command tree.
#
# The bundled spec is the source of truth for the STATIC (import-time) registration loop —
# this gives byte-identical --help output for non-custom squads.  Types added later by
# a project's own .overrides/workflow.toml (not present in the bundled spec at import time,
# so impossible to register statically) are handled lazily by _CustomTypeGroup.get_command,
# which fires AFTER --dir is resolved and the active spec is bound.
_spec = bundled_spec()
# Deterministic registration order: each type's explicit ItemSpec.order (ascending), the
# type-name string breaking ties. This is an explicit, documented ordering key — independent
# of default_workflow.toml's own [items.*] table order — so neither a reshuffle of the
# bundled TOML nor a project override can silently reorder `sq --help`. A type that omits
# `order` defaults to +inf (see ItemSpec.order) and sorts after every bundled type.
_STATIC_TYPES: list[str] = sorted(_spec.non_roster_types(), key=lambda t: (_spec.items[t].order, t))

for _type_str in _STATIC_TYPES:
    _type_app = _items.build_item_app(_type_str)
    app.add_typer(
        _type_app,
        name=_type_str,
        help=f"Operate on a {_type_str} by number.",
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
    form, so a bare ``--at``/``--dir`` token is always the global option.
    """
    hoisted: list[str] = []
    rest: list[str] = []
    i = 0
    while i < len(args):
        tok = args[i]
        if tok in _GLOBAL_VALUE_OPTS and i + 1 < len(args):
            hoisted += [tok, args[i + 1]]
            i += 2
        elif tok.startswith(("--at=", "--dir=")):
            hoisted.append(tok)
            i += 1
        else:
            rest.append(tok)
            i += 1
    return hoisted + rest


def main() -> None:
    """Console-script entry point: make --at/--dir position-independent, then run the app."""
    sys.argv[1:] = _hoist_global_options(sys.argv[1:])
    app()
