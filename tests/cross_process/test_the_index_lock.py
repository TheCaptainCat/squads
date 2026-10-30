"""The index lock across processes: concurrent writers serialise, a writer waits for a held lock and
says so, gives up when it stays held, and finds the lock free when its holder was killed.

Each case runs the real `sq` console script against a scratch squad, as the cross-process set does.
"""

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from squads._paths import SquadPaths

#: Takes the squad's lock with the store's own flags, reports it, then holds it for the seconds
#: given (until killed when it is long) and releases it by exiting.
HOLDER = """\
import sys, time
from filelock import FileLock
lock = FileLock(
    sys.argv[1], thread_local=False, fallback_to_soft=False, preserve_lock_file=True
)
lock.acquire(timeout=30)
print("held", flush=True)
time.sleep(float(sys.argv[2]))
"""


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("FORCE_COLOR", None)
    return env


def _sq_command(project: SquadPaths, *args: str) -> list[str]:
    """The `sq` console script of the running environment, on the project."""
    script = shutil.which("sq", path=str(Path(sys.executable).parent))
    assert script is not None, "the sq console script is not installed next to the interpreter"
    return [script, "-C", str(project.root), *args]


def _create(project: SquadPaths, title: str) -> list[str]:
    return _sq_command(project, "create", "task", title, "--author", "manager", "--json")


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, env=_env(), check=False)


def _titles(project: SquadPaths) -> list[str]:
    """The titles of the tasks the squad holds, read back through `sq list`."""
    listed = _run(_sq_command(project, "list", "--type", "task", "--json"))
    assert listed.returncode == 0, listed.stderr
    return [item["title"] for item in json.loads(listed.stdout)]


@pytest.fixture
def holder(project: SquadPaths) -> Iterator[Callable[[float], subprocess.Popen[str]]]:
    """Starts a process holding the squad's lock; every one still alive at the end is killed."""
    started: list[subprocess.Popen[str]] = []

    def start(seconds: float) -> subprocess.Popen[str]:
        process = subprocess.Popen(
            [sys.executable, "-I", "-c", HOLDER, str(project.lock_path), str(seconds)],
            stdout=subprocess.PIPE,
            text=True,
        )
        started.append(process)
        assert process.stdout is not None
        assert process.stdout.readline().strip() == "held"
        return process

    yield start
    for process in started:
        process.kill()
        process.wait()
        if process.stdout is not None:
            process.stdout.close()


def test_concurrent_writers_serialise_and_leave_a_valid_index(project) -> None:
    writers = [
        subprocess.Popen(
            _create(project, f"Item {n}"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=_env(),
        )
        for n in range(4)
    ]
    outputs = [(w.communicate(), w.returncode) for w in writers]
    assert [(code, err) for (_, err), code in outputs] == [(0, "")] * 4
    ids = {json.loads(out)["id"] for (out, _), _ in outputs}
    assert len(ids) == 4
    assert sorted(_titles(project)) == [f"Item {n}" for n in range(4)]


def test_a_writer_finding_the_lock_held_says_so_then_proceeds_on_release(project, holder) -> None:
    holder(2.0)
    result = _run(_create(project, "After the wait"))
    assert (result.returncode, result.stderr) == (
        0,
        f"waiting for the index lock {project.lock_path}…\n",
    )
    assert json.loads(result.stdout)["title"] == "After the wait"
    assert _titles(project) == ["After the wait"]


def test_a_lock_held_past_the_timeout_fails_the_command_and_writes_nothing(project, holder) -> None:
    holder(60.0)
    result = _run(_create(project, "Never written"))
    assert (result.returncode, result.stdout, result.stderr) == (
        1,
        "",
        f"waiting for the index lock {project.lock_path}…\n"
        f"error: the index lock {project.lock_path} is held by another sq process; "
        "nothing was written, retry the command\n",
    )
    assert _titles(project) == []


def test_a_holder_killed_hard_releases_the_lock(project, holder) -> None:
    process = holder(60.0)
    process.kill()
    process.wait()
    result = _run(_create(project, "After the kill"))
    assert (result.returncode, result.stderr) == (0, "")
    assert _titles(project) == ["After the kill"]
