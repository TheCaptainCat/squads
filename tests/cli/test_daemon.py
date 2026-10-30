"""`sq daemon ...`: seeing the daemon that serves a squad, stopping it, refusing a second one."""

import json
import os
import re
import shutil
from typing import Any

import pytest

from squads import __version__
from squads._spec_documents import spec_sources
from tests._daemon_process import enable_browser

pytestmark = pytest.mark.anyio

NONE_RUNNING = "no daemon is running for this squad\n"


async def _status(invoke, *args: str) -> dict[str, Any]:
    result = await invoke([*args, "daemon", "status", "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


@pytest.mark.covers("daemon status")
async def test_status_with_no_daemon_says_so(project, daemon_runtime, invoke) -> None:
    result = await invoke(["daemon", "status"])
    assert (result.exit_code, result.output) == (0, NONE_RUNNING)


@pytest.mark.covers("daemon status", "--json")
async def test_status_json_with_no_daemon_reports_none(project, daemon_runtime, invoke) -> None:
    assert await _status(invoke) == {"running": False, "daemon": None}


@pytest.mark.covers("daemon status", "--json")
async def test_status_json_reports_the_daemon_that_serves_the_squad(
    project, run_daemon, invoke
) -> None:
    running = run_daemon(project)

    document = await _status(invoke)

    daemon = document["daemon"]
    assert document["running"] is True
    assert (daemon["pid"], daemon["version"], daemon["squad_dir"]) == (
        os.getpid(),
        __version__,
        str(project.squad_dir.resolve()),
    )
    [listener] = daemon["listeners"]
    if running.endpoint.transport == "unix":
        assert listener == {
            "transport": "unix",
            "address": str(running.endpoint.files.socket),
            "kind": "cli",
        }
    else:
        assert (listener["transport"], listener["kind"]) == ("tcp", "cli")
        assert listener["address"].startswith("127.0.0.1:")
    assert daemon["vocabulary"]["hash"] == spec_sources(project.squad_dir).vocabulary().hash


@pytest.mark.covers("daemon status")
async def test_status_prints_the_identity_of_the_daemon(project, run_daemon, invoke) -> None:
    run_daemon(project)
    daemon = (await _status(invoke))["daemon"]

    result = await invoke(["daemon", "status"])

    listening = [
        f"  listening: {ln['address']} ({ln['transport']}, {ln['kind']})"
        for ln in daemon["listeners"]
    ]
    lines = result.output.splitlines()
    # each request moves the idle deadline, so the status call before this one is behind it
    assert re.fullmatch(r"  exits idle at: \d{4}-\d\d-\d\dT[\d:.]+\+00:00", lines.pop(4))
    assert (result.exit_code, lines) == (
        0,
        [
            f"daemon running (pid {os.getpid()})",
            f"  version: {__version__}",
            f"  squad: {project.squad_dir.resolve()}",
            f"  started: {daemon['started_at']}",
            *listening,
            f"  vocabulary: {daemon['vocabulary']['hash']}",
        ],
    )


@pytest.mark.covers("daemon stop")
async def test_stop_ends_the_daemon_and_removes_its_files(project, run_daemon, invoke) -> None:
    running = run_daemon(project)
    files = running.endpoint.files

    result = await invoke(["daemon", "stop"])

    assert (result.exit_code, result.output) == (0, "daemon stopped\n")
    assert await _status(invoke) == {"running": False, "daemon": None}
    running.wait_until_exited()
    assert [p.name for p in files.all() if p.exists()] == []


@pytest.mark.covers("daemon stop", "--json")
async def test_stop_json_says_a_daemon_was_running(project, run_daemon, invoke) -> None:
    run_daemon(project)
    result = await invoke(["daemon", "stop", "--json"])
    assert (result.exit_code, json.loads(result.output)) == (0, {"was_running": True})


@pytest.mark.covers("daemon stop", "--json")
async def test_stop_with_no_daemon_does_nothing_and_succeeds(
    project, daemon_runtime, invoke
) -> None:
    plain = await invoke(["daemon", "stop"])
    as_json = await invoke(["daemon", "stop", "--json"])

    assert (plain.exit_code, plain.output) == (0, NONE_RUNNING)
    assert (as_json.exit_code, json.loads(as_json.output)) == (0, {"was_running": False})


@pytest.mark.covers("daemon run")
async def test_run_refuses_to_start_while_one_runs(project, run_daemon, invoke) -> None:
    run_daemon(project)

    result = await invoke(["daemon", "run"])

    assert (result.exit_code, result.output) == (1, "error: already running\n")


@pytest.mark.covers("daemon run", "--report-fd")
async def test_run_reports_why_it_did_not_start_on_the_pipe_it_is_given(
    project, run_daemon, invoke
) -> None:
    run_daemon(project)
    read, write = os.pipe()
    try:
        # the daemon closes the write end once it has reported
        result = await invoke(["daemon", "run", "--report-fd", str(write)])
        reported = os.read(read, 200)
    finally:
        os.close(read)

    assert (result.exit_code, reported) == (1, b"error: already running\n")


@pytest.mark.covers("daemon status", "--json")
async def test_status_finds_the_daemon_from_a_folder_inside_the_squad(
    project, run_daemon, invoke
) -> None:
    run_daemon(project)
    inside = project.root / "docs" / "notes"
    inside.mkdir(parents=True)

    from_inside = await _status(invoke, "-C", str(inside))

    assert from_inside["running"] is True
    assert from_inside["daemon"]["squad_dir"] == str(project.squad_dir.resolve())


@pytest.mark.covers("daemon status", "--json")
async def test_status_from_another_squad_reports_none(
    project, run_daemon, invoke, tmp_path_factory
) -> None:
    run_daemon(project)
    other = shutil.copytree(project.root, tmp_path_factory.mktemp("other") / "copy")

    assert await _status(invoke, "-C", str(other)) == {"running": False, "daemon": None}


@pytest.mark.covers("daemon status", "--json")
async def test_status_json_lists_the_browser_listener_when_it_is_on(
    project, run_daemon, invoke
) -> None:
    enable_browser(project)
    run_daemon(project)

    listeners = (await _status(invoke))["daemon"]["listeners"]

    assert listeners[0]["kind"] == "cli"
    browser = [ln for ln in listeners if ln["kind"] == "browser"]
    assert browser
    assert all(ln["address"].startswith(("127.0.0.1:", "[::1]:")) for ln in browser)


@pytest.mark.covers("daemon status", "--json")
async def test_status_finds_the_daemon_through_a_link_to_the_project(
    project, run_daemon, invoke, tmp_path_factory
) -> None:
    run_daemon(project)
    link = tmp_path_factory.mktemp("links") / "project"
    try:
        link.symlink_to(project.root, target_is_directory=True)
    except OSError:
        pytest.skip("this platform does not let the test create a link")

    through_link = await _status(invoke, "-C", str(link))

    assert through_link["daemon"]["squad_dir"] == str(project.squad_dir.resolve())


def _hold_the_lock(endpoint):
    """Hold the daemon's lock without serving, as a daemon that does not answer does."""
    from filelock import FileLock

    endpoint.runtime_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock = FileLock(
        str(endpoint.files.lock),
        thread_local=False,
        fallback_to_soft=False,
        preserve_lock_file=True,
    )
    lock.acquire(timeout=5)
    return lock


@pytest.mark.covers("daemon status")
async def test_status_says_so_when_a_daemon_holds_the_lock_and_does_not_answer(
    project, daemon_runtime, invoke
) -> None:
    from squads._endpoint import endpoint_for

    endpoint = endpoint_for(project.root)
    assert endpoint is not None
    lock = _hold_the_lock(endpoint)
    try:
        result = await invoke(["daemon", "status"])
    finally:
        lock.release()

    assert (result.exit_code, result.output) == (
        1,
        f"error: a daemon holds {endpoint.files.lock} but does not answer; it may be starting, "
        "or it needs to be ended from outside\n",
    )


@pytest.mark.covers("daemon stop")
async def test_stop_says_so_when_a_daemon_holds_the_lock_and_does_not_answer(
    project, daemon_runtime, invoke
) -> None:
    from squads._endpoint import endpoint_for

    endpoint = endpoint_for(project.root)
    assert endpoint is not None
    lock = _hold_the_lock(endpoint)
    try:
        result = await invoke(["daemon", "stop"])
    finally:
        lock.release()

    assert (result.exit_code, result.output) == (
        1,
        f"error: a daemon holds {endpoint.files.lock} but does not answer; it may be starting, "
        "or it needs to be ended from outside\n",
    )


@pytest.mark.covers("daemon run")
async def test_run_refuses_to_start_with_an_unusable_squads_daemon(
    project, daemon_runtime, invoke, monkeypatch
) -> None:
    monkeypatch.setenv("SQUADS_DAEMON", "maybe")

    result = await invoke(["daemon", "run"])

    assert (result.exit_code, result.output) == (
        1,
        "error: SQUADS_DAEMON must be on or off, got 'maybe'; every command runs in local mode "
        "until it is fixed\n",
    )
