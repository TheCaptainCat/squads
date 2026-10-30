"""The status and body a route answers with for each row of the error table, and the envelope of a
partial read. Each case asserts the whole response; state is read back through the CLI."""

import json
import logging
from collections.abc import Iterator

import pytest
from filelock import FileLock

from squads._board._store import board_folder
from squads._index import _store as index_store
from squads._paths import SquadPaths
from squads._services import _local_api as local_api
from squads._services import _service as service
from tests._daemon_harness import Reply, Served

pytestmark = pytest.mark.anyio

JSON = "application/json"


def whole(reply: Reply) -> tuple[int, str, object]:
    """The status, content type and parsed body of a response."""
    return reply.status, reply.headers["content-type"], reply.json()


def error(kind: str, message: str, **extra: object) -> dict[str, object]:
    return {"error": {"type": kind, "message": message, "warnings": [], **extra}}


def create_task(daemon: Served, title: str) -> str:
    reply = daemon.request(
        "POST", "/v1/items", {"type": "task", "title": title, "author": "manager"}
    )
    assert reply.status == 200, reply.body
    return reply.json()["data"]["id"]


def test_an_unknown_item_answers_404_not_found(project, serve) -> None:
    reply = serve(project).get("/v1/items/TASK-99")
    assert whole(reply) == (
        404,
        JSON,
        error("not_found", "no item with number 99 (use a full ID like TYPE-99 or bare 99)"),
    )


def test_a_transition_the_lifecycle_refuses_answers_409_conflict(project, serve) -> None:
    daemon = serve(project)
    item_id = create_task(daemon, "Refused")
    reply = daemon.request("POST", f"/v1/items/{item_id}/status", {"status": "Done"})
    assert reply.status == 409
    assert reply.headers["content-type"] == JSON
    body = reply.json()["error"]
    assert (body["type"], body["warnings"], "details" in body) == ("conflict", [], False)
    assert "Draft" in body["message"]
    assert "Done" in body["message"]


def test_a_vocabulary_that_differs_answers_409_with_the_digests(project, serve) -> None:
    daemon = serve(project)
    digests = daemon.get("/v1/daemon").json()["vocabulary"]["documents"]
    reply = daemon.get("/v1/items", {"Squads-Vocabulary": "0" * 64})
    assert whole(reply) == (
        409,
        JSON,
        error(
            "vocabulary_mismatch",
            "the client's workflow vocabulary differs from the squad's",
            details=digests,
        ),
    )


def test_a_schema_that_differs_answers_409_with_both_versions(project, serve) -> None:
    daemon = serve(project)
    schema = daemon.get("/v1/daemon").json()["schema_version"]
    reply = daemon.get("/v1/items", {"Squads-Schema": "0.1"})
    assert whole(reply) == (
        409,
        JSON,
        error(
            "schema_mismatch",
            f"the client speaks schema v0.1 and this squad is served at schema v{schema}",
            details={"client": "0.1", "daemon": schema},
        ),
    )


async def test_a_stale_if_match_answers_409_and_writes_nothing(project, serve, invoke) -> None:
    daemon = serve(project)
    item_id = create_task(daemon, "Read early")
    etag = daemon.get(f"/v1/items/{item_id}").headers["etag"]
    changed = daemon.request("PATCH", f"/v1/items/{item_id}", {"description": "Changed first"})
    assert changed.status == 200
    before = await invoke(["show", "2", "--json"])
    reply = daemon.request(
        "PATCH", f"/v1/items/{item_id}", {"title": "Too late"}, {"If-Match": etag}
    )
    assert whole(reply) == (
        409,
        JSON,
        error(
            "changed_since_read",
            "TASK-2 changed since it was read; nothing was written. Read it again and re-run.",
        ),
    )
    after = await invoke(["show", "2", "--json"])
    assert after.output == before.output
    assert json.loads(after.output)["title"] == "Read early"


@pytest.fixture
def short_lock_wait(monkeypatch) -> Iterator[None]:
    """A store that waits 0.3 s before it says so and gives up after 1.5 s, so a held lock is
    reached within the test."""
    monkeypatch.setattr(index_store, "_LOCK_NOTICE_AFTER", 0.3)
    real = service.IndexStore
    monkeypatch.setattr(service, "IndexStore", lambda *a, **k: real(*a, lock_timeout=1.5, **k))
    yield


def test_a_lock_held_past_the_timeout_answers_423_with_the_waiting_notice(
    project: SquadPaths, serve, short_lock_wait
) -> None:
    daemon = serve(project)
    holder = FileLock(
        str(project.lock_path), thread_local=False, fallback_to_soft=False, preserve_lock_file=True
    )
    holder.acquire(timeout=5)
    try:
        reply = daemon.request(
            "POST", "/v1/items", {"type": "task", "title": "Never written", "author": "manager"}
        )
    finally:
        holder.release()
    assert whole(reply) == (
        423,
        JSON,
        {
            "error": {
                "type": "locked",
                "message": f"the index lock {project.lock_path} is held by another sq process; "
                "nothing was written, retry the command",
                "warnings": [f"waiting for the index lock {project.lock_path}…"],
            }
        },
    )
    assert daemon.get("/v1/items?type=task").json()["data"]["items"] == []


def test_an_option_the_operation_refuses_answers_400_invalid(project, serve) -> None:
    reply = serve(project).request(
        "POST", "/v1/items", {"type": "nonesuch", "title": "T", "author": "manager"}
    )
    assert whole(reply) == (
        400,
        JSON,
        error(
            "invalid",
            "unknown item type 'nonesuch': no spec supplied, or the spec does not declare "
            "this type. Declare it in .overrides/workflow.toml or check for a typo.",
        ),
    )


def test_a_failure_that_is_not_a_squads_error_answers_500_and_logs_the_traceback(
    project, serve, monkeypatch, caplog
) -> None:
    async def boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("the explosion")

    monkeypatch.setattr(local_api, "handler_for", lambda _op: boom)
    daemon = serve(project)
    with caplog.at_level(logging.ERROR, logger="squads.daemon"):
        reply = daemon.get("/v1/items")
    assert whole(reply) == (
        500,
        JSON,
        error("internal", "internal error; the traceback is in the daemon's log"),
    )
    logged = [r for r in caplog.records if r.name == "squads.daemon"]
    assert [(r.levelno, r.exc_info[1].args) for r in logged if r.exc_info] == [
        (logging.ERROR, ("the explosion",))
    ]


def test_a_partial_read_answers_200_with_what_it_left_out(project: SquadPaths, serve) -> None:
    daemon = serve(project)
    posted = daemon.request("POST", "/v1/board", {"body": "A notice"}, {"Squads-Actor": "manager"})
    assert posted.status == 200, posted.body
    broken = board_folder(project) / "BOARD-broken.md"
    broken.write_bytes(b"\xff\xfe not text")
    reply = daemon.get("/v1/board")
    body = reply.json()
    assert (reply.status, reply.headers["content-type"], body["warnings"]) == (200, JSON, [])
    assert [row["body"] for row in body["data"]["items"]] == ["A notice"]
    assert body["omitted"] == [
        {
            "source": "board/BOARD-broken.md",
            "message": f"{broken} is not valid UTF-8: byte 0xff at offset 0 — invalid start byte",
            "code": "unreadable",
        }
    ]


def test_a_route_the_table_does_not_hold_answers_404_not_found(project, serve) -> None:
    reply = serve(project).get("/v1/nowhere")
    assert whole(reply) == (404, JSON, error("not_found", "no such route"))
