"""What the router answers where no operation does: a path nothing serves, a method a path lacks
(with every method it does serve) and the operations that are never served."""

import re

from squads._api._ops import OPERATIONS, ROUTED_OPERATIONS
from squads._paths import SquadPaths

JSON = "application/json"


def test_a_squad_creating_operation_has_no_route(project: SquadPaths, serve) -> None:
    daemon = serve(project)
    assert [op.name for op in OPERATIONS if op.local_only] == ["squad.init", "squad.adopt"]
    for target in ("/v1/squad/init", "/v1/squad/adopt"):
        reply = daemon.request("POST", target, {})
        assert (reply.status, reply.headers["content-type"], reply.json()) == (
            404,
            JSON,
            {"error": {"type": "not_found", "message": "no such route", "warnings": []}},
        )


def test_a_method_a_path_lacks_answers_405_naming_every_method_it_serves(
    project: SquadPaths, serve
) -> None:
    daemon = serve(project)
    served: dict[str, set[str]] = {}
    for op in ROUTED_OPERATIONS:
        method, path = op.route
        served.setdefault(path, set()).add(method)
        if method == "GET":
            served[path].add("HEAD")
    for path, methods in [
        *served.items(),
        ("/v1/daemon", {"GET", "HEAD"}),
        ("/v1/openapi.json", {"GET", "HEAD"}),
    ]:
        refused = next(m for m in ("PUT", "PATCH", "DELETE", "POST") if m not in methods)
        target = re.sub(r"\{\w+\}", "x", path)
        reply = daemon.request(refused, target)
        expected = ", ".join(sorted(methods | allowed_elsewhere(target, served)))
        assert (reply.status, reply.headers.get("allow")) == (405, expected), (refused, path)
        assert reply.json()["error"]["type"] == "invalid"


def allowed_elsewhere(target: str, served: dict[str, set[str]]) -> set[str]:
    """The methods other templates matching *target* serve (a literal path beside a parameter)."""
    found: set[str] = set()
    for path, methods in served.items():
        pattern = re.sub(r"\\\{\w+\\\}", "[^/]+", re.escape(path))
        if re.fullmatch(pattern, target):
            found |= methods
    return found


def test_a_stale_if_match_on_a_skill_link_answers_409(seeded_project: SquadPaths, serve) -> None:
    daemon = serve(seeded_project)
    etag = daemon.get("/v1/skills/greeting").headers["etag"]
    daemon.request("POST", "/v1/skills/greeting/link-role", {"role": "manager"})
    reply = daemon.request(
        "POST", "/v1/skills/greeting/unlink-role", {"role": "manager"}, {"If-Match": etag}
    )
    assert (reply.status, reply.json()["error"]["type"]) == (409, "changed_since_read")
