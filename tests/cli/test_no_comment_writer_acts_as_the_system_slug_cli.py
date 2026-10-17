"""The system slug authors rename and retype entries and nothing else: every comment writer
refuses it, whether or not a roster entry holds it, and writes nothing. The anonymous slug keeps
resolving to the anonymous author before the roster is read."""

import json

import pytest

from _helpers import create_item, squad_tree
from squads._services import _base

pytestmark = pytest.mark.anyio

WRITERS = ["item", "subtask", "board", "import-event-as", "import-default-as"]


@pytest.fixture
async def target(svc):
    item = (await create_item(svc, "task", "Target")).item
    await svc.add_subtask(item.id, "A subtask")
    return item


def _argv(writer: str, slug: str, target, tmp_path) -> list[str]:
    n = str(target.sequence_id)
    if writer == "item":
        return ["task", n, "comment", "--as", slug, "-m", "hello"]
    if writer == "subtask":
        return ["task", n, "subtask", "ST1", "comment", "--as", slug, "-m", "hello"]
    if writer == "board":
        return ["board", "post", "--as", slug, "-m", "hello"]
    event = {"op": "comment", "target": target.id, "message": "hello"}
    path = tmp_path / "events.jsonl"
    if writer == "import-event-as":
        path.write_text(json.dumps({**event, "as": slug}) + "\n", encoding="utf-8")
        return ["import", str(path), "--as", "manager"]
    path.write_text(json.dumps(event) + "\n", encoding="utf-8")
    return ["import", str(path), "--as", slug]


@pytest.fixture(params=["no-holder", "held-by-a-hand-written-operator"])
async def system_slug_roster(request, svc, monkeypatch):
    if request.param == "held-by-a-hand-written-operator":
        with monkeypatch.context() as unchecked:
            unchecked.setattr(_base, "_check_roster_slug", lambda *args, **kwargs: None)
            await svc.add_operator("Sys Op", slug="squads")
    return request.param


@pytest.mark.parametrize("writer", WRITERS)
@pytest.mark.parametrize("slug", ["squads", "Squads", "@squads"])
async def test_every_comment_writer_refuses_the_system_slug_and_writes_nothing(
    project, invoke, target, tmp_path, system_slug_roster, writer, slug
) -> None:
    argv = _argv(writer, slug, target, tmp_path)
    before = squad_tree(project.root)

    r = await invoke(argv)

    assert r.exit_code == 1, r.output
    assert "reserved for system entries" in r.output or "lowercase letters" in r.output
    assert squad_tree(project.root) == before


@pytest.mark.parametrize("writer", WRITERS)
@pytest.mark.parametrize("slug", ["manager", "op-anna"])
async def test_every_comment_writer_still_accepts_a_role_and_an_operator(
    project, invoke, target, tmp_path, writer, slug
) -> None:
    assert (await invoke(["operator", "add", "Anna Lee"])).exit_code == 0
    before = squad_tree(project.root)

    r = await invoke(_argv(writer, slug, target, tmp_path))

    assert r.exit_code == 0, r.output
    assert squad_tree(project.root) != before


@pytest.mark.parametrize("holder", ["no-entry", "an-entry-holds-operator"])
async def test_the_anonymous_slug_names_the_anonymous_author_before_the_roster_is_read(
    project, invoke, svc, target, monkeypatch, holder
) -> None:
    if holder == "an-entry-holds-operator":
        with monkeypatch.context() as unchecked:
            unchecked.setattr(_base, "_check_roster_slug", lambda *args, **kwargs: None)
            await svc.add_operator("Real Name", slug="operator")

    r = await invoke(["task", str(target.sequence_id), "comment", "--as", "operator", "-m", "hi"])

    assert r.exit_code == 0, r.output
    (comment,) = json.loads(
        (await invoke(["task", str(target.sequence_id), "comments", "--json"])).output
    )
    assert (comment["author_slug"], comment["author"]) == ("operator", "Operator")


async def test_a_retype_still_writes_a_system_entry(project, invoke, svc) -> None:
    item = (await create_item(svc, "task", "Plain")).item

    r = await invoke(["task", str(item.sequence_id), "retype", "bug"])

    assert r.exit_code == 0, r.output
    comments = json.loads(
        (await invoke(["bug", str(item.sequence_id), "comments", "--json"])).output
    )
    assert [c["author_slug"] for c in comments] == ["squads"]


@pytest.mark.parametrize("writer", ["item", "board"])
async def test_the_refusal_says_act_as_because_a_board_notice_is_not_a_comment(
    invoke, target, tmp_path, writer
) -> None:
    r = await invoke(_argv(writer, "squads", target, tmp_path))

    assert "cannot act as 'squads': that slug is reserved for system entries" in r.output
