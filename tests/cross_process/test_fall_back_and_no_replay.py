"""When the daemon cannot be had a command runs locally and says why, and the next command tries
again; when a daemon takes a request and the connection is lost, the command fails and sends nothing
twice.

Each case runs the real `sq` console script against a scratch squad and a runtime directory of its
own.
"""

import json
import pathlib
import subprocess

import pytest

from squads._daemon_start import failure_line
from squads._endpoint import Endpoint, endpoint_for, runtime_dir_problem
from squads._paths import SquadPaths
from tests.cross_process._fake_daemon import SilentDaemon
from tests.cross_process._sq import env, run, sq_command


def remote(project: SquadPaths, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        sq_command(project, *args),
        capture_output=True,
        text=True,
        env={**env(), "SQUADS_DAEMON": "on"},
        check=False,
    )


@pytest.fixture
def endpoint(project: SquadPaths, daemon_runtime) -> Endpoint:
    found = endpoint_for(project.root)
    assert found is not None
    return found


def test_an_unusable_runtime_directory_runs_the_command_locally_and_the_next_tries_again(
    project: SquadPaths, endpoint: Endpoint
) -> None:
    endpoint.runtime_dir.mkdir(mode=0o755, exist_ok=True)
    pathlib.Path(endpoint.runtime_dir).chmod(0o755)
    reason = runtime_dir_problem(endpoint)
    assert reason is not None
    try:
        first = remote(project, "list", "--json")
        assert (first.returncode, first.stderr) == (0, failure_line(reason) + "\n")
        assert [item["type"] for item in json.loads(first.stdout)] == ["role"]

        pathlib.Path(endpoint.runtime_dir).chmod(0o700)
        second = remote(project, "list", "--json")
        assert (second.returncode, second.stdout, second.stderr) == (0, first.stdout, "")
        status = run(sq_command(project, "daemon", "status", "--json"))
        assert json.loads(status.stdout)["running"] is True
    finally:
        run(sq_command(project, "daemon", "stop"))


def test_a_connection_lost_after_the_request_was_sent_is_an_error_and_is_not_replayed(
    project: SquadPaths, endpoint: Endpoint
) -> None:
    assert runtime_dir_problem(endpoint) is None
    daemon = SilentDaemon(endpoint.files.socket, hang_up=True)
    try:
        result = remote(project, "create", "task", "Never twice", "--author", "manager")
    finally:
        daemon.close()
    assert (result.returncode, result.stdout) == (1, "")
    assert result.stderr == (
        f"error: the connection to the squad served at {endpoint.files.socket} was lost after "
        "the request was sent (Remote end closed connection without response); the operation "
        "may still complete. Check its result before running it again.\n"
    )
    assert daemon.requests == 1
    listed = run(sq_command(project, "list", "--type", "task", "--json"))
    assert json.loads(listed.stdout) == []
