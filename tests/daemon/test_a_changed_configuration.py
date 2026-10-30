"""A daemon whose configuration changed answers `retiring` and runs nothing, and a GET never
mutates the squad."""

import hashlib
from pathlib import Path

import pytest

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


def snapshot(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_get_requests_leave_every_file_of_the_squad_as_they_found_it(
    project: SquadPaths, serve
) -> None:
    daemon = serve(project)
    daemon.request("POST", "/v1/items", {"type": "task", "title": "Seen", "author": "manager"})
    before = snapshot(project.root)
    for target in (
        "/v1/items",
        "/v1/items/TASK-2",
        "/v1/items/TASK-2/comments",
        "/v1/tree",
        "/v1/search?q=Seen",
        "/v1/reflog",
        "/v1/check",
        "/v1/board",
        "/v1/roles",
        "/v1/workflow/types",
        "/v1/daemon",
        "/v1/openapi.json",
    ):
        assert daemon.get(target).status == 200, target
    assert snapshot(project.root) == before
