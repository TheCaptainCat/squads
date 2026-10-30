"""The shim's transport where the daemon listens on a loopback port: it asks the process on the
recorded port who it is before it sends the command line, and sends it only to the daemon the
record names."""

import json
import os
from pathlib import Path

import pytest

from squads import _shim as shim
from squads._endpoint import Endpoint, endpoint_for
from squads._paths import SquadPaths
from tests._daemon_harness import Served


def _port_endpoint(project: SquadPaths, served: Served, runtime: Path, *, pid: int) -> Endpoint:
    """The endpoint the squad has where daemons listen on a port, with a record naming *pid* as
    the daemon on *served*'s port."""
    environ = {"LOCALAPPDATA": str(runtime), "SQUADS_DAEMON": "on"}
    endpoint = endpoint_for(project.root, environ=environ, platform="win32", version="test")
    assert endpoint is not None
    endpoint.runtime_dir.mkdir(parents=True)
    record = {
        "pid": pid,
        "version": "test",
        "squad_dir": str(endpoint.squad_dir),
        "listeners": [
            {"transport": "tcp", "address": f"{served.host}:{served.port}", "kind": "cli"}
        ],
    }
    endpoint.files.info.write_text(json.dumps(record), encoding="utf-8")
    return endpoint


def _list_request(project: SquadPaths) -> dict[str, object]:
    return shim.build_request(
        ["list", "--json"],
        cwd=str(project.root),
        client_dir=str(project.root),
        attachments={},
        terminal=shim.terminal_facts(),
        environ={},
        prog_name="sq",
    )


def test_a_command_is_sent_to_the_daemon_the_record_names(
    project: SquadPaths, serve, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    endpoint = _port_endpoint(project, serve(project), tmp_path / "local", pid=os.getpid())

    code = shim.Session(endpoint, _list_request(project), None).run()

    shown = capsys.readouterr()
    assert (code, shown.err) == (0, "")
    assert [item["type"] for item in json.loads(shown.out)] == ["role"]


def test_a_command_is_not_sent_to_a_process_that_is_not_the_recorded_daemon(
    project: SquadPaths, serve, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    endpoint = _port_endpoint(project, serve(project), tmp_path / "local", pid=os.getpid() + 1)

    with pytest.raises(shim.Fallback):
        shim.Session(endpoint, _list_request(project), None).run()

    assert capsys.readouterr().out == ""
