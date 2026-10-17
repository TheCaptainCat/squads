"""One squad holding every roster shape, built once per module and copied per test.

The shapes a roster verb must be checked against: a bundled skill, a generated per-type
skill, a system skill whose view the project dropped, a project skill, a bundled role, a
bundled role with a per-slug override, a templated developer, a declared developer, a project
role, a retired role, an operator and a retired operator. ``restore`` copies the built squad
into a test's own directory, so a destructive verb never sees another test's leftovers.
"""

import asyncio
import os
import shutil
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from typer.testing import CliRunner

from squads import __version__
from squads._cli import app
from squads._context import bind_context as bind
from squads._context import get_context
from squads._rendering._engine import invalidate_squad_dir
from squads._services import _service as service

#: shape -> (entity kind, slug)
SHAPES: dict[str, tuple[str, str]] = {
    "bundled skill": ("skill", "squads"),
    "generated skill": ("skill", "sq-task"),
    "system skill with its view dropped": ("skill", "greeting"),
    "project skill": ("skill", "release-runbook"),
    "bundled role": ("role", "manager"),
    "bundled role with an override": ("role", "architect"),
    "templated developer": ("role", "rust-dev"),
    "declared developer": ("role", "auditor-dev"),
    "project role": ("role", "security-analyst"),
    "retired role": ("role", "devops"),
    "operator": ("operator", "op-ada"),
    "retired operator": ("operator", "op-old"),
}

_ROLE_FILE = (
    'full_name = "{name}"\ntitle = "{slug}"\n'
    'description = "A declared role."\nmission = "A declared role."\n'
)

#: Drops the greeting skill's view from `[selected]`, so that skill is no longer generated.
_WORKFLOW = """\
[selected]
views = ["milestone_rollup", "role_definition", "squads_skill", "memory_skill", "item_skill"]
"""

FROZEN = datetime(2026, 6, 7, 10, 0, 0, tzinfo=UTC)


def _override(squad_dir: Path, name: str, text: str) -> None:
    path = squad_dir / ".overrides" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# squads:override-base:{__version__}\n{text}", encoding="utf-8")


def build(root: Path) -> Path:
    """Build the every-shape squad at *root* (which must exist and be empty); return it."""
    previous = Path.cwd()
    prior_context = get_context()
    bind(replace(prior_context, clock_override=FROZEN))
    os.chdir(root)
    try:
        paths = asyncio.run(service.init(root=root, roles_spec="all")).paths
        squad_dir = paths.squad_dir
        runner = CliRunner()

        def run(*args: str) -> None:
            invalidate_squad_dir(squad_dir)
            result = runner.invoke(app, list(args))
            assert result.exit_code == 0, (args, result.output)

        run("dev", "add", "--tech", "rust")
        _override(
            squad_dir,
            "roles/auditor-dev.toml",
            _ROLE_FILE.format(name="Auditor", slug="auditor-dev") + 'capabilities = ["dev"]\n',
        )
        _override(
            squad_dir,
            "roles/security-analyst.toml",
            _ROLE_FILE.format(name="Sentinel", slug="security-analyst"),
        )
        _override(squad_dir, "roles/architect.toml", 'full_name = "Renamed Architect"\n')
        run("role", "activate", "auditor-dev")
        run("role", "activate", "security-analyst")
        run("role", "devops", "status", "Archived")
        run("skill", "add", "Release Runbook", "--desc", "Ship a release.")
        run("operator", "add", "Ada Lovelace", "--slug", "op-ada")
        run("operator", "add", "Old Hand", "--slug", "op-old")
        run("operator", "op-old", "status", "Archived")
        _override(squad_dir, "workflow.toml", _WORKFLOW)
        run("skill", "greeting", "view", "disable", "greeting_skill")
        run("sync")
        return root
    finally:
        os.chdir(previous)
        bind(prior_context)


def restore(template: Path, dest: Path) -> Path:
    """Copy the built squad to *dest* (a fresh directory) and return it."""
    shutil.copytree(template, dest, symlinks=True)
    return dest
