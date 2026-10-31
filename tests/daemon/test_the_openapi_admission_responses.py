"""The OpenAPI document declares what admission and the router can answer, and the statuses the
daemon really gives for those requests are among the ones it declares."""

import json
import sys

import pytest

from tests._daemon_process import enable_browser

JSON = {"Content-Type": "application/json"}


def declared(running) -> dict[tuple[str, str], list[str]]:
    status, body = running.get_over_cli("/v1/openapi.json")
    assert status == 200
    return {
        (method, route): sorted(op["responses"])
        for route, methods in json.loads(body)["paths"].items()
        for method, op in methods.items()
    }


def test_every_operation_and_daemon_route_declares_the_misdirected_forbidden_and_405_answers(
    project, run_daemon
) -> None:
    operations = declared(run_daemon(project))

    assert operations
    for codes in operations.values():
        assert {"403", "405", "421"} <= set(codes)


def test_what_admission_and_the_router_answer_is_declared(project, run_daemon) -> None:
    enable_browser(project)
    running = run_daemon(project)
    operations = declared(running)
    _, port = running.listener("browser")

    answers = {
        # a rebinding Host on a daemon route
        ("get", "/v1/daemon"): running.over_tcp(
            "browser", "GET", "/v1/daemon", headers={"Host": f"rebound.example:{port}"}
        ),
        # a write without Squads-Client on a daemon route
        ("post", "/v1/daemon/stop"): running.over_tcp(
            "browser",
            "POST",
            "/v1/daemon/stop",
            headers={**JSON, "Origin": f"http://127.0.0.1:{port}"},
            body=b"{}",
        ),
        # a method the path does not serve
        ("delete", "/v1/daemon"): running.over_tcp(
            "browser",
            "DELETE",
            "/v1/daemon",
            headers={**JSON, "Squads-Client": "1", "Origin": f"http://127.0.0.1:{port}"},
        ),
    }

    for (method, route), (status, _, _) in answers.items():
        reference = (method if method != "delete" else "get", route)
        assert str(status) in operations[reference], (method, route, status)
    assert [s for s, _, _ in answers.values()] == [421, 403, 405]
    assert answers[("delete", "/v1/daemon")][1]["allow"] == "GET, HEAD"


@pytest.mark.skipif(sys.platform != "win32", reason="the CLI port is a TCP port on Windows only")
def test_a_get_with_an_origin_on_the_windows_cli_port_is_declared(project, run_daemon) -> None:
    running = run_daemon(project)

    status, _, _ = running.over_tcp("cli", "GET", "/v1/daemon", headers={"Origin": "http://x.test"})

    assert (status, "403" in declared(running)[("get", "/v1/daemon")]) == (403, True)
