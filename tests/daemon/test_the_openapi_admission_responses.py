"""The OpenAPI document declares what admission can answer: a misdirected request on every
operation and a refused write on every operation that writes."""

import json


def test_the_openapi_document_declares_the_admission_refusals(project, run_daemon) -> None:
    running = run_daemon(project)
    status, body = running.get_over_cli("/v1/openapi.json")
    paths = json.loads(body)["paths"]

    assert status == 200
    operations = {
        (method, route): sorted(op["responses"])
        for route, methods in paths.items()
        if route not in ("/v1/daemon", "/v1/daemon/stop")
        for method, op in methods.items()
    }
    assert operations
    assert all("421" in codes for codes in operations.values())
    assert all(("403" in codes) == (method != "get") for (method, _), codes in operations.items())
