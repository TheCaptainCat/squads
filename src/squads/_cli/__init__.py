"""The Typer application, exposed as both `squads` and `sq`."""

import typer

from squads import __version__
from squads._cli import _common as common

app = typer.Typer(
    name="sq",
    help=(
        "Manage a team of AI agents: bootstrap roles & skills, track work with stable IDs.\n\n"
        "New here? Run `sq workflow` for how the team works, or `sq <command> --help` for details."
    ),
    epilog="Team workflow: `sq workflow`  ·  per-command help: `sq <command> --help`",
    no_args_is_help=True,
    add_completion=False,
)


def _version_cb(value: bool):
    if value:
        common.console.print(f"squads {__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
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
    common.version_notice()


# Register commands (imported after `app` is defined; they decorate it).
from squads._cli import (  # noqa: E402
    _comment,
    _create,
    _dev,
    _main,
    _refs,
    _role,
    _skill,
)

app.add_typer(_create.create_app, name="create", help="Create a tracked item.")
app.add_typer(_role.role_app, name="role", help="Manage agent roles.")
app.add_typer(_comment.story_app, name="story", help="Manage a feature's user stories.")
app.add_typer(_comment.subtask_app, name="subtask", help="Manage a task's subtasks.")
app.add_typer(_refs.ref_app, name="ref", help="Manage reference edges.")
app.add_typer(_dev.dev_app, name="dev", help="Manage developer roles.")
app.add_typer(_skill.skill_app, name="skill", help="Manage agent skills.")
app.add_typer(_main.guide_app, name="guide", help="Manage project guides.")
