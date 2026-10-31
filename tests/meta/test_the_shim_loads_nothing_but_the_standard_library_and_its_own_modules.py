"""Repo-hygiene gate: the shim loads no `squads` module beyond a few, no third-party package and
none of `dataclasses`, `typing`, `importlib.metadata`, on a live path (a read, a stdin attachment,
a confirmed prompt, a command with no deadline) and on a cold start. Not run: the error and
Ctrl-C handlers, the local fall back and the Windows-only branches."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from squads._daemon_link import wait_until_gone
from squads._daemon_start import ensure
from squads._endpoint import endpoint_for
from squads._paths import SquadPaths
from tests.cross_process._sq import env, run, sq_command

#: The `squads` modules a command that reaches a daemon may load.
_LIVE = frozenset({"squads", "squads.__main__", "squads._shim", "squads._endpoint"})

#: Added when no daemon answers and the shim starts one.
_START = frozenset({"squads._daemon_start", "squads._daemon_link"})
_START_WINDOWS = frozenset({"squads._windows_owner"})

#: Modules whose import the shim's speed rules out.
_FORBIDDEN = frozenset({"dataclasses", "typing", "importlib.metadata"})

#: Not packages: the script itself and the virtual environment's start-up hook.
_ENVIRONMENT = frozenset({"__main__", "_virtualenv"})

#: Runs the entry point as the console script does, writing what it loaded when the process ends.
PROBE = """\
import atexit, json, sys
out = sys.argv[1]
atexit.register(lambda: open(out, "w").write(json.dumps(sorted(sys.modules))))
sys.argv = ["sq", *sys.argv[2:]]
from squads.__main__ import main
main()
"""


def _breaches(loaded: list[str], allowed: frozenset[str]) -> list[str]:
    found: list[str] = []
    for name in loaded:
        top = name.split(".")[0]
        if name in _FORBIDDEN:
            found.append(name)
        elif top == "squads":
            if name not in allowed:
                found.append(name)
        elif top not in sys.stdlib_module_names and top not in _ENVIRONMENT:
            found.append(name)
    return sorted(found)


def _loaded(
    project: SquadPaths, out: Path, argv: list[str] | None = None, stdin: str = ""
) -> list[str]:
    done = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            PROBE,
            str(out),
            "-C",
            str(project.root),
            *(argv or ["list", "--json"]),
        ],
        capture_output=True,
        text=True,
        input=stdin,
        env={**env(), "SQUADS_DAEMON": "on"},
        check=False,
    )
    assert (done.returncode, done.stderr) == (0, "")
    return json.loads(out.read_text(encoding="utf-8"))


def _setup(project: SquadPaths) -> tuple[str, str]:
    """A task with a comment, made without a daemon: its number and the comment's short hash."""
    created = run(sq_command(project, "create", "task", "Shapes", "--author", "manager", "--json"))
    number = str(json.loads(created.stdout)["sequence_id"])
    run(sq_command(project, "task", number, "comment", "--as", "manager", "-m", "Remove me"))
    listed = run(sq_command(project, "task", number, "comments", "--json"))
    return number, json.loads(listed.stdout)[0]["short_hash"]


@pytest.fixture
def stopped(project: SquadPaths, daemon_runtime):
    """Any daemon the case started is stopped at the end."""
    yield
    run(sq_command(project, "daemon", "stop"))
    endpoint = endpoint_for(project.root)
    assert endpoint is not None
    assert wait_until_gone(endpoint, 15)


def test_the_shim_on_the_way_to_a_live_daemon_loads_only_its_own_modules(
    project: SquadPaths, stopped, tmp_path: Path
) -> None:
    endpoint = endpoint_for(project.root)
    assert endpoint is not None
    assert ensure(endpoint) is None

    number, short = _setup(project)
    shapes = {
        "read": (["list", "--json"], ""),
        "a stdin attachment": (["task", number, "body", "--file", "-", "--force"], "From stdin\n"),
        "a confirmed prompt": (
            ["task", number, "comment", short, "remove", "--as", "manager"],
            "y\n",
        ),
        "no answer deadline": (["repair"], ""),
    }

    for name, (argv, stdin) in shapes.items():
        loaded = _loaded(project, tmp_path / "live.json", argv, stdin)
        assert (name, _breaches(loaded, _LIVE)) == (name, [])


def test_the_shim_that_starts_a_daemon_adds_only_the_start_modules(
    project: SquadPaths, stopped, tmp_path: Path
) -> None:
    allowed = _LIVE | _START | (_START_WINDOWS if sys.platform == "win32" else frozenset())

    assert _breaches(_loaded(project, tmp_path / "cold.json"), allowed) == []


def test_the_scan_names_what_it_finds() -> None:
    sample = ["squads._shim", "squads._cli", "typing", "yaml.parser", "json", "_virtualenv"]
    assert _breaches(sample, _LIVE) == ["squads._cli", "typing", "yaml.parser"]
