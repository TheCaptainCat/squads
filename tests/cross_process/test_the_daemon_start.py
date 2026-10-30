"""Starting a daemon and finding it again, with real processes: a first command on a cold key starts
one that outlives it, a second finds the same one, and a runtime directory that cannot hold the
daemon's files is a failed start that says why.

Each case runs the real `sq` console script against a scratch squad nested under the test's
directory and a runtime directory of its own.
"""

import contextlib
import json
import os
import signal
import subprocess
import sys
from collections.abc import Iterator
from typing import Any

import pytest

from squads._daemon_start import ensure
from squads._endpoint import Endpoint, endpoint_for
from squads._paths import SquadPaths
from tests.cross_process._sq import env, run, sq_command

#: Starts the daemon from a client process that then exits.
STARTER = """\
import sys
from pathlib import Path
from squads._daemon_start import ensure
from squads._endpoint import endpoint_for
endpoint = endpoint_for(Path(sys.argv[1]))
print(ensure(endpoint) or "started", flush=True)
"""


@pytest.fixture
def endpoint(project: SquadPaths, daemon_runtime) -> Iterator[Endpoint]:
    """The endpoint of the scratch squad; any daemon it started is stopped at the end."""
    found = endpoint_for(project.root)
    assert found is not None
    yield found
    run(sq_command(project, "daemon", "stop"))


def status(project: SquadPaths) -> dict[str, Any]:
    result = run(sq_command(project, "daemon", "status", "--json"))
    assert (result.returncode, result.stderr) == (0, "")
    return json.loads(result.stdout)


def test_a_first_command_on_a_cold_key_starts_a_daemon_that_status_reports(
    project, endpoint
) -> None:
    assert status(project) == {"running": False, "daemon": None}

    assert ensure(endpoint) is None

    reported = status(project)
    assert reported["running"] is True
    assert reported["daemon"]["pid"] != os.getpid()
    assert reported["daemon"]["squad_dir"] == str(endpoint.squad_dir)


def test_a_second_command_is_answered_by_the_daemon_the_first_started(project, endpoint) -> None:
    assert ensure(endpoint) is None
    first = status(project)["daemon"]["pid"]

    assert ensure(endpoint) is None

    assert status(project)["daemon"]["pid"] == first


def test_the_daemon_outlives_the_client_that_started_it_and_its_process_group(
    project, endpoint
) -> None:
    """The starter runs in a process group of its own, which is killed once it has reported."""
    starter = subprocess.Popen(
        [sys.executable, "-I", "-c", STARTER, str(project.root)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env(),
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        start_new_session=sys.platform != "win32",
    )
    out, err = starter.communicate(timeout=60)
    assert (starter.returncode, out, err) == (0, "started\n", "")
    if sys.platform != "win32":
        with contextlib.suppress(ProcessLookupError):
            os.killpg(starter.pid, signal.SIGKILL)

    assert status(project)["running"] is True


def test_a_daemon_that_cannot_load_the_vocabulary_is_a_failed_start_that_says_why(
    project, endpoint
) -> None:
    overrides = project.squad_dir / ".overrides"
    overrides.mkdir(exist_ok=True)
    (overrides / "workflow.toml").write_text("[[broken", encoding="utf-8")

    reason = ensure(endpoint)

    assert reason is not None
    assert reason.startswith("cannot load the workflow vocabulary: ")
    assert status(project) == {"running": False, "daemon": None}


@pytest.mark.skipif(sys.platform == "win32", reason="Windows has no owner-only directory mode")
def test_a_runtime_directory_open_to_others_is_a_failed_start_that_says_why(
    project, endpoint
) -> None:
    endpoint.runtime_dir.mkdir(parents=True, exist_ok=True)
    endpoint.runtime_dir.chmod(0o755)

    reason = ensure(endpoint)

    assert reason == f"{endpoint.runtime_dir} is accessible to other users (mode 0755)"
    assert status(project) == {"running": False, "daemon": None}
