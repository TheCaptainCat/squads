"""The credential verbs run only where the squad is served, on the owner's listener: the secret a
client answers a hidden prompt with never comes back in the output, and the browser listener
cannot reach the verbs or the store."""

import json
import sys

import pytest

from squads._sources._credentials import store_path
from tests._daemon_process import enable_browser
from tests._endpoint_client import command_body, post_commands

SECRET = "glpat-not-a-real-token"
SOURCE = (
    '[sources.platform]\nconnector = "gitlab"\nbase_url = "http://127.0.0.1:9"\n'
    '[sources.platform.maps.types]\nbug = "task"\n'
)
SET = ["source", "credential", "set", "platform"]
HEADERS = {"Content-Type": "application/json", "Squads-Client": "1"}


def _declare(project) -> None:
    path = project.squad_dir / ".overrides" / "sources.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SOURCE, encoding="utf-8")


def test_a_hidden_answer_is_asked_for_without_echo_and_never_comes_back(
    project, serve, credentials_home
) -> None:
    _declare(project)
    daemon = serve(project)

    asked = post_commands(daemon, command_body(SET)).json()
    answers = [{"digest": asked["digest"], "line": SECRET}]
    done = post_commands(daemon, command_body(SET, answers=answers))

    assert asked == {
        "kind": "prompt",
        "output": [],
        "text": "platform token: ",
        "stream": "stderr",
        "digest": asked["digest"],
        "hidden": True,
    }
    assert (done.status, done.json()["exit_code"]) == (200, 0)
    assert SECRET not in json.dumps(asked) + done.body.decode()
    assert SECRET in store_path().read_text(encoding="utf-8")


@pytest.mark.skipif(sys.platform == "win32", reason="Windows has no Unix socket")
async def test_the_browser_listener_reaches_neither_the_credential_verbs_nor_the_store(
    project, run_daemon, credentials_home
) -> None:
    _declare(project)
    enable_browser(project)
    running = run_daemon(project)
    host, port = running.listener("browser")
    answers = [{"digest": "x", "line": SECRET}]
    body = json.dumps(command_body(SET, answers=answers)).encode()

    status, _, answer = running.over_tcp(
        "browser",
        "POST",
        "/v1/commands",
        headers={**HEADERS, "Origin": f"http://{host}:{port}"},
        body=body,
    )
    served, document = running.get_over_cli("/v1/openapi.json")

    assert (status, json.loads(answer)) == (
        404,
        {"error": {"type": "not_found", "message": "no such route", "warnings": []}},
    )
    assert not store_path().exists()
    assert (served, "credential" in document.decode()) == (200, False)
