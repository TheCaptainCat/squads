"""`sq daemon ...`: seeing the daemon that serves a squad, stopping it, refusing a second one."""

import json
import os
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
    assert (result.exit_code, result.output.splitlines()) == (
        0,
        [
            f"daemon running (pid {os.getpid()})",
            f"  version: {__version__}",
            f"  squad: {project.squad_dir.resolve()}",
            f"  started: {daemon['started_at']}",
            f"  exits idle at: {daemon['idle_deadline']}",
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
