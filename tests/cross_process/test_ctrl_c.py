"""Ctrl-C while the client waits for the daemon: one SIGINT ends the wait at once, says the
operation may still complete, and exits 130; the daemon runs a started operation to the end.

Each case runs the real `sq` console script against a scratch squad and a runtime directory of its
own, and sends exactly one SIGINT.
"""

import json
import signal
import subprocess
import sys
import time
from collections.abc import Iterator

import pytest
from filelock import FileLock

from squads._cli._remote import endpoint_name
from squads._endpoint import Endpoint, endpoint_for, runtime_dir_problem
from squads._paths import SquadPaths
from tests.cross_process._fake_daemon import SilentDaemon
from tests.cross_process._sq import env, run, sq_command

#: Delivers CTRL_C_EVENT on Windows, which has no signal to send a process: it attaches to the
#: console the process owns, ignores the event itself and raises it for every process there.
CTRL_C = """\
import ctypes, sys
kernel = ctypes.windll.kernel32
kernel.FreeConsole()
if not kernel.AttachConsole(int(sys.argv[1])):
    sys.exit(2)
kernel.SetConsoleCtrlHandler(None, True)
kernel.GenerateConsoleCtrlEvent(0, 0)
"""

#: A process that has a console of its own, so a Ctrl-C raised there reaches it alone.
NEW_CONSOLE = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)


def remote_env() -> dict[str, str]:
    return {**env(), "SQUADS_DAEMON": "on"}


def interrupted(endpoint: Endpoint) -> str:
    """What the client prints when Ctrl-C ends its wait."""
    return (
        f"error: no answer from the squad served at {endpoint_name(endpoint)}; "
        "the operation may still complete. Check its result before running it again.\n"
    )


@pytest.fixture
def endpoint(project: SquadPaths, daemon_runtime) -> Iterator[Endpoint]:
    found = endpoint_for(project.root)
    assert found is not None
    yield found
    run(sq_command(project, "daemon", "stop"))


def one_sigint(process: subprocess.Popen[str], within: float) -> tuple[int, str, str]:
    """Send exactly one SIGINT and collect the process's exit and output."""
    started = time.monotonic()
    if sys.platform == "win32":
        subprocess.run([sys.executable, "-I", "-c", CTRL_C, str(process.pid)], check=True)
    else:
        process.send_signal(signal.SIGINT)
    out, err = process.communicate(timeout=within)
    assert time.monotonic() - started < within
    return process.returncode, out, err


def test_one_ctrl_c_ends_the_wait_for_a_daemon_that_never_answers(
    project: SquadPaths, endpoint: Endpoint
) -> None:
    assert runtime_dir_problem(endpoint) is None
    silent = SilentDaemon(endpoint)
    try:
        process = subprocess.Popen(
            sq_command(project, "list", "--json"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=remote_env(),
            creationflags=NEW_CONSOLE,
        )
        assert silent.received.wait(30), "the command never sent its request"
        assert one_sigint(process, within=5) == (130, "", interrupted(endpoint))
    finally:
        silent.close()


def test_one_ctrl_c_ends_the_wait_for_a_slow_answer_and_the_write_lands_once(
    project: SquadPaths, endpoint: Endpoint
) -> None:
    started = run_with(project, "list", "--json")
    assert started.returncode == 0, started.stderr
    holder = FileLock(
        str(project.lock_path), thread_local=False, fallback_to_soft=False, preserve_lock_file=True
    )
    holder.acquire(timeout=10)
    try:
        process = subprocess.Popen(
            sq_command(project, "create", "task", "Lands once", "--author", "manager"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=remote_env(),
            creationflags=NEW_CONSOLE,
        )
        time.sleep(2.5)  # the request is with the daemon, which waits for the lock
        code, out, err = one_sigint(process, within=5)
        assert (code, out) == (130, "")
        assert err.endswith(interrupted(endpoint))
    finally:
        holder.release()
    titles: list[str] = []
    for _ in range(100):
        listed = run_with(project, "list", "--type", "task", "--json")
        titles = [item["title"] for item in json.loads(listed.stdout)]
        if titles:
            break
        time.sleep(0.1)
    assert titles == ["Lands once"]


def run_with(project: SquadPaths, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        sq_command(project, *args), capture_output=True, text=True, env=remote_env(), check=False
    )
