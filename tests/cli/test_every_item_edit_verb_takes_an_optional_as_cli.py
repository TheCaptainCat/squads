"""Every verb that edits one addressed item, sub-entity or roster entry takes an optional
`--as SLUG`, validated as a comment's is and recorded as the reflog actor; without it the
actor stays `system`, and a refused `--as` writes nothing."""

import json
from typing import Any

import pytest

pytestmark = pytest.mark.anyio

#: Setup argv lists run (as `system`) before the verb; each verb row is
#: name -> (setup, verb argv without `--as`).
_ITEM = ["task", "2"]
_SETUP_TASK = [["create", "task", "T", "--author", "manager"]]
_SETUP_TWO = [*_SETUP_TASK, ["create", "bug", "B", "--author", "manager"]]
_SETUP_SUB = [*_SETUP_TASK, [*_ITEM, "add-subtask", "Child"]]
_SETUP_FEATURE = [["create", "feature", "F", "--author", "manager"]]
_SETUP_REVIEW = [["create", "review", "R", "--author", "manager"]]
_SETUP_FINDING = [*_SETUP_REVIEW, ["review", "2", "add-finding", "Off by one"]]
_SETUP_MILESTONE = [["create", "milestone", "M", "--author", "manager"]]

_WORK_ITEM_VERBS = {
    "status": (_SETUP_TASK, [*_ITEM, "status", "InProgress"]),
    "update": (_SETUP_TASK, [*_ITEM, "update", "--title", "Renamed"]),
    "update --status": (_SETUP_TASK, [*_ITEM, "update", "--status", "InProgress"]),
    "body": (_SETUP_TASK, [*_ITEM, "body", "-m", "A body"]),
    "ref add": (_SETUP_TWO, [*_ITEM, "ref", "add", "3"]),
    "ref rm": (
        [*_SETUP_TWO, [*_ITEM, "ref", "add", "3"]],
        [*_ITEM, "ref", "rm", "3"],
    ),
    "retype": (_SETUP_TASK, [*_ITEM, "retype", "bug"]),
    "remove": (_SETUP_TASK, [*_ITEM, "remove", "--yes"]),
    "view add": (
        [*_SETUP_MILESTONE, ["milestone", "2", "view", "disable", "milestone_rollup"]],
        ["milestone", "2", "view", "add", "milestone_rollup"],
    ),
    "view disable": (_SETUP_MILESTONE, ["milestone", "2", "view", "disable", "milestone_rollup"]),
}

_SUBENTITY_VERBS = {
    "add-subtask": (_SETUP_TASK, [*_ITEM, "add-subtask", "Child"]),
    "add-story": (_SETUP_FEATURE, ["feature", "2", "add-story", "A story"]),
    "add-finding": (_SETUP_REVIEW, ["review", "2", "add-finding", "Off by one"]),
    "subtask update": (_SETUP_SUB, [*_ITEM, "subtask", "1", "update", "--title", "Renamed"]),
    "subtask update --status": (
        _SETUP_SUB,
        [*_ITEM, "subtask", "1", "update", "--status", "InProgress"],
    ),
    "finding update": (_SETUP_FINDING, ["review", "2", "finding", "1", "update", "--title", "X"]),
    "subtask body": (_SETUP_SUB, [*_ITEM, "subtask", "1", "body", "-m", "A body"]),
    "subtask remove": (_SETUP_SUB, [*_ITEM, "subtask", "1", "remove", "--yes"]),
}

_ROSTER_SETUP = [
    ["role", "activate", "architect"],
    ["skill", "add", "Pairing"],
    ["operator", "add", "Pierre Chat"],
]

_ROSTER_VERBS = {
    "role update": (_ROSTER_SETUP, ["role", "architect", "update", "--model", "opus"]),
    "role set-default": (_ROSTER_SETUP, ["role", "architect", "set-default"]),
    "role status": (_ROSTER_SETUP, ["role", "architect", "status", "Archived"]),
    "role remove": (
        [*_ROSTER_SETUP, ["role", "architect", "status", "Archived"]],
        ["role", "architect", "remove", "--purge"],
    ),
    "skill update": (_ROSTER_SETUP, ["skill", "pairing", "update", "--title", "Pairing 2"]),
    "skill status": (_ROSTER_SETUP, ["skill", "pairing", "status", "Archived"]),
    "skill body": (_ROSTER_SETUP, ["skill", "pairing", "body", "-m", "A body"]),
    "skill remove": (
        [*_ROSTER_SETUP, ["skill", "pairing", "status", "Archived"]],
        ["skill", "pairing", "remove", "--purge"],
    ),
    "skill link-role": (_ROSTER_SETUP, ["skill", "pairing", "link-role", "architect"]),
    "skill unlink-role": (
        [*_ROSTER_SETUP, ["skill", "pairing", "link-role", "architect"]],
        ["skill", "pairing", "unlink-role", "architect"],
    ),
    "skill ref add": (_ROSTER_SETUP, ["skill", "pairing", "ref", "add", "1"]),
    "skill ref rm": (
        [*_ROSTER_SETUP, ["skill", "pairing", "ref", "add", "1"]],
        ["skill", "pairing", "ref", "rm", "1"],
    ),
    "operator update": (_ROSTER_SETUP, ["operator", "op-pierre", "update", "--title", "Pierre"]),
    "operator status": (_ROSTER_SETUP, ["operator", "op-pierre", "status", "Archived"]),
    "operator body": (_ROSTER_SETUP, ["operator", "op-pierre", "body", "-m", "A body"]),
    "operator remove": (
        [*_ROSTER_SETUP, ["operator", "op-pierre", "status", "Archived"]],
        ["operator", "op-pierre", "remove", "--purge"],
    ),
}

_CREATE_VERBS = {
    "skill add": ([], ["skill", "add", "Pairing"]),
    "operator add": ([], ["operator", "add", "Pierre Chat"]),
    "role activate": ([], ["role", "activate", "architect"]),
    "role add": (
        [],
        [
            "role",
            "add",
            "scout",
            "--name",
            "Scout",
            "--job-title",
            "Scout",
            "--desc",
            "d",
            "--mission",
            "m",
        ],
    ),
    "dev add": ([], ["dev", "add", "--tech", "python"]),
}

_VERBS = {**_CREATE_VERBS, **_WORK_ITEM_VERBS, **_SUBENTITY_VERBS, **_ROSTER_VERBS}


async def _reflog(invoke) -> list[dict[str, Any]]:
    result = await invoke(["reflog", "--tail", "0", "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


async def _run_setup(invoke, setup: list[list[str]]) -> int:
    for argv in setup:
        result = await invoke(argv)
        assert result.exit_code == 0, (argv, result.output)
    return len(await _reflog(invoke))


@pytest.mark.parametrize("verb", list(_VERBS))
async def test_the_reflog_actor_is_the_as_slug_when_given_and_system_when_not(
    project, invoke, verb: str
) -> None:
    setup, argv = _VERBS[verb]
    before = await _run_setup(invoke, setup)

    result = await invoke([*argv, "--as", "manager"])

    assert result.exit_code == 0, result.output
    written = (await _reflog(invoke))[before:]
    assert written
    assert {line["actor"] for line in written} == {"manager"}


@pytest.mark.parametrize("verb", list(_VERBS))
async def test_a_verb_without_as_still_records_system(project, invoke, verb: str) -> None:
    setup, argv = _VERBS[verb]
    before = await _run_setup(invoke, setup)

    result = await invoke(argv)

    assert result.exit_code == 0, result.output
    written = (await _reflog(invoke))[before:]
    assert written
    assert {line["actor"] for line in written} == {"system"}


_REFUSED_VERBS = (
    "status",
    "update",
    "remove",
    "subtask update --status",
    "role status",
    "skill link-role",
    "operator update",
)


@pytest.mark.parametrize("slug", ["nobody", "system", ""], ids=["unknown", "system", "empty"])
@pytest.mark.parametrize("verb", _REFUSED_VERBS)
async def test_a_refused_as_exits_1_and_writes_nothing(
    project, invoke, verb: str, slug: str
) -> None:
    setup, argv = _VERBS[verb]
    before = await _run_setup(invoke, setup)

    result = await invoke([*argv, "--as", slug])

    assert result.exit_code == 1, result.output
    assert len(await _reflog(invoke)) == before
    if slug == "nobody":
        assert "manager" in result.output


async def test_an_unlink_retirement_attributes_every_line_it_writes(project, invoke) -> None:
    before = await _run_setup(
        invoke, [*_ROSTER_SETUP, ["skill", "pairing", "link-role", "architect"]]
    )

    result = await invoke(["skill", "pairing", "status", "Archived", "--unlink", "--as", "manager"])

    assert result.exit_code == 0, result.output
    written = (await _reflog(invoke))[before:]
    assert {line["op"] for line in written} >= {"status", "ref"}
    assert {line["actor"] for line in written} == {"manager"}
