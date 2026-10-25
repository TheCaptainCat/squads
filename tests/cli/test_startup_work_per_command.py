"""What one invocation does before its command runs: how often it reads the workflow override,
how many times it builds the Click command tree, and what it imports.

Every row runs the real entry point in a fresh interpreter and counts with spies on the
resolution and the tree build; timings are never asserted.
"""

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from squads import __version__, version_line
from squads._rendering._engine import invalidate_squad_dir

pytestmark = pytest.mark.anyio

_OVERRIDE = '[items.feature]\naliases = ["feat", "f", "ft"]\n'
_BROKEN_OVERRIDE = "[items.feature\n"

#: Runs the entry point with the argv in ``$1`` and prints what the invocation did as JSON. A spy
#: on the resolution imports the workflow package, so the import row runs without spies.
_PROBE = """\
import json, sys
argv, spied = json.loads(sys.argv[1]), json.loads(sys.argv[2])
sys.argv = ["sq", *argv]
seen = {"disk_reads": 0, "override_loads": 0, "tree_builds": 0}


def counting(owner, name, key):
    original = getattr(owner, name)

    def spy(*args, **kwargs):
        seen[key] += 1
        return original(*args, **kwargs)

    setattr(owner, name, spy)


if spied:
    import typer.main
    from squads._cli import _common
    from squads._workflow import _loader

    counting(typer.main, "get_command", "tree_builds")
    counting(_common, "_read_spec_from_disk", "disk_reads")
    counting(_loader, "load_workflow_spec", "override_loads")
from squads.__main__ import main

try:
    main()
    seen["exit"] = 0
except SystemExit as stop:
    seen["exit"] = stop.code or 0
heavy = ("squads._cli", "squads._workflow", "squads._services")
seen["modules"] = sorted(m for m in heavy if m in sys.modules)
sys.stderr.write(json.dumps(seen))
"""


@dataclass(frozen=True)
class _Row:
    squad: str  # plain, override, broken or none
    argv: tuple[str, ...]
    counts: tuple[int, int, int] | None  # disk reads, override loads, tree builds
    twin: tuple[str, ...] | None = None  # an argv that must print exactly what argv prints
    exit_code: int = 0


_SHOW = ("task", "{task}", "show")

_ROWS = {
    "bare --version imports no cli": _Row("plain", ("--version",), None),
    "--version after -C prints the same line": _Row(
        "plain", ("--version",), None, twin=("-C", ".", "--version")
    ),
    "--help in a customised squad": _Row("override", ("--help",), (1, 1, 1)),
    "--help with a broken override": _Row("broken", ("--help",), (1, 1, 1)),
    "--help outside a squad": _Row("none", ("--help",), (1, 0, 1)),
    "task show": _Row("override", _SHOW, (0, 1, 1)),
    "task show with a trailing --at": _Row("override", (*_SHOW, "--at", "2026-01-01"), (0, 1, 1)),
    "task show with a leading --at": _Row("override", ("--at", "2026-01-01", *_SHOW), (0, 1, 1)),
}


def _write_override(squad_dir: Path, body: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{body}", encoding="utf-8"
    )
    invalidate_squad_dir(squad_dir)


def _run(cwd: Path, argv: tuple[str, ...], *, spied: bool) -> tuple[str, dict[str, object]]:
    done = subprocess.run(
        [sys.executable, "-c", _PROBE, json.dumps(argv), json.dumps(spied)],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    seen = json.loads(done.stderr[done.stderr.rindex("{") :])
    return done.stdout, seen


@pytest.mark.parametrize("name", list(_ROWS))
async def test_startup_work_per_command(
    name: str, project, invoke, tmp_path_factory: pytest.TempPathFactory
) -> None:
    row = _ROWS[name]
    created = await invoke(["create", "task", "Probe", "--author", "manager"])
    number = re.search(r"TASK-(\d+)", created.output)
    assert number is not None, created.output
    if row.squad != "plain":
        _write_override(project.squad_dir, _BROKEN_OVERRIDE if row.squad == "broken" else _OVERRIDE)
    cwd = tmp_path_factory.mktemp("bare") if row.squad == "none" else project.root
    argv = tuple(token.format(task=number.group(1)) for token in row.argv)

    out, seen = _run(cwd, argv, spied=row.counts is not None)

    assert seen["exit"] == row.exit_code, seen
    if row.counts is None:
        assert seen["modules"] == []
        assert out.splitlines() == [version_line()]
    else:
        assert (seen["disk_reads"], seen["override_loads"], seen["tree_builds"]) == row.counts
    if row.twin is not None:
        twin_out, _ = _run(cwd, row.twin, spied=False)
        assert twin_out == out
