"""The index lock: concurrent writers serialise, a writer waits for a held lock and says so, gives
up when it stays held, and finds the lock free when its holder was killed."""

import asyncio
import json
import subprocess
import sys
import time
from collections.abc import Callable, Iterator

import pytest

from squads._paths import SquadPaths
from tests._profile import selected

P = selected()

pytestmark = pytest.mark.anyio

#: Takes the squad's lock the way `sq` does, reports it, holds it for the seconds given (until
#: killed when none) and releases it by exiting.
HOLDER = """\
import sys, time
from filelock import FileLock
lock = FileLock(sys.argv[1], thread_local=False)
lock.acquire(timeout=30)
print("held", flush=True)
time.sleep(float(sys.argv[2]))
"""

#: A `sq` run as a child process: the entry point `sq` installs, with the project as `-C`.
SQ = "from squads.__main__ import main; main()"


def _hold(project: SquadPaths, seconds: float) -> subprocess.Popen[str]:
    """A process that holds the squad's index lock for *seconds*, once it reports holding it."""
    holder = subprocess.Popen(
        [sys.executable, "-I", "-c", HOLDER, str(project.lock_path), str(seconds)],
        stdout=subprocess.PIPE,
        text=True,
    )
    assert holder.stdout is not None
    assert holder.stdout.readline().strip() == "held"
    return holder


@pytest.fixture
def holder(project: SquadPaths) -> Iterator[Callable[[float], subprocess.Popen[str]]]:
    """Starts a holder of the squad's lock; every holder still alive at the end is killed."""
    started: list[subprocess.Popen[str]] = []

    def start(seconds: float) -> subprocess.Popen[str]:
        started.append(_hold(project, seconds))
        return started[-1]

    yield start
    for process in started:
        process.kill()
        process.wait()
        if process.stdout is not None:
            process.stdout.close()


async def _titles(invoke) -> list[str]:
    """The titles of the items of the reference type, in number order."""
    result = await invoke(["list", "--type", P.ref, "--json"])
    assert result.exit_code == 0, result.output
    return [item["title"] for item in json.loads(result.output)]


def _run_writers(project: SquadPaths) -> list[tuple[str, int]]:
    """Four `sq create` processes started together: each one's output and exit code."""
    writers = [
        subprocess.Popen(
            [
                sys.executable,
                "-c",
                SQ,
                "-C",
                str(project.root),
                "create",
                P.ref,
                f"Item {n}",
                "--author",
                "manager",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for n in range(4)
    ]
    return [(w.communicate()[0], w.returncode) for w in writers]


@pytest.mark.covers("list", "--type")
async def test_concurrent_writers_serialise_and_leave_a_valid_index(project, invoke) -> None:
    outputs = await asyncio.to_thread(_run_writers, project)
    assert [code for _, code in outputs] == [0, 0, 0, 0], outputs
    result = await invoke(["list", "--type", P.ref, "--json"])
    items = json.loads(result.output)
    assert sorted(item["title"] for item in items) == [f"Item {n}" for n in range(4)]
    assert len({item["id"] for item in items}) == 4


@pytest.mark.covers("create <type>", "--author")
async def test_a_writer_finding_the_lock_held_says_so_then_proceeds_on_release(
    project, invoke, holder
) -> None:
    holder(2.0)
    started = time.monotonic()
    result = await invoke(["create", P.ref, "After the wait", "--author", "manager"])
    waited = time.monotonic() - started
    assert result.exit_code == 0, result.output
    assert f"waiting for the index lock {project.lock_path}" in result.output
    assert 1.0 <= waited < 8.0
    assert await _titles(invoke) == ["After the wait"]


@pytest.mark.covers("create <type>", "--author")
async def test_a_lock_held_past_the_timeout_fails_the_command_and_writes_nothing(
    project, invoke, holder
) -> None:
    holder(60.0)
    result = await invoke(["create", P.ref, "Never written", "--author", "manager"])
    assert result.exit_code == 1
    assert f"waiting for the index lock {project.lock_path}" in result.output
    assert (
        f"error: the index lock {project.lock_path} is held by another sq process; "
        "nothing was written, retry the command\n"
    ) in result.output
    assert await _titles(invoke) == []


@pytest.mark.covers("create <type>", "--author")
async def test_a_holder_killed_hard_releases_the_lock(project, invoke, holder) -> None:
    process = holder(60.0)
    process.kill()
    process.wait()
    started = time.monotonic()
    result = await invoke(["create", P.ref, "After the kill", "--author", "manager"])
    assert result.exit_code == 0, result.output
    assert "waiting for the index lock" not in result.output
    assert time.monotonic() - started < 1.0
    assert await _titles(invoke) == ["After the kill"]
