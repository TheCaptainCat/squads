"""Every writer of a discussion comment stamps the header grammar with the author's slug: the
``comment`` verb on an item and on each sub-entity kind, the bulk importer, and the system entries
that retype and the two bulk renames write."""

import json

import pytest

from _helpers import create_item
from squads._errors import SquadsError
from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._sections import get_section

pytestmark = pytest.mark.anyio

TS = "2026-06-07T10:00:00Z"  # the frozen clock of the shared fixtures


def _headers(region: str) -> list[str]:
    return [ln for ln in region.splitlines() if ln.startswith("- [")]


async def _region(svc, item_id: str, tag: str = markers.DISCUSSION) -> str:
    item = await svc.get(item_id)
    text = item_file(svc.paths, item).read_text(encoding="utf-8")
    region = get_section(text, tag)
    assert region is not None
    return region


async def test_the_comment_verb_stamps_slug_and_name_for_each_kind_of_author(svc):
    await svc.add_operator("Pierre Chat")
    task = (await create_item(svc, "task", "Target")).item

    await svc.comment(task.id, ["as a role"], as_slug="manager")
    await svc.comment(task.id, ["as an operator"], as_slug="op-pierre")
    await svc.comment(task.id, ["as the sentinel"], as_slug="operator")

    assert _headers(await _region(svc, task.id)) == [
        f"- [{TS}] `manager` Catherine Manager:",
        f"- [{TS}] `op-pierre` Pierre Chat:",
        f"- [{TS}] `operator` Operator:",
    ]
    assert [(c.author_slug, c.author) for c in await svc.comments(task.id)] == [
        ("manager", "Catherine Manager"),
        ("op-pierre", "Pierre Chat"),
        ("operator", "Operator"),
    ]


@pytest.mark.parametrize(
    ("item_type", "adder", "kwarg", "kind"),
    [
        pytest.param("feature", "add_story", "story", "story", id="story"),
        pytest.param("task", "add_subtask", "subtask", "subtask", id="subtask"),
        pytest.param("review", "add_finding", "finding", "finding", id="finding"),
    ],
)
async def test_the_comment_verb_stamps_the_header_in_each_sub_entity_discussion(
    svc, item_type, adder, kwarg, kind
):
    item = (await create_item(svc, item_type, "Parent")).item
    block = await getattr(svc, adder)(item.id, "A block")

    await svc.comment(item.id, ["on the block"], as_slug="manager", **{kwarg: block.local_id})

    tag = markers.discussion_tag(f"{kind}:{block.local_id}")
    assert _headers(await _region(svc, item.id, tag)) == [f"- [{TS}] `manager` Catherine Manager:"]


async def test_the_bulk_importer_stamps_the_actors_slug(svc):
    task = (await create_item(svc, "task", "Target")).item
    text = json.dumps({"op": "comment", "target": task.id, "message": "imported", "as": "manager"})

    result = await svc.import_events(text)

    assert result.applied is not None, result.plan.issues
    assert _headers(await _region(svc, task.id)) == [f"- [{TS}] `manager` Catherine Manager:"]


@pytest.mark.parametrize("actor", ["Bad Actor", "QA", "has`tick", ""])
async def test_the_bulk_importer_refuses_an_actor_outside_the_slug_grammar_and_writes_nothing(
    svc, actor
):
    task = (await create_item(svc, "task", "Target")).item
    good = {"op": "comment", "target": task.id, "message": "fine", "as": "manager"}
    bad = {"op": "comment", "target": task.id, "message": "refused", "as": actor}
    before = item_file(svc.paths, task).read_bytes()

    result = await svc.import_events("\n".join(json.dumps(e) for e in (good, bad)))

    assert result.applied is None
    assert any(i.line == 2 for i in result.plan.issues)
    assert item_file(svc.paths, task).read_bytes() == before


async def test_a_system_entry_is_written_as_the_squads_slug_by_retype_and_both_renames(svc):
    retyped = (await create_item(svc, "task", "Retype me")).item
    status_renamed = (await create_item(svc, "feature", "Status rename")).item
    await create_item(svc, "epic", "Type rename")

    retyped_id = (await svc.retype(retyped.id, "bug")).item.id
    await svc.rename_status("feature", "Draft", "Ready")
    await svc.rename_type("epic", "milestone")

    type_renamed_id = (await svc.list_items(item_type="milestone"))[0].id
    for item_id in (retyped_id, status_renamed.id, type_renamed_id):
        (header,) = _headers(await _region(svc, item_id))
        assert header == f"- [{TS}] `squads` squads:"
        (system,) = await svc.comments(item_id)
        assert (system.author_slug, system.author) == ("squads", "squads")


async def test_the_comment_writer_refuses_a_slug_outside_the_grammar_before_writing(svc):
    task = (await create_item(svc, "task", "Target")).item
    before = item_file(svc.paths, task).read_bytes()

    with pytest.raises(SquadsError, match="cannot write a comment as"):
        await svc.comment(task.id, ["x"], as_slug="Not A Slug")

    assert item_file(svc.paths, task).read_bytes() == before


async def test_the_bulk_importer_refuses_squads_as_an_actor_and_still_accepts_the_rest(svc):
    task = (await create_item(svc, "task", "Target")).item
    before = item_file(svc.paths, task).read_bytes()
    event = {"op": "comment", "target": task.id, "message": "x", "as": "squads"}

    refused = await svc.import_events(json.dumps(event))

    assert refused.applied is None
    assert "reserved for system entries" in refused.plan.issues[0].message
    assert item_file(svc.paths, task).read_bytes() == before

    for actor in ("ghost", "operator"):
        accepted = await svc.import_events(json.dumps(event | {"as": actor}))
        assert accepted.applied is not None, actor
    assert [c.author_slug for c in await svc.comments(task.id)] == ["ghost", "operator"]
