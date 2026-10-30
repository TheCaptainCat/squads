"""Each metadata header binds the request it arrives on, and nothing the daemon's own process
holds stands in for it. The test process is the daemon's process, so each case sets the process
value the header replaces to something else."""

import json
from pathlib import Path

import pytest

from squads._paths import SquadPaths

pytestmark = pytest.mark.anyio

CREATE = {"type": "task", "title": "Bound", "author": "manager"}


async def last_reflog(invoke) -> dict[str, object]:
    result = await invoke(["reflog", "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)[-1]


async def test_the_actor_header_is_the_actor_the_reflog_records(project, serve, invoke) -> None:
    daemon = serve(project)
    daemon.request("POST", "/v1/items", CREATE)
    reply = daemon.request(
        "PATCH", "/v1/items/TASK-2", {"description": "Declared"}, {"Squads-Actor": "manager"}
    )
    assert reply.status == 200, reply.body
    line = await last_reflog(invoke)
    assert (line["actor"], line["op"]) == ("manager", "update")


async def test_the_time_header_is_the_time_the_write_records(project, serve, invoke) -> None:
    daemon = serve(project)
    reply = daemon.request("POST", "/v1/items", CREATE, {"Squads-At": "2030-01-02T03:04:05Z"})
    assert reply.status == 200
    shown = json.loads((await invoke(["show", "2", "--json"])).output)
    assert (shown["created_at"], shown["updated_at"]) == ("2030-01-02T03:04:05Z",) * 2
    assert (await last_reflog(invoke))["ts"] == "2030-01-02T03:04:05Z"


async def test_the_session_header_is_the_session_the_reflog_records(
    project, serve, invoke, monkeypatch
) -> None:
    monkeypatch.setenv("SQUADS_SESSION_ID", "process-session")
    daemon = serve(project)
    daemon.request("POST", "/v1/items", CREATE, {"Squads-Session-Id": "header-session"})
    assert (await last_reflog(invoke))["session_id"] == "header-session"
    daemon.request("PATCH", "/v1/items/TASK-2", {"description": "again"})
    assert (await last_reflog(invoke))["session_id"] is None


async def test_the_parent_session_header_is_the_parent_the_reflog_records(
    project, serve, invoke, monkeypatch
) -> None:
    monkeypatch.setenv("SQUADS_PARENT_SESSION_ID", "process-parent")
    daemon = serve(project)
    daemon.request("POST", "/v1/items", CREATE, {"Squads-Parent-Session-Id": "header-parent"})
    assert (await last_reflog(invoke))["parent_session_id"] == "header-parent"
    daemon.request("PATCH", "/v1/items/TASK-2", {"description": "again"})
    assert (await last_reflog(invoke))["parent_session_id"] is None


def test_a_remedy_path_is_spelled_from_the_client_directory_or_the_squad_root(
    project: SquadPaths, serve, tmp_path_factory, monkeypatch
) -> None:
    ghost = project.squad_dir / ".overrides" / "roles" / "ghost.toml"
    ghost.parent.mkdir(parents=True)
    ghost.write_text('name = "Ghost"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path_factory.mktemp("elsewhere"))
    daemon = serve(project)

    def remedy(headers: dict[str, str]) -> str:
        reply = daemon.request("POST", "/v1/roles/activate", {"slug": "ghost"}, headers)
        assert reply.status == 400, reply.body
        message: str = reply.json()["error"]["message"]
        return message.rsplit("--file ", 1)[1].rstrip("`")

    squad = project.squad_dir.name
    ghost_path = str(Path(".overrides", "roles", "ghost.toml"))
    assert remedy({}) == str(Path(squad, ghost_path))
    assert remedy({"Squads-Client-Dir": str(project.root.parent)}) == (
        str(Path(project.root.name, squad, ghost_path))
    )
    assert remedy({"Squads-Client-Dir": str(project.squad_dir)}) == ghost_path
