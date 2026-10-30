"""The shim over a loopback port sends the command line only to the daemon the record names.

Each case runs the real entry point in a process of its own, with the endpoint resolved for a
platform that has ports (the one seam: Linux has none)."""

import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from squads._endpoint import Endpoint, endpoint_for
from squads._paths import SquadPaths
from tests._daemon_harness import Served
from tests.cross_process._fake_daemon import SilentDaemon
from tests.cross_process._sq import env, run, sq_command

#: Runs the entry point with the endpoint resolved for a platform whose daemons listen on a port.
PROBE = """\
import sys
import squads._shim as shim
resolve = shim.endpoint_for
shim.endpoint_for = lambda start: resolve(start, platform="win32")
sys.argv = ["sq", *sys.argv[1:]]
shim.main()
"""


@pytest.fixture
def endpoint(project: SquadPaths, daemon_runtime, tmp_path: Path) -> Iterator[Endpoint]:
    """The squad's endpoint where daemons listen on a port, with its runtime directory made; any
    daemon a case started on the platform's own transport is stopped at the end."""
    environ = {"LOCALAPPDATA": str(tmp_path / "local"), "SQUADS_DAEMON": "on"}
    found = endpoint_for(project.root, environ=environ, platform="win32")
    assert found is not None
    found.runtime_dir.mkdir(parents=True)
    yield found
    run(sq_command(project, "daemon", "stop"))


def _record(endpoint: Endpoint, port: str, *, pid: int) -> None:
    """The record naming *pid* as the daemon on *port*."""
    listener = {"transport": "tcp", "address": port, "kind": "cli"}
    record = {
        "pid": pid,
        "version": "test",
        "squad_dir": str(endpoint.squad_dir),
        "listeners": [listener],
    }
    endpoint.files.info.write_text(json.dumps(record), encoding="utf-8")


def _sq(project: SquadPaths, endpoint: Endpoint, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", "-c", PROBE, "-C", str(project.root), *args],
        capture_output=True,
        text=True,
        env={**env(), "SQUADS_DAEMON": "on", "LOCALAPPDATA": str(endpoint.runtime_dir.parent)},
        timeout=120,
        check=False,
    )


def test_a_command_is_sent_to_the_daemon_the_record_names(
    project: SquadPaths, serve, endpoint: Endpoint
) -> None:
    served: Served = serve(project)
    _record(endpoint, f"{served.host}:{served.port}", pid=os.getpid())

    result = _sq(project, endpoint, "list", "--json")

    assert (result.returncode, result.stderr) == (0, "")
    assert [item["type"] for item in json.loads(result.stdout)] == ["role"]


def test_a_command_is_not_sent_to_a_process_that_is_not_the_recorded_daemon(
    project: SquadPaths, endpoint: Endpoint
) -> None:
    impostor = SilentDaemon(endpoint)
    try:
        _record(
            endpoint,
            impostor.sock.getsockname()[0] + f":{impostor.sock.getsockname()[1]}",
            pid=os.getpid() + 1,
        )

        result = _sq(project, endpoint, "list", "--json")
    finally:
        impostor.close()

    assert impostor.requests == 0
    assert result.returncode == 0
    assert [item["type"] for item in json.loads(result.stdout)] == ["role"]


def test_a_connection_lost_after_the_request_was_sent_over_a_port_is_an_error(
    project: SquadPaths, endpoint: Endpoint
) -> None:
    # answers one connection at a time, and closes the one that carries the command line
    daemon = SilentDaemon(endpoint, hang_up=True)
    try:
        result = _sq(project, endpoint, "list", "--json")
    finally:
        daemon.close()

    assert (result.returncode, result.stdout) == (1, "")
    assert "was lost after the request was sent" in result.stderr
    assert daemon.requests == 1
