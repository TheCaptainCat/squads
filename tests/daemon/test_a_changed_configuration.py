"""A daemon whose configuration changed answers `retiring` and runs nothing."""

import threading
import time

import pytest
from filelock import FileLock

from squads._paths import SquadPaths

pytestmark = pytest.mark.anyio


def test_a_vocabulary_mismatch_on_a_changed_configuration_answers_retiring(
    project: SquadPaths, serve
) -> None:
    daemon = serve(project, retirement_check=lambda: True)
    reply = daemon.get("/v1/items", {"Squads-Vocabulary": "0" * 64})
    assert (reply.status, reply.headers["content-type"], reply.json()) == (
        503,
        "application/json",
        {"not_executed": "retiring"},
    )


def test_a_request_queued_behind_another_is_checked_when_its_turn_comes(
    project: SquadPaths, serve
) -> None:
    changed = threading.Event()
    daemon = serve(project, retirement_check=changed.is_set)
    holder = FileLock(
        str(project.lock_path), thread_local=False, fallback_to_soft=False, preserve_lock_file=True
    )
    holder.acquire(timeout=5)
    replies: dict[str, object] = {}

    def send(label: str, method: str, target: str, body: dict[str, object] | None) -> None:
        replies[label] = daemon.request(method, target, body)

    first = threading.Thread(
        target=send,
        args=("write", "POST", "/v1/items", {"type": "task", "title": "T", "author": "manager"}),
    )
    first.start()
    time.sleep(0.5)
    second = threading.Thread(target=send, args=("read", "GET", "/v1/items", None))
    second.start()
    time.sleep(0.5)
    changed.set()
    holder.release()
    first.join(30)
    second.join(30)
    read = replies["read"]
    assert (read.status, read.json()) == (503, {"not_executed": "retiring"})  # type: ignore[attr-defined]
