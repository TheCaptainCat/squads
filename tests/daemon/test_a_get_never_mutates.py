"""Every GET operation of the table leaves every file of the squad as it found it."""

import hashlib
import re
from pathlib import Path

from squads._api._ops import ROUTED_OPERATIONS
from squads._paths import SquadPaths
from tests._daemon_harness import Served

MANAGER = {"Squads-Actor": "manager"}


def snapshot(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def comment_hash(daemon: Served, target: str) -> str:
    reply = daemon.request("POST", target, {"texts": ["a comment"]}, MANAGER)
    assert reply.status == 200, reply.body
    return str(reply.json()["data"]["entry"]["hash"])


def seed(daemon: Served) -> dict[str, str]:
    """An item with a sub-entity, a memory, a notice and a comment on every discussion host, and
    the values the path and query parameters of the GET operations take."""
    created = daemon.request(
        "POST", "/v1/items", {"type": "task", "title": "Seen", "author": "manager"}
    )
    task = created.json()["data"]["id"]
    daemon.request("POST", f"/v1/items/{task}/subentities", {"kind": "subtask", "title": "Step"})
    daemon.request("POST", "/v1/operators", {"name": "Op Person"})
    daemon.request("POST", "/v1/board", {"body": "A notice"}, MANAGER)
    daemon.request(
        "POST", "/v1/memory/manager", {"role": "manager", "summary": "A fact", "slug": "fact"}
    )
    return {
        "id": task,
        "local": "ST1",
        "slug": "manager",
        "role": "manager",
        "root": task,
        "q": "Seen",
        "query": "fact",
        "name": "role_definition",
        "item": "ROLE-1",
        "item_hash": comment_hash(daemon, f"/v1/items/{task}/comments"),
        "sub_hash": comment_hash(daemon, f"/v1/items/{task}/subentities/ST1/comments"),
        "roles_hash": comment_hash(daemon, "/v1/roles/manager/comments"),
        "skills_hash": comment_hash(daemon, "/v1/skills/greeting/comments"),
        "operators_hash": comment_hash(daemon, "/v1/operators/op-op/comments"),
        "roles_addr": "manager",
        "skills_addr": "greeting",
        "operators_addr": "op-op",
    }


def fill(path: str, values: dict[str, str]) -> tuple[str, dict[str, str]]:
    """*path* with its parameters filled from *values*, and the query a GET of it needs."""
    kind = path.split("/")[2]
    scope = "sub" if "/subentities/{local}/comments" in path else "item"
    own: dict[str, str] = {}
    if "{hash}" in path:
        own["hash"] = values[f"{scope}_hash" if kind == "items" else f"{kind}_hash"]
    if kind == "memory":
        own["slug"] = "fact"
    if "{addr}" in path:
        own["addr"] = values[f"{kind}_addr"]
    filled = re.sub(r"\{(\w+)\}", lambda m: own.get(m[1]) or values[m[1]], path)
    return filled, values


def test_every_get_operation_leaves_every_file_of_the_squad_as_it_found_it(
    seeded_project: SquadPaths, serve
) -> None:
    daemon = serve(seeded_project)
    values = seed(daemon)
    before = snapshot(seeded_project.root)
    gets = [op for op in ROUTED_OPERATIONS if op.method == "GET"]
    assert len(gets) > 50
    refused: list[str] = []
    for op in gets:
        path, _ = fill(op.route[1], values)
        required = {
            name
            for name, field in op.request.model_fields.items()
            if field.is_required() and "{" + name + "}" not in op.route[1]
        }
        query = "&".join(f"{name}={values[name]}" for name in sorted(required))
        reply = daemon.get(f"{path}?{query}" if query else path, MANAGER)
        if reply.status != 200:
            refused.append(f"{op.name} {path}: {reply.status} {reply.body[:100]!r}")
    assert not refused, "\n".join(refused)
    assert snapshot(seeded_project.root) == before
