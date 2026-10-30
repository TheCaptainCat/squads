"""When the shim has sent nothing a daemon ran, the command runs in its own process: after a
connection the daemon refuses, after a daemon that went away between the two phases of a prompt,
and for the commands that are never sent to one.

Each case runs the real `sq` console script against a scratch squad and a runtime directory of its
own.
"""

import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Iterator

import pytest

from squads._daemon_start import ensure, failure_line
from squads._endpoint import Endpoint, endpoint_for, runtime_dir_problem
from squads._paths import SquadPaths
from tests.cross_process._fake_daemon import SilentDaemon
from tests.cross_process._sq import env, run, sq_command

PROMPT = b"[y/N]"


def remote_env() -> dict[str, str]:
    return {**env(), "SQUADS_DAEMON": "on"}


def local(project: SquadPaths, *args: str) -> subprocess.CompletedProcess[str]:
    """A command with the daemon switched off, for the setup and the checks of a case."""
    return subprocess.run(
        sq_command(project, *args),
        capture_output=True,
        text=True,
        env={**env(), "SQUADS_DAEMON": "off"},
        check=False,
    )


@pytest.fixture
def endpoint(project: SquadPaths, daemon_runtime) -> Iterator[Endpoint]:
    """The endpoint of the scratch squad; any daemon a case started is stopped at the end."""
    found = endpoint_for(project.root)
    assert found is not None
    yield found
    run(sq_command(project, "daemon", "stop"))


@pytest.mark.skipif(sys.platform == "win32", reason="the spoiled runtime directory is a POSIX mode")
def test_a_refused_connection_runs_the_command_locally(
    project: SquadPaths, endpoint: Endpoint
) -> None:
    endpoint.runtime_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
    stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    stale.bind(str(endpoint.files.socket))  # a socket file nothing listens on
    stale.close()

    result = subprocess.run(
        sq_command(project, "list", "--json"),
        capture_output=True,
        text=True,
        env=remote_env(),
        check=False,
    )

    spoiled = f"{endpoint.runtime_dir} is accessible to other users (mode 0755)"
    assert (result.returncode, result.stderr) == (0, failure_line(spoiled) + "\n")
    assert [item["type"] for item in json.loads(result.stdout)] == ["role"]


class Screen:
    """What a process has written to its stdout so far, read on a thread of its own."""

    def __init__(self, process: subprocess.Popen[bytes]) -> None:
        self.text = b""
        self.prompted = threading.Event()
        self._thread = threading.Thread(target=self._read, args=(process,), daemon=True)
        self._thread.start()

    def _read(self, process: subprocess.Popen[bytes]) -> None:
        assert process.stdout is not None
        while chunk := os.read(process.stdout.fileno(), 4096):
            self.text += chunk
            if PROMPT in self.text:
                self.prompted.set()

    def finish(self) -> bytes:
        self._thread.join(30)
        return self.text


def comments_of(project: SquadPaths, number: int) -> list[str]:
    listed = local(project, "task", str(number), "comments", "--json")
    return [entry["body"] for entry in json.loads(listed.stdout)]


def refused(endpoint: Endpoint) -> bool:
    """Whether connecting to the daemon's socket is refused."""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
        try:
            probe.connect(str(endpoint.files.socket))
        except OSError:
            return True
    return False


@pytest.mark.skipif(sys.platform == "win32", reason="the daemon's socket is a Unix one")
def test_a_daemon_killed_between_the_two_phases_of_a_prompt_is_asked_again_locally(
    project: SquadPaths, endpoint: Endpoint
) -> None:
    number = json.loads(
        local(project, "create", "task", "Prompted", "--author", "manager", "--json").stdout
    )["sequence_id"]
    local(project, "task", str(number), "comment", "--as", "manager", "-m", "Kept until confirmed")
    short = json.loads(local(project, "task", str(number), "comments", "--json").stdout)[0][
        "short_hash"
    ]
    assert ensure(endpoint) is None
    status = json.loads(run(sq_command(project, "daemon", "status", "--json")).stdout)

    process = subprocess.Popen(
        sq_command(project, "task", str(number), "comment", short, "remove", "--as", "manager"),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=remote_env(),
    )
    screen = Screen(process)
    assert screen.prompted.wait(30), "the command never asked"
    assert comments_of(project, number) == ["- Kept until confirmed"]  # nothing written yet
    os.kill(status["daemon"]["pid"], signal.SIGKILL)
    deadline = time.monotonic() + 15
    while not refused(endpoint):
        assert time.monotonic() < deadline, "the daemon did not go"
        time.sleep(0.05)

    assert process.stdin is not None
    process.stdin.write(b"y\ny\n")  # the first reaches the shim, the second the local run
    process.stdin.close()
    code = process.wait(timeout=60)
    shown = screen.finish()
    assert process.stderr is not None
    assert (code, process.stderr.read(), shown.count(PROMPT)) == (0, b"", 2)
    assert comments_of(project, number) == []


def test_the_local_only_commands_are_never_sent_to_a_daemon(
    project: SquadPaths, endpoint: Endpoint
) -> None:
    assert runtime_dir_problem(endpoint) is None
    silent = SilentDaemon(endpoint)
    codes: dict[str, int] = {}
    try:
        for command in (
            ["daemon", "status", "--json"],
            ["init", "--help"],
            ["adopt", "--help"],
            ["ui", "--help"],
        ):
            result = subprocess.run(
                sq_command(project, *command),
                capture_output=True,
                text=True,
                env=remote_env(),
                timeout=30,
                check=False,
            )
            codes[command[0]] = result.returncode
    finally:
        silent.close()

    assert (codes, silent.requests) == ({"daemon": 0, "init": 0, "adopt": 0, "ui": 0}, 0)


def test_a_daemon_that_retires_runs_nothing_and_the_command_runs_locally(
    project: SquadPaths, endpoint: Endpoint
) -> None:
    assert ensure(endpoint) is None
    config = project.config_path
    config.write_text(config.read_text(encoding="utf-8") + "\n# edited\n", encoding="utf-8")

    result = subprocess.run(
        sq_command(project, "list", "--json"),
        capture_output=True,
        text=True,
        env=remote_env(),
        check=False,
    )

    assert (result.returncode, result.stderr) == (0, "")
    assert [item["type"] for item in json.loads(result.stdout)] == ["role"]


def _ctrl_c_at_the_prompt(project: SquadPaths, daemon: str, *argv: str) -> tuple[int, bytes]:
    """The exit code and whole terminal output of *argv* on a pseudo-terminal it owns, interrupted
    once it asks."""
    import pty

    command = sq_command(project, *argv)
    pid, master = pty.fork()
    if pid == 0:  # pragma: no cover
        os.execve(command[0], command, {**env(), "SQUADS_DAEMON": daemon, "TERM": "xterm"})
    shown = b""
    while PROMPT + b": " not in shown:  # the whole prompt, trailing space included
        shown += os.read(master, 4096)
    os.write(master, b"\x03")
    try:
        while chunk := os.read(master, 4096):
            shown += chunk
    except OSError:  # the terminal closes with the process
        pass
    os.close(master)
    _, status = os.waitpid(pid, 0)
    # the terminal's echo of the key may land either side of the program's last write
    return os.waitstatus_to_exitcode(status), shown.replace(b"^C", b"")


@pytest.mark.skipif(sys.platform == "win32", reason="the terminal is a Unix pseudo-terminal")
@pytest.mark.filterwarnings("ignore:This process:DeprecationWarning")
def test_ctrl_c_at_a_prompt_reads_as_it_does_locally(
    project: SquadPaths, endpoint: Endpoint
) -> None:
    number = json.loads(
        local(project, "create", "task", "Prompted", "--author", "manager", "--json").stdout
    )["sequence_id"]
    local(project, "task", str(number), "comment", "--as", "manager", "-m", "Kept")
    short = json.loads(local(project, "task", str(number), "comments", "--json").stdout)[0][
        "short_hash"
    ]
    remove = ("task", str(number), "comment", short, "remove", "--as", "manager")

    here = _ctrl_c_at_the_prompt(project, "off", *remove)
    served = _ctrl_c_at_the_prompt(project, "on", *remove)

    assert served == here
    assert here[0] == 1
    assert comments_of(project, number) == ["- Kept"]
