"""Every operation under an item or a roster entry, and every creation, answers the ETag of the item
it addressed, with any method; it answers none only when the item's file is gone."""

from typing import Any

from squads._api._ops import ROUTED_OPERATIONS, carries_etag
from squads._paths import SquadPaths
from tests._daemon_harness import Reply, Served
from tests.daemon.test_etags import etag_of_file

#: Operations that answer no ETag because the file they addressed no longer exists.
GONE = frozenset({"items.remove", "roles.remove", "skills.remove", "operators.remove"})

#: Operations a role or a skill whose body renders through its declared view refuses; the refusal
#: carries no ETag, and the view tag cannot be disabled on it.
REFUSED = frozenset({"roles.view_disable", "skills.view_disable"})

MANAGER = {"Squads-Actor": "manager"}


class Scenario:
    """Calls operations of the table by name and keeps the reply of each."""

    def __init__(self, daemon: Served) -> None:
        self.daemon = daemon
        self.replies: dict[str, Reply] = {}
        self.operations = {op.name: op for op in ROUTED_OPERATIONS}

    def call(
        self,
        name: str,
        params: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Reply:
        method, path = self.operations[name].route
        reply = self.daemon.request(method, path.format(**(params or {})), body, headers)
        self.replies[name] = reply
        return reply


def run_scenario(daemon: Served) -> Scenario:
    s = Scenario(daemon)
    items(s)
    roles(s)
    skills(s)
    operators(s)
    return s


def items(s: Scenario) -> None:
    task = s.call("items.create", body={"type": "task", "title": "A", "author": "manager"}).json()[
        "data"
    ]["id"]
    item = {"id": task}
    s.call("items.show", item)
    s.call("items.refs", item)
    s.call("items.comments", item)
    s.call("items.subentities.list", item)
    s.call("items.status", item, {"status": "Ready"})
    s.call("items.update", item, {"description": "d"})
    s.call("items.body", item, {"text": "b"})
    s.call("items.ref_add", item, {"target": "ROLE-1"})
    s.call("items.ref_rm", {**item, "target": "ROLE-1"})
    comment = s.call("items.comments.add", item, {"texts": ["hi"]}, MANAGER)
    digest = comment.json()["data"]["entry"]["hash"]
    s.call("items.comments.show", {**item, "hash": digest})
    s.call("items.comments.removal", {**item, "hash": digest}, headers=MANAGER)
    edited = s.call("items.comments.edit", {**item, "hash": digest}, {"texts": ["ho"]}, MANAGER)
    digest = edited.json()["data"]["hash"]
    s.call("items.subentities.add", item, {"kind": "subtask", "title": "S"})
    sub = {**item, "local": "ST1"}
    s.call("items.subentities.show", sub)
    s.call("items.subentities.update", sub, {"title": "S2"})
    s.call("items.subentities.body", sub, {"text": "x"})
    note = s.call("items.subentities.comments.add", sub, {"texts": ["hi"]}, MANAGER)
    sub_digest = note.json()["data"]["entry"]["hash"]
    s.call("items.subentities.comments.show", {**sub, "hash": sub_digest})
    s.call("items.subentities.comments.removal", {**sub, "hash": sub_digest}, headers=MANAGER)
    changed = s.call(
        "items.subentities.comments.edit", {**sub, "hash": sub_digest}, {"texts": ["ho"]}, MANAGER
    )
    sub_digest = changed.json()["data"]["hash"]
    s.call("items.subentities.comments.remove", {**sub, "hash": sub_digest}, headers=MANAGER)
    s.call("items.subentities.remove", sub)
    s.call("items.comments.remove", {**item, "hash": digest}, headers=MANAGER)
    retyped = s.call("items.retype", item, {"target": "bug"})
    s.call("items.remove", {"id": retyped.json()["data"]["entry"]["id"]})
    milestone = s.call(
        "items.create", body={"type": "milestone", "title": "M", "author": "manager"}
    ).json()["data"]["id"]
    s.call("items.view_add", {"id": milestone}, {"name": "milestone_rollup"})
    s.call("items.view_disable", {"id": milestone, "name": "milestone_rollup"})


def roles(s: Scenario) -> None:
    role = {"addr": "manager"}
    s.call("roles.show", role)
    s.call("roles.comments", role)
    note = s.call("roles.comments.add", role, {"texts": ["hi"]}, MANAGER)
    digest = note.json()["data"]["entry"]["hash"]
    s.call("roles.comments.show", {**role, "hash": digest})
    s.call("roles.comments.removal", {**role, "hash": digest}, headers=MANAGER)
    edited = s.call("roles.comments.edit", {**role, "hash": digest}, {"texts": ["ho"]}, MANAGER)
    digest = edited.json()["data"]["hash"]
    s.call("roles.comments.remove", {**role, "hash": digest}, headers=MANAGER)
    s.call("roles.update", role, {"title": "Boss"})
    s.call("roles.body", role, {"text": "t"})
    s.call("roles.set_default", role)
    s.call("roles.regen", role)
    s.call("roles.view_add", role, {"name": "role_definition"})
    s.call("roles.view_disable", {**role, "name": "role_definition"})
    s.call("roles.activate", body={"slug": "architect"}, headers=MANAGER)
    s.call(
        "roles.add",
        body={
            "slug": "scout",
            "name": "Scout",
            "job_title": "scout",
            "description": "d",
            "mission": "m",
        },
        headers=MANAGER,
    )
    s.call("roles.status", {"addr": "architect"}, {"status": "Archived"})
    s.call("roles.remove", {"addr": "architect"}, {"purge": True})


def skills(s: Scenario) -> None:
    skill = {"addr": "greeting"}
    s.call("skills.show", skill)
    s.call("skills.refs", skill)
    s.call("skills.comments", skill)
    note = s.call("skills.comments.add", skill, {"texts": ["hi"]}, MANAGER)
    digest = note.json()["data"]["entry"]["hash"]
    s.call("skills.comments.show", {**skill, "hash": digest})
    s.call("skills.comments.removal", {**skill, "hash": digest}, headers=MANAGER)
    edited = s.call("skills.comments.edit", {**skill, "hash": digest}, {"texts": ["ho"]}, MANAGER)
    digest = edited.json()["data"]["hash"]
    s.call("skills.comments.remove", {**skill, "hash": digest}, headers=MANAGER)
    s.call("skills.regen", skill)
    s.call("skills.ref_add", skill, {"target": "ROLE-1"})
    s.call("skills.ref_rm", {**skill, "target": "ROLE-1"})
    s.call("skills.link_role", skill, {"role": "manager"})
    s.call("skills.unlink_role", skill, {"role": "manager"})
    s.call("skills.view_add", skill, {"name": "greeting_skill"})
    s.call("skills.view_disable", {**skill, "name": "greeting_skill"})
    s.call(
        "skills.add",
        body={"name": "probe", "description": "d", "when_to_use": "w", "allowed_tools": ""},
    )
    probe = {"addr": "probe"}
    s.call("skills.update", probe, {"title": "Probe"})
    s.call("skills.body", probe, {"text": "t"})
    s.call("skills.status", probe, {"status": "Archived"})
    s.call("skills.remove", probe, {"purge": True})


def operators(s: Scenario) -> None:
    added = s.call("operators.add", body={"name": "Op Person"})
    operator = {"addr": added.json()["data"]["entry"]["slug"]}
    s.call("operators.show", operator)
    s.call("operators.comments", operator)
    note = s.call("operators.comments.add", operator, {"texts": ["hi"]}, MANAGER)
    digest = note.json()["data"]["entry"]["hash"]
    s.call("operators.comments.show", {**operator, "hash": digest})
    s.call("operators.comments.removal", {**operator, "hash": digest}, headers=MANAGER)
    edited = s.call(
        "operators.comments.edit", {**operator, "hash": digest}, {"texts": ["ho"]}, MANAGER
    )
    digest = edited.json()["data"]["hash"]
    s.call("operators.comments.remove", {**operator, "hash": digest}, headers=MANAGER)
    s.call("operators.update", operator, {"title": "O"})
    s.call("operators.body", operator, {"text": "t"})
    s.call("operators.status", operator, {"status": "Archived"})
    s.call("operators.remove", operator, {"purge": True})


def test_every_operation_under_an_item_answers_its_etag(seeded_project: SquadPaths, serve) -> None:
    scenario = run_scenario(serve(seeded_project))
    selected = {op.name for op in ROUTED_OPERATIONS if carries_etag(op)}
    assert set(scenario.replies) >= selected, sorted(selected - set(scenario.replies))
    wrong: list[str] = []
    for name in sorted(selected):
        reply = scenario.replies[name]
        if name in REFUSED:
            if reply.status != 400 or "etag" in reply.headers:
                wrong.append(f"{name}: expected a refusal without an ETag, got {reply.status}")
        elif reply.status != 200:
            wrong.append(f"{name}: answered {reply.status} {reply.body[:120]!r}")
        elif ("etag" in reply.headers) == (name in GONE):
            wrong.append(
                f"{name}: ETag header {'present' if 'etag' in reply.headers else 'absent'}"
            )
    assert not wrong, "\n".join(wrong)


def test_the_etag_a_roster_read_answers_is_the_hash_of_its_file(
    seeded_project: SquadPaths, serve
) -> None:
    daemon = serve(seeded_project)
    reply = daemon.get("/v1/roles/manager")
    path = seeded_project.squad_dir / "agents/roles/ROLE-000001-manager.md"
    assert reply.headers["etag"] == etag_of_file(path)
