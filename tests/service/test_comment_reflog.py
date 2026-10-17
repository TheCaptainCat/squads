"""``comment_edit`` and ``comment_remove`` leave one reflog line per change, whose delta holds
one entry per comment touched; a no-op and a refusal leave none."""

import pytest

from _comment_scene import Scene, at, scene
from squads._errors import SquadsError
from squads._index._reflog import REFLOG_OPS, read_lines, reflog_path

pytestmark = pytest.mark.anyio


async def _lines(built: Scene, op: str):
    return [ln for ln in await read_lines(reflog_path(built.svc.paths.squad_dir)) if ln.op == op]


def test_the_closed_vocabulary_lists_both_ops() -> None:
    assert {"comment_edit", "comment_remove"} <= set(REFLOG_OPS)


@pytest.mark.parametrize("sub", [False, True], ids=["item", "subentity"])
async def test_an_edit_logs_the_comment_as_it_was_and_the_new_hash(svc, sub) -> None:
    built = await scene(svc, ["before text", "other"], sub=sub)
    target = (await built.comments())[0]
    at(900)

    res = await svc.edit_comment(
        built.item_id, target.hash[:7], ["after"], as_slug="manager", sub=built.sub
    )

    (line,) = await _lines(built, "comment_edit")
    assert line.target == built.item_id
    assert line.actor
    assert line.delta == {
        "comments": [
            {
                "author": "manager",
                "hash": target.hash,
                "region": built.tag,
                "ts": target.timestamp,
                "before": "- before text",
                "after_hash": res.new.hash,
            }
        ]
    }


async def test_a_removal_logs_the_comment_as_it_was(svc) -> None:
    built = await scene(svc, ["gone text", "kept"])
    target = (await built.comments())[0]

    await svc.remove_comment(built.item_id, target.hash[:7], as_slug="manager")

    (line,) = await _lines(built, "comment_remove")
    (entry,) = line.delta["comments"]
    assert entry == {
        "author": "manager",
        "hash": target.hash,
        "region": "discussion",
        "ts": target.timestamp,
        "before": "- gone text",
    }


async def test_a_group_logs_one_entry_per_member(svc) -> None:
    built = await scene(svc, ["twin"])
    built.set_region(built.region() + built.region().lstrip("\n"))
    group = (await built.comments())[0]
    assert len(await built.comments()) == 2
    at(900)

    await svc.edit_comment(built.item_id, group.hash[:7], ["merged"], as_slug="manager")
    merged = (await built.comments())[0]
    await svc.remove_comment(built.item_id, merged.hash[:7], as_slug="manager")

    (edit,) = await _lines(built, "comment_edit")
    (remove,) = await _lines(built, "comment_remove")
    assert [e["hash"] for e in edit.delta["comments"]] == [group.hash, group.hash]
    assert len({e["after_hash"] for e in edit.delta["comments"]}) == 1
    assert len(remove.delta["comments"]) == 1


async def test_a_no_op_edit_and_a_refusal_log_nothing(svc) -> None:
    built = await scene(svc, ["same"])
    target = (await built.comments())[0]
    at(900)

    await svc.edit_comment(built.item_id, target.hash[:7], ["same"], as_slug="manager")
    with pytest.raises(SquadsError):
        await svc.edit_comment(built.item_id, "deadbeef", ["x"], as_slug="manager")
    with pytest.raises(SquadsError):
        await svc.remove_comment(built.item_id, "deadbeef", as_slug="manager")

    assert await _lines(built, "comment_edit") == []
    assert await _lines(built, "comment_remove") == []
