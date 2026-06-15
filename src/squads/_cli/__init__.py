"""The Typer application, exposed as both `squads` and `sq`."""

import io
import sys

import typer

from squads import __version__
from squads import _actor as actor
from squads._cli import _common as common

# The generated output (workflow cheatsheet, tables, panels) contains → • — and box-drawing
# characters. On a legacy Windows console (cp1252) Rich would crash encoding them, so force UTF-8.
if sys.platform == "win32":  # pragma: no cover
    for _stream in (sys.stdout, sys.stderr):
        if isinstance(_stream, io.TextIOWrapper):
            _stream.reconfigure(encoding="utf-8", errors="replace")

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
)


def _version_cb(value: bool):
    if value:
        common.console.print(f"squads {__version__}")
        raise typer.Exit()


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
    common.set_active_dir(dir)
    common.apply_timestamp(at)
    # Set the ambient actor to "system" for this invocation; commands that know the
    # acting identity (e.g. `comment --as`, `create --author`) may override this via
    # actor.set_actor() before the mutation.  This unconditional re-set at callback start
    # is what prevents actor state from leaking across invocations — the same mechanism
    # apply_timestamp uses for the clock (no try/finally needed).
    actor.set_actor("system")
    common.require_current_schema(ctx.invoked_subcommand)
    common.version_notice()


# Register commands (imported after `app` is defined; they decorate it). `_main` is a side-effect
# import — its `@app.command()`s attach the top-level commands but it's never referenced by name.
from squads._cli import (  # noqa: E402
    _create,
    _dev,
    _items,
    _migrate,
    _operator,
    _override,
    _role,
    _skill,
)
from squads._cli import _main as _main  # noqa: E402
from squads._models._enums import TYPE_ALIASES, WORK_TYPES  # noqa: E402

app.add_typer(_create.create_app, name="create", help="Create a tracked item.")
app.add_typer(_role.role_app, name="role", help="Manage agent roles.")
app.add_typer(_dev.dev_app, name="dev", help="Manage developer roles.")
app.add_typer(_operator.operator_app, name="operator", help="Manage human operators.")
app.add_typer(_skill.skill_app, name="skill", help="Manage agent skills.")
app.add_typer(
    _migrate.migrate_app, name="migrate", help="Run schema migrations and read their steps."
)
app.add_typer(
    _override.override_app,
    name="override",
    help="Manage project-level template and role overrides.",
)

# Resource-oriented item groups: `sq <type> <num> <verb> …`.
# Build each type's sub-app once, then register it under its canonical name and
# any hidden aliases so every alias routes to the identical command tree.
for _type in WORK_TYPES:
    _type_app = _items.build_item_app(_type)
    app.add_typer(
        _type_app,
        name=_type.value,
        help=f"Operate on a {_type.value} by number.",
    )
    for _alias in TYPE_ALIASES.get(_type, ()):
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
