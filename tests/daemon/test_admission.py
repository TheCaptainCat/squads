"""A request a listener's admission rules refuse never reaches a route: the whole answer is
asserted, and the squad is read back to show nothing was written. The listener decides the rules,
so the cases run over TCP; the browser listener carries them on every platform."""

import json
import sys
from typing import Any

import pytest

from tests._daemon_process import enable_browser

pytestmark = pytest.mark.anyio

CREATE = json.dumps({"type": "task", "title": "Refused", "author": "manager"}).encode()
JSON = "application/json"


def refused(status: int, kind: str, message: str) -> tuple[int, dict[str, Any]]:
    return status, {"error": {"type": kind, "message": message, "warnings": []}}


async def nothing_written(invoke) -> None:
    listed = await invoke(["list", "--type", "task", "--json"])
    assert (listed.exit_code, json.loads(listed.output)) == (0, [])


def write(running, headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
    """A create on the browser listener with exactly *headers* besides its own Origin."""
    host, port = running.listener("browser")
    sent = {"Origin": f"http://{host}:{port}", **headers}
    status, _, body = running.over_tcp("browser", "POST", "/v1/items", headers=sent, body=CREATE)
    return status, json.loads(body)


async def test_a_host_that_is_not_the_listeners_is_refused_before_routing(
    project, run_daemon, invoke
) -> None:
    enable_browser(project)
    running = run_daemon(project)
    _, port = running.listener("browser")

    status, headers, body = running.over_tcp(
        "browser", "GET", "/v1/daemon", headers={"Host": f"rebound.example:{port}"}
    )

    assert (status, json.loads(body)) == refused(
        421, "misdirected", "the Host header does not name this listener"
    )
    assert "access-control-allow-origin" not in headers


async def test_a_form_post_is_refused(project, run_daemon, invoke) -> None:
    enable_browser(project)
    running = run_daemon(project)

    answer = write(
        running, {"Content-Type": "application/x-www-form-urlencoded", "Squads-Client": "1"}
    )

    assert answer == refused(403, "forbidden", "a write needs Content-Type: application/json")
    await nothing_written(invoke)


async def test_a_plain_text_body_is_refused(project, run_daemon, invoke) -> None:
    enable_browser(project)
    running = run_daemon(project)

    answer = write(running, {"Content-Type": "text/plain", "Squads-Client": "1"})

    assert answer == refused(403, "forbidden", "a write needs Content-Type: application/json")
    await nothing_written(invoke)


async def test_a_write_without_the_client_header_is_refused(project, run_daemon, invoke) -> None:
    enable_browser(project)
    running = run_daemon(project)

    answer = write(running, {"Content-Type": JSON})

    assert answer == refused(403, "forbidden", "a write needs the header Squads-Client: 1")
    await nothing_written(invoke)


async def test_a_write_with_another_client_header_value_is_refused(
    project, run_daemon, invoke
) -> None:
    enable_browser(project)
    running = run_daemon(project)

    answer = write(running, {"Content-Type": JSON, "Squads-Client": "2"})

    assert answer == refused(403, "forbidden", "a write needs the header Squads-Client: 1")
    await nothing_written(invoke)


async def test_a_preflight_is_refused_and_no_cors_header_is_ever_sent(project, run_daemon) -> None:
    enable_browser(project)
    running = run_daemon(project)
    host, port = running.listener("browser")
    origin = f"http://{host}:{port}"

    preflight = running.over_tcp(
        "browser",
        "OPTIONS",
        "/v1/items",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type, squads-client",
        },
    )
    read = running.over_tcp("browser", "GET", "/v1/daemon", headers={"Origin": origin})

    assert (preflight[0], json.loads(preflight[2])) == refused(
        403, "forbidden", "a write needs Content-Type: application/json"
    )
    assert read[0] == 200
    for _, headers, _ in (preflight, read):
        assert [name for name in headers if name.startswith("access-control-")] == []


@pytest.mark.skipif(sys.platform != "win32", reason="the CLI port is a TCP port on Windows only")
async def test_any_origin_on_the_windows_cli_port_is_refused(project, run_daemon, invoke) -> None:
    running = run_daemon(project)

    status, _, body = running.over_tcp(
        "cli",
        "GET",
        "/v1/daemon",
        headers={"Origin": "http://example.com"},
    )

    assert (status, json.loads(body)) == refused(
        403, "forbidden", "this listener refuses a request that has an Origin"
    )


async def test_head_is_admitted_like_get(project, run_daemon) -> None:
    enable_browser(project)
    running = run_daemon(project)

    status, _, _ = running.over_tcp("browser", "HEAD", "/v1/daemon")

    assert status == 200


@pytest.mark.skipif(sys.platform == "win32", reason="the CLI listener is a TCP port on Windows")
async def test_the_cli_socket_asks_for_neither_the_content_type_nor_the_client_header(
    project, run_daemon
) -> None:
    from squads._daemon_link import connection
    from squads._endpoint import read_record

    running = run_daemon(project)
    conn = connection(running.endpoint, read_record(running.endpoint))
    assert conn is not None
    try:
        conn.request("POST", "/v1/items", body=b"{}")
        reply = conn.getresponse()
        status, body = reply.status, json.loads(reply.read())
    finally:
        conn.close()

    # routed and refused as an invalid request, not by admission
    assert (status, body["error"]["type"]) == (400, "invalid")
