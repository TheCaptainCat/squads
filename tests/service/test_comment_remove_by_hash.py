"""``remove_comment``: the author deletes one comment; everything else in the file stays
byte-identical, an emptied region keeps its markers, and the same refusals as an edit apply."""

import itertools

import pytest

from _comment_scene import SHAPES, Scene, scene
from squads import _discussion as discussion
from squads import _sections as sections
from squads._errors import SquadsError
from squads._index._reflog import reflog_path

POSITIONS = {"first": (3, 0), "middle": (3, 1), "last": (3, 2), "only": (1, 0)}


def _rows():
    for pos, shape, sub, pre in itertools.product(POSITIONS, SHAPES, (False, True), (False, True)):
        label = f"{pos}-{shape}-{'sub' if sub else 'item'}-{'pre' if pre else 'bare'}"
        yield pytest.param(pos, shape, sub, pre, id=label)


@pytest.mark.parametrize(("pos", "shape", "sub", "pre"), _rows())
async def test_a_removal_takes_only_the_comments_own_lines(svc, pos, shape, sub, pre) -> None:
    count, i = POSITIONS[pos]
    texts = [f"neighbour {n}" for n in range(count)]
    texts[i] = SHAPES[shape]
    built = await scene(svc, texts, sub=sub, preamble="Notes before the comments." if pre else "")
    target = (await built.comments())[i]
    old = sections.split_lines(built.body(), keepends=True)
    start = old.index(f"- [{target.timestamp}] `manager` Catherine Manager:\n")
    end = start + 1
    while end < len(old) and not old[end].startswith(("- [", "<!--")):
        end += 1

    res = await svc.remove_comment(built.item_id, target.hash[:8], as_slug="manager", sub=built.sub)

    assert sections.split_lines(built.body(), keepends=True) == old[:start] + old[end:]
    assert [c.hash for c in res.removed] == [target.hash]
    assert target.hash not in [c.hash for c in await built.comments()]


async def test_removing_the_only_comment_keeps_the_markers(svc) -> None:
    built = await scene(svc, ["alone"])
    (target,) = await built.comments()

    await svc.remove_comment(built.item_id, target.hash[:7], as_slug="manager")

    assert built.region() == "\n"
    assert await built.comments() == []


async def test_removing_a_comment_leaves_the_others_hashes_valid(svc) -> None:
    built = await scene(svc, ["a", "b", "c"])
    first, second, third = await built.comments()

    await svc.remove_comment(built.item_id, second.hash[:7], as_slug="manager")

    assert [c.hash for c in await built.comments()] == [first.hash, third.hash]


async def test_a_second_removal_with_the_same_hash_finds_nothing(svc) -> None:
    built = await scene(svc, ["a", "b"])
    first, _ = await built.comments()
    await svc.remove_comment(built.item_id, first.hash[:7], as_slug="manager")

    with pytest.raises(SquadsError, match="edited or removed since it was read"):
        await svc.remove_comment(built.item_id, first.hash[:7], as_slug="manager")


# ------------------------------------------------------------------ refusals


def _bytes(built: Scene) -> tuple[bytes, bytes]:
    log = reflog_path(built.svc.paths.squad_dir)
    return built.path.read_bytes(), log.read_bytes() if log.exists() else b""


async def _refused(svc, built: Scene, token: str, as_slug: str, match: str) -> None:
    before = _bytes(built)
    with pytest.raises(SquadsError, match=match):
        await svc.remove_comment(built.item_id, token, as_slug=as_slug, sub=built.sub)
    assert _bytes(built) == before


async def test_a_different_author_is_refused(svc) -> None:
    await svc.add_operator("Pierre Chat")
    built = await scene(svc, ["mine"])
    (c,) = await built.comments()

    await _refused(svc, built, c.hash[:7], "op-pierre", "written by manager; --as op-pierre")


async def test_a_system_entry_can_not_be_removed_by_anyone(svc) -> None:
    built = await scene(svc, ["mine"])
    entry = discussion.format_comment("2026-06-07T09:00:00Z", "squads", "squads", ["moved"])
    built.set_region(built.region() + entry + "\n")
    system = [c for c in await built.comments() if c.author_slug == "squads"]

    await _refused(svc, built, system[0].hash[:7], "manager", "written by squads")
    await _refused(svc, built, system[0].hash[:7], "squads", "reserved for system entries")


async def test_a_legacy_shaped_line_is_refused(svc) -> None:
    built = await scene(svc, ["mine"])
    built.set_region(built.region() + "- [2026-01-01T00:00:00Z] Old Name:\n  - old\n")
    c = (await built.comments())[0]

    await _refused(svc, built, c.hash[:7], "manager", r"line \d+ looks like a comment header")


async def test_a_hash_of_another_discussion_of_the_item_names_where_it_lives(svc) -> None:
    built = await scene(svc, ["sub only"], sub=True)
    (c,) = await built.comments()

    with pytest.raises(SquadsError, match=r"it is in subtask ST1 \(sq task \d+ subtask 1 comment"):
        await svc.remove_comment(built.item_id, c.hash[:7], as_slug="manager")
