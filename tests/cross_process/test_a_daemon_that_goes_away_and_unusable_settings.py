"""An unusable daemon setting is said once and the command runs locally; a daemon that goes away
mid-session is started again for the next call, or the call runs locally with one line saying why.

Each case runs the real `sq` console script or a client process against a scratch squad and a
runtime directory of its own.
"""

import json
import pathlib
import subprocess
import sys

import pytest

from squads._daemon_start import failure_line
from squads._endpoint import Endpoint, endpoint_for, runtime_dir_problem
from squads._paths import SquadPaths
from tests.cross_process._sq import env, run, sq_command

#: A client that holds one API for a whole session, as `sq ui` does: it calls, has the daemon
#: stopped, optionally makes a restart impossible, and calls again.
SESSION = """\
import asyncio, json, pathlib, subprocess, sys
from squads._api import _ops as ops
from squads._api._dto._workflow import CatalogRequest
from squads._cli._calls import SelectedApi

root, sq, spoil = sys.argv[1], sys.argv[2], sys.argv[3]
api = SelectedApi(pathlib.Path(root))

def pid():
    command = [sq, "-C", root, "daemon", "status", "--json"]
    status = json.loads(subprocess.run(command, capture_output=True, text=True).stdout)
    return status["daemon"]["pid"] if status["running"] else None

asyncio.run(api.call(ops.WORKFLOW_TYPES, CatalogRequest()))
first = pid()
subprocess.run([sq, "-C", root, "daemon", "stop"], capture_output=True)
if spoil != "-":
    pathlib.Path(spoil).chmod(0o755)
answer = asyncio.run(api.call(ops.WORKFLOW_TYPES, CatalogRequest()))
print(json.dumps({"first": first, "second": pid(), "types": len(answer.data.items)}))
"""


def remote(project: SquadPaths, *args: str, setting: str | None = None):
    environment = {**env(), "SQUADS_DAEMON": setting or "on"}
    return subprocess.run(
        sq_command(project, *args), capture_output=True, text=True, env=environment, check=False
    )


@pytest.fixture
def endpoint(project: SquadPaths, daemon_runtime) -> Endpoint:
    found = endpoint_for(project.root)
    assert found is not None
    return found


def test_an_unusable_squads_daemon_is_said_once_and_the_command_runs_locally(project) -> None:
    result = remote(project, "list", "--json", setting="maybe")

    assert (result.returncode, [i["type"] for i in json.loads(result.stdout)]) == (0, ["role"])
    assert result.stderr == (
        "warning: SQUADS_DAEMON must be on or off, got 'maybe'; every command runs in local "
        "mode until it is fixed\n"
    )


def test_an_unusable_daemon_table_is_said_once_and_the_command_runs_locally(project) -> None:
    config = project.config_path
    config.write_text(config.read_text() + '\n[daemon]\nenabled = "yes"\n', encoding="utf-8")

    result = remote(project, "list", "--json")

    assert result.returncode == 0
    assert result.stderr == (
        "warning: [daemon] enabled must be true or false, got 'yes'; every command runs in "
        "local mode until it is fixed\n"
    )


def _session(project: SquadPaths, spoil: str) -> subprocess.CompletedProcess[str]:
    script = sq_command(project)[0]
    return subprocess.run(
        [sys.executable, "-I", "-c", SESSION, str(project.root), script, spoil],
        capture_output=True,
        text=True,
        env={**env(), "SQUADS_DAEMON": "on"},
        check=False,
    )


@pytest.mark.skipif(sys.platform == "win32", reason="the spoiled runtime directory is a POSIX mode")
def test_a_daemon_stopped_mid_session_is_started_again_for_the_next_call(project, endpoint) -> None:
    try:
        result = _session(project, "-")
        assert (result.returncode, result.stderr) == (0, "")
        answered = json.loads(result.stdout)
        assert answered["types"] > 0
        assert answered["second"] is not None
        assert answered["second"] != answered["first"]
    finally:
        run(sq_command(project, "daemon", "stop"))


@pytest.mark.skipif(sys.platform == "win32", reason="the spoiled runtime directory is a POSIX mode")
def test_a_daemon_stopped_mid_session_that_cannot_be_restarted_says_why_and_answers_locally(
    project, endpoint
) -> None:
    result = _session(project, str(endpoint.runtime_dir))

    pathlib.Path(endpoint.runtime_dir).chmod(0o700)
    reason = runtime_dir_problem(endpoint)
    assert reason is None
    spoiled = f"{endpoint.runtime_dir} is accessible to other users (mode 0755)"
    assert (result.returncode, result.stderr) == (0, failure_line(spoiled) + "\n")
    answered = json.loads(result.stdout)
    assert (answered["second"], answered["types"] > 0) == (None, True)
