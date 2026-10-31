"""The ETag a read and a write answer with: the SHA-256 of the item file's bytes."""

import hashlib
from pathlib import Path

from squads._paths import SquadPaths


def etag_of_file(path: Path) -> str:
    return f'"{hashlib.sha256(path.read_bytes()).hexdigest()}"'


def test_a_read_answers_the_etag_of_the_file_it_read(project: SquadPaths, serve) -> None:
    daemon = serve(project)
    made = daemon.request(
        "POST", "/v1/items", {"type": "task", "title": "Read me", "author": "manager"}
    )
    path = project.squad_dir / made.json()["data"]["path"]
    reply = daemon.get("/v1/items/TASK-2")
    assert reply.status == 200
    assert reply.headers["etag"] == etag_of_file(path)
    assert reply.json()["data"]["etag"] == etag_of_file(path)


def test_a_write_answers_the_etag_of_the_file_it_wrote(project: SquadPaths, serve) -> None:
    daemon = serve(project)
    created = daemon.request(
        "POST", "/v1/items", {"type": "task", "title": "Write me", "author": "manager"}
    )
    path = project.squad_dir / created.json()["data"]["path"]
    assert created.headers["etag"] == etag_of_file(path)
    renamed = daemon.request(
        "PATCH", "/v1/items/TASK-2", {"title": "Renamed"}, {"If-Match": created.headers["etag"]}
    )
    moved = project.squad_dir / renamed.json()["data"]["entry"]["path"]
    assert moved != path
    assert renamed.headers["etag"] == etag_of_file(moved)
    removed = daemon.request("DELETE", "/v1/items/TASK-2")
    assert (removed.status, "etag" in removed.headers) == (200, False)
