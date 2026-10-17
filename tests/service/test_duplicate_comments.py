"""A comment equal to one already in its discussion (same author, second and text) is refused on
write and by the importer, tolerated on load, merged by an edit and removed together."""

import json

import pytest

from _comment_scene import Scene, at, scene
from squads import _discussion as discussion
from squads._errors import SquadsError

pytestmark = pytest.mark.anyio


def _twice(region: str) -> str:
    """The region with its last comment written a second time."""
    last = region.rstrip("\n").split("\n- [")[-1]
    entry = last if last.startswith("- [") else "- [" + last
    return region + entry + "\n"


async def _duplicated(svc, *, sub: bool = False) -> Scene:
    built = await scene(svc, ["twin", "other"], sub=sub)
    built.set_region(_twice(built.region()))
    return built


@pytest.mark.parametrize("sub", [False, True], ids=["item", "subentity"])
async def test_writing_the_same_comment_in_the_same_second_is_refused(svc, sub) -> None:
    built = await scene(svc, [], sub=sub)
    at(5)
    await svc.comment(built.item_id, ["same"], as_slug="manager", sub=built.sub)
    before = built.path.read_bytes()

    with pytest.raises(SquadsError, match=r"already has this comment by manager at .* \(\w{7}\)"):
        await svc.comment(built.item_id, ["same"], as_slug="manager", sub=built.sub)

    assert built.path.read_bytes() == before


@pytest.mark.parametrize("sub", [False, True], ids=["item", "subentity"])
async def test_two_different_texts_in_one_second_are_both_accepted(svc, sub) -> None:
    built = await scene(svc, [], sub=sub)
    at(5)
    await svc.comment(built.item_id, ["one"], as_slug="manager", sub=built.sub)
    await svc.comment(built.item_id, ["two"], as_slug="manager", sub=built.sub)

    assert len(await built.comments()) == 2


async def test_the_same_text_in_two_discussions_is_accepted_with_its_own_hash(svc) -> None:
    built = await scene(svc, [], sub=True)
    at(5)
    await svc.comment(built.item_id, ["same"], as_slug="manager")
    await svc.comment(built.item_id, ["same"], as_slug="manager", sub=built.sub)

    item = await svc.get(built.item_id)
    top = await svc.comments(built.item_id)
    sub = (await built.comments())[0]
    assert top[0].hash != sub.hash
    assert item.sequence_id


async def test_the_other_author_may_write_the_same_text_in_the_same_second(svc) -> None:
    await svc.add_operator("Pierre Chat")
    built = await scene(svc, [])
    at(5)
    await svc.comment(built.item_id, ["same"], as_slug="manager")
    await svc.comment(built.item_id, ["same"], as_slug="op-pierre")

    assert len(await built.comments()) == 2


async def test_a_duplicate_group_loads_as_listed_members_with_one_hash(svc) -> None:
    built = await _duplicated(svc)

    cmts = await built.comments()

    assert [c.body for c in cmts] == ["- twin", "- other", "- other"]
    assert cmts[1].hash == cmts[2].hash
    assert discussion.short_hashes(cmts)[1] == discussion.short_hashes(cmts)[2]


async def test_check_does_not_report_a_duplicate_group(svc) -> None:
    built = await scene(svc, ["twin", "other"])
    clean = [i.message for i in await svc.check()]
    built.set_region(_twice(built.region()))

    assert [i.message for i in await svc.check()] == clean


async def test_an_edit_merges_the_group_into_its_first_member(svc) -> None:
    built = await _duplicated(svc)
    group = (await built.comments())[1]
    at(900)

    res = await svc.edit_comment(built.item_id, group.hash[:7], ["merged"], as_slug="manager")

    cmts = await built.comments()
    assert [c.body for c in cmts] == ["- twin", "- merged"]
    assert res.changed
    assert cmts[1].edited_ts is not None


async def test_a_removal_takes_every_member(svc) -> None:
    built = await _duplicated(svc)
    group = (await built.comments())[1]

    res = await svc.remove_comment(built.item_id, group.hash[:7], as_slug="manager")

    assert len(res.removed) == 2
    assert [c.body for c in await built.comments()] == ["- twin"]


async def test_an_edit_that_would_equal_another_comment_is_refused_even_in_a_group(svc) -> None:
    built = await _duplicated(svc)
    twin, group = (await built.comments())[:2]
    built.set_region(built.region().replace(f"- [{group.timestamp}]", f"- [{twin.timestamp}]"))
    group = (await built.comments())[1]
    before = built.path.read_bytes()

    with pytest.raises(SquadsError, match="already has this comment"):
        await svc.edit_comment(built.item_id, group.hash[:7], ["twin"], as_slug="manager")

    assert built.path.read_bytes() == before


async def test_an_import_of_a_duplicate_is_refused_whole_and_writes_nothing(svc) -> None:
    built = await scene(svc, ["keep"])
    other = (await scene(svc, ["x"])).item_id
    before = (built.path.read_bytes(), (await svc.get(other)).updated_at)
    events = [
        {"op": "comment", "target": built.item_id, "message": "fresh", "as": "manager"},
        {
            "op": "comment",
            "target": other,
            "message": "same",
            "as": "manager",
            "at": "2026-07-01T00:00:00Z",
        },
        {
            "op": "comment",
            "target": other,
            "message": "same",
            "as": "manager",
            "at": "2026-07-01T00:00:00Z",
        },
    ]

    with pytest.raises(SquadsError, match="already has this comment"):
        await svc.import_events("\n".join(json.dumps(e) for e in events))

    assert built.path.read_bytes() == before[0]
    assert (await svc.get(other)).updated_at == before[1]
