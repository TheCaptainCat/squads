"""Repo-hygiene gate: the CLI's shim, run as the console script runs it, loads no `squads` module
beyond the few it is allowed, no third-party package, and none of `dataclasses`, `typing` or
`importlib.metadata`, on the way to a live daemon and on a cold start that ends with one."""

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


def _loaded(project: SquadPaths, out: Path) -> list[str]:
    done = subprocess.run(
        [sys.executable, "-I", "-c", PROBE, str(out), "-C", str(project.root), "list", "--json"],
        capture_output=True,
        text=True,
        env={**env(), "SQUADS_DAEMON": "on"},
        check=False,
    )
    assert (done.returncode, done.stderr) == (0, "")
    assert json.loads(done.stdout)
    return json.loads(out.read_text(encoding="utf-8"))


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

    assert _breaches(_loaded(project, tmp_path / "live.json"), _LIVE) == []


def test_the_shim_that_starts_a_daemon_adds_only_the_start_modules(
    project: SquadPaths, stopped, tmp_path: Path
) -> None:
    allowed = _LIVE | _START | (_START_WINDOWS if sys.platform == "win32" else frozenset())

    assert _breaches(_loaded(project, tmp_path / "cold.json"), allowed) == []


def test_the_scan_names_what_it_finds() -> None:
    sample = ["squads._shim", "squads._cli", "typing", "yaml.parser", "json", "_virtualenv"]
    assert _breaches(sample, _LIVE) == ["squads._cli", "typing", "yaml.parser"]
