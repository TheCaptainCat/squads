"""An unusable daemon setting is said once and the command runs locally; a daemon that goes away
mid-session of the terminal UI's API is started again for the next call, or the call runs locally
with one line saying why.

Each case runs the real `sq` console script or a client process against a scratch squad and a
runtime directory of its own.
"""

import json
import pathlib
import subprocess
import sys
from collections.abc import Iterator

import pytest

from squads._daemon_start import failure_line
from squads._endpoint import Endpoint, endpoint_for
from squads._paths import SquadPaths
from tests.cross_process._sq import env, run, sq_command

#: A client that holds one API for a whole session and asks it to look for a daemon again before
#: each call, the way the terminal UI does. The mode says what happens to the daemon meanwhile.
SESSION = """\
import asyncio, json, pathlib, subprocess, sys
from squads._api import _ops as ops
from squads._api._dto._workflow import CatalogRequest
from squads._cli import _remote
from squads._cli._remote import SelectedApi

root, sq, mode, target = sys.argv[1:5]
prior = SelectedApi(pathlib.Path(root))

def call():
    prior.reselect()
    return len(asyncio.run(prior.call(ops.WORKFLOW_TYPES, CatalogRequest())).data.items)

def pid():
    command = [sq, "-C", root, "daemon", "status", "--json"]
    status = json.loads(subprocess.run(command, capture_output=True, text=True).stdout)
    return status["daemon"]["pid"] if status["running"] else None

def stop():
    subprocess.run([sq, "-C", root, "daemon", "stop"], capture_output=True)

first = None
if mode == "stuck":
    pathlib.Path(target).chmod(0o755)
    _remote.RETRY_AFTER = 0
    for _ in range(3):
        types = call()
elif mode == "backoff":
    from filelock import FileLock
    from squads._endpoint import endpoint_for
    pathlib.Path(target).chmod(0o755)
    call()
    pathlib.Path(target).chmod(0o700)
    lock = FileLock(str(endpoint_for(pathlib.Path(root)).files.lock))
    with lock:
        types = call()
elif mode == "recover":
    pathlib.Path(target).chmod(0o755)
    call(); call()
    pathlib.Path(target).chmod(0o700)
    _remote.RETRY_AFTER = 0
    types = call()
else:
    call()
    first = pid()
    stop()
    if mode == "chmod":
        pathlib.Path(target).chmod(0o755)
    elif mode == "disable":
        with open(target, "a") as config:
            config.write("\\n[daemon]\\nenabled = false\\n")
    for _ in range(3 if mode != "none" else 1):
        types = call()
print(json.dumps({"first": first, "second": pid(), "types": types}))
"""


def remote(project: SquadPaths, *args: str, setting: str | None = None):
    environment = {**env(), "SQUADS_DAEMON": setting or "on"}
    return subprocess.run(
        sq_command(project, *args), capture_output=True, text=True, env=environment, check=False
    )


@pytest.fixture
def endpoint(project: SquadPaths, daemon_runtime) -> Iterator[Endpoint]:
    """The endpoint of the scratch squad; any daemon a case started is stopped at the end."""
    found = endpoint_for(project.root)
    assert found is not None
    yield found
    run(sq_command(project, "daemon", "stop"))


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


def _session(project: SquadPaths, mode: str, target: str = "-") -> subprocess.CompletedProcess[str]:
    script = sq_command(project)[0]
    return subprocess.run(
        [sys.executable, "-I", "-c", SESSION, str(project.root), script, mode, target],
        capture_output=True,
        text=True,
        env={k: v for k, v in env().items() if k != "SQUADS_DAEMON"},  # the table decides
        check=False,
    )


def test_a_daemon_stopped_mid_session_is_started_again_for_the_next_call(project, endpoint) -> None:
    try:
        result = _session(project, "none")
        assert (result.returncode, result.stderr) == (0, "")
        answered = json.loads(result.stdout)
        assert answered["types"] > 0
        assert answered["second"] is not None
        assert answered["second"] != answered["first"]
    finally:
        run(sq_command(project, "daemon", "stop"))


@pytest.mark.skipif(sys.platform == "win32", reason="the spoiled runtime directory is a POSIX mode")
def test_a_daemon_stopped_mid_session_that_cannot_be_restarted_says_why_once(
    project, endpoint
) -> None:
    result = _session(project, "chmod", str(endpoint.runtime_dir))

    pathlib.Path(endpoint.runtime_dir).chmod(0o700)
    spoiled = f"{endpoint.runtime_dir} is accessible to other users (mode 0755)"
    # three calls after the stop, one line
    assert (result.returncode, result.stderr) == (0, failure_line(spoiled) + "\n")
    answered = json.loads(result.stdout)
    assert (answered["second"], answered["types"] > 0) == (None, True)


def test_a_daemon_switched_off_mid_session_is_not_started_again(project, endpoint) -> None:
    result = _session(project, "disable", str(project.config_path))

    assert (result.returncode, result.stderr) == (0, "")
    answered = json.loads(result.stdout)
    assert (answered["second"], answered["types"] > 0) == (None, True)


@pytest.mark.skipif(sys.platform == "win32", reason="the spoiled runtime directory is a POSIX mode")
def test_a_session_that_began_without_a_daemon_finds_one_once_it_can_be_started(
    project, endpoint
) -> None:
    endpoint.runtime_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
    try:
        result = _session(project, "recover", str(endpoint.runtime_dir))

        spoiled = f"{endpoint.runtime_dir} is accessible to other users (mode 0755)"
        # two calls while it cannot be started, one line; the third finds a daemon
        assert (result.returncode, result.stderr) == (0, failure_line(spoiled) + "\n")
        answered = json.loads(result.stdout)
        assert (answered["second"] is not None, answered["types"] > 0) == (True, True)
    finally:
        run(sq_command(project, "daemon", "stop"))


@pytest.mark.skipif(sys.platform == "win32", reason="the spoiled runtime directory is a POSIX mode")
def test_a_failed_start_is_said_once_however_often_it_is_tried(project, endpoint) -> None:
    endpoint.runtime_dir.mkdir(mode=0o755, parents=True, exist_ok=True)

    result = _session(project, "stuck", str(endpoint.runtime_dir))

    spoiled = f"{endpoint.runtime_dir} is accessible to other users (mode 0755)"
    assert (result.returncode, result.stderr) == (0, failure_line(spoiled) + "\n")


@pytest.mark.skipif(sys.platform == "win32", reason="the spoiled runtime directory is a POSIX mode")
def test_a_failed_start_is_not_tried_again_straight_away(project, endpoint) -> None:
    endpoint.runtime_dir.mkdir(mode=0o755, parents=True, exist_ok=True)

    result = _session(project, "backoff", str(endpoint.runtime_dir))

    # the second call would have started a daemon, found the lock held, waited and said another
    # reason; it answers locally and silently instead
    spoiled = f"{endpoint.runtime_dir} is accessible to other users (mode 0755)"
    assert (result.returncode, result.stderr) == (0, failure_line(spoiled) + "\n")
