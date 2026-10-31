"""The browser listener is off unless `[daemon] browser = true`; when on, it serves the same
routes on loopback and takes a write only from a request whose Origin is its own."""

import json

import pytest

from tests._daemon_process import enable_browser
from tests._endpoint_client import command_body

pytestmark = pytest.mark.anyio

CREATE = json.dumps({"type": "task", "title": "Via the browser port", "author": "manager"}).encode()
HEADERS = {"Content-Type": "application/json", "Squads-Client": "1"}


async def test_the_browser_listener_is_loopback_and_listed_in_the_identity(
    project, run_daemon
) -> None:
    enable_browser(project)
    running = run_daemon(project)

    listeners = running.identity()["listeners"]

    browser = [ln for ln in listeners if ln["kind"] == "browser"]
    assert browser
    assert {ln["transport"] for ln in browser} == {"tcp"}
    assert all(ln["address"].startswith(("127.0.0.1:", "[::1]:")) for ln in browser)
    assert json.loads(running.endpoint.files.info.read_text())["listeners"] == listeners


async def test_a_write_from_the_listeners_own_origin_is_stored(project, run_daemon, invoke) -> None:
    enable_browser(project)
    running = run_daemon(project)
    host, port = running.listener("browser")

    status, _, body = running.over_tcp(
        "browser",
        "POST",
        "/v1/items",
        headers={**HEADERS, "Origin": f"http://{host}:{port}"},
        body=CREATE,
    )

    assert status == 200, body
    shown = await invoke(["task", "2", "show", "--json"])
    assert (shown.exit_code, json.loads(shown.output)["title"]) == (0, "Via the browser port")


async def test_a_write_from_a_foreign_origin_is_refused_and_nothing_is_stored(
    project, run_daemon, invoke
) -> None:
    enable_browser(project)
    running = run_daemon(project)

    status, _, body = running.over_tcp(
        "browser",
        "POST",
        "/v1/items",
        headers={**HEADERS, "Origin": "http://example.com"},
        body=CREATE,
    )

    assert (status, json.loads(body)) == (
        403,
        {
            "error": {
                "type": "forbidden",
                "message": "a write needs an Origin equal to this listener's",
                "warnings": [],
            }
        },
    )
    listed = await invoke(["list", "--type", "task", "--json"])
    assert (listed.exit_code, json.loads(listed.output)) == (0, [])


async def test_the_browser_listener_does_not_serve_the_command_endpoint(
    project, run_daemon
) -> None:
    enable_browser(project)
    running = run_daemon(project)
    host, port = running.listener("browser")
    body = json.dumps(command_body(["--help"])).encode()

    status, _, answer = running.over_tcp(
        "browser",
        "POST",
        "/v1/commands",
        headers={**HEADERS, "Origin": f"http://{host}:{port}"},
        body=body,
    )

    assert (status, json.loads(answer)) == (
        404,
        {"error": {"type": "not_found", "message": "no such route", "warnings": []}},
    )
    served, _ = running.get_over_cli("/v1/commands", "POST", command_body(["--help"]))
    assert served == 200
