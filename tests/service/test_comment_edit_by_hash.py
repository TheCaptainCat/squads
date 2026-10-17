"""``edit_comment``: the author replaces one comment, keeping its header and position and gaining
an edit mark; everything else in the file stays byte-identical."""

import itertools

import pytest

from _comment_scene import SHAPES, Scene, at, scene
from squads import _discussion as discussion
from squads import _sections as sections
from squads._errors import SquadsError
from squads._index._reflog import reflog_path

POSITIONS = {"first": (3, 0), "middle": (3, 1), "last": (3, 2), "only": (1, 0)}


def _rows():
    for pos, shape, sub, pre in itertools.product(POSITIONS, SHAPES, (False, True), (False, True)):
        yield pytest.param(
            pos,
            shape,
            sub,
            pre,
            id=f"{pos}-{shape}-{'sub' if sub else 'item'}-{'pre' if pre else 'bare'}",
        )


async def _built(svc, pos: str, shape: str, sub: bool, pre: bool) -> tuple[Scene, int]:
    count, at_index = POSITIONS[pos]
    texts = [f"neighbour {n}" for n in range(count)]
    texts[at_index] = SHAPES[shape]
    built = await scene(svc, texts, sub=sub, preamble="Notes before the comments." if pre else "")
    return built, at_index


@pytest.mark.parametrize(("pos", "shape", "sub", "pre"), _rows())
async def test_an_edit_changes_only_the_comments_own_lines(svc, pos, shape, sub, pre) -> None:
    built, i = await _built(svc, pos, shape, sub, pre)
    target = (await built.comments())[i]
    old_lines = sections.split_lines(built.body(), keepends=True)
    start = old_lines.index(f"- [{target.timestamp}] `manager` Catherine Manager:\n")
    end = start + 1
    while end < len(old_lines) and not old_lines[end].startswith(("- [", "<!--")):
        end += 1
    at(500)

    res = await svc.edit_comment(
        built.item_id,
        target.hash[:8],
        ["new text", "second\nbullet"],
        as_slug="manager",
        sub=built.sub,
    )

    new_lines = sections.split_lines(built.body(), keepends=True)
    header = f"- [{target.timestamp}, edited {res.new.edited_ts}] `manager` Catherine Manager:\n"
    expected = [header, "  - new text\n", "  - second\n", "    bullet\n"]
    assert new_lines == old_lines[:start] + expected + old_lines[end:]
    assert res.changed
    assert res.new.hash != target.hash
    assert (res.new.timestamp, res.new.author_slug) == (target.timestamp, "manager")


async def test_the_printed_hash_is_the_one_a_fresh_load_computes(svc) -> None:
    built = await scene(svc, ["a", "b"])
    target = (await built.comments())[0]
    at(900)

    res = await svc.edit_comment(built.item_id, target.hash[:7], ["changed"], as_slug="manager")

    fresh = await built.comments()
    assert [c.hash for c in fresh if c.edited_ts] == [res.new.hash]
    assert res.new_shown == discussion.short_hashes(fresh)[0]


async def test_a_second_edit_replaces_the_mark(svc) -> None:
    built = await scene(svc, ["a"])
    first = (await built.comments())[0]
    at(900)
    one = await svc.edit_comment(built.item_id, first.hash[:7], ["b"], as_slug="manager")
    at(1000)

    await svc.edit_comment(built.item_id, one.new.hash[:7], ["c"], as_slug="manager")

    (now,) = await built.comments()
    assert built.region().count("edited") == 1
    assert now.edited_ts == "2026-06-07T10:16:40Z"
    assert now.timestamp == first.timestamp


async def test_an_edit_to_the_same_text_writes_nothing(svc) -> None:
    built = await scene(svc, ["same", "other"])
    target = (await built.comments())[0]
    before = built.path.read_bytes()
    at(900)

    res = await svc.edit_comment(built.item_id, target.hash[:7], ["same"], as_slug="manager")

    assert not res.changed
    assert res.new.hash == target.hash
    assert built.path.read_bytes() == before


async def test_the_display_name_in_the_header_survives_a_rename_of_the_author(svc) -> None:
    built = await scene(svc, ["a"])
    text = built.text().replace("Catherine Manager:", "Old Display Name:")
    built.path.write_text(text, encoding="utf-8")
    (target,) = await built.comments()
    at(900)

    await svc.edit_comment(built.item_id, target.hash[:7], ["b"], as_slug="manager")

    assert "`manager` Old Display Name:" in built.text()


# ------------------------------------------------------------------ refusals


def _bytes(built: Scene) -> tuple[bytes, bytes]:
    log = reflog_path(built.svc.paths.squad_dir)
    return built.path.read_bytes(), log.read_bytes() if log.exists() else b""


async def _refused(svc, built: Scene, token: str, messages: list[str], as_slug: str, match: str):
    before = _bytes(built)
    with pytest.raises(SquadsError, match=match):
        await svc.edit_comment(built.item_id, token, messages, as_slug=as_slug, sub=built.sub)
    assert _bytes(built) == before


async def test_a_different_author_is_refused(svc) -> None:
    await svc.add_operator("Pierre Chat")
    built = await scene(svc, ["mine"])
    (c,) = await built.comments()

    await _refused(
        svc,
        built,
        c.hash[:7],
        ["x"],
        "op-pierre",
        "written by manager; --as op-pierre cannot change it",
    )


async def test_a_name_is_not_a_slug(svc) -> None:
    built = await scene(svc, ["mine"])
    (c,) = await built.comments()

    await _refused(svc, built, c.hash[:7], ["x"], "Catherine Manager", "unknown slug")


async def test_a_system_entry_can_not_be_edited_by_anyone(svc) -> None:
    built = await scene(svc, ["mine"])
    entry = discussion.format_comment("2026-06-07T09:00:00Z", "squads", "squads", ["moved"])
    built.set_region(built.region() + entry + "\n")
    system = [c for c in await built.comments() if c.author_slug == "squads"]
    assert system

    await _refused(svc, built, system[0].hash[:7], ["x"], "manager", "written by squads")
    await _refused(svc, built, system[0].hash[:7], ["x"], "squads", "reserved for system entries")


async def test_the_anonymous_sentinel_edits_its_own_comments(svc) -> None:
    built = await scene(svc, ["anon"], authors=["operator"])
    (c,) = await built.comments()
    at(900)

    res = await svc.edit_comment(built.item_id, c.hash[:7], ["still anon"], as_slug="operator")

    assert res.changed


async def test_a_live_marker_in_the_new_text_is_refused(svc) -> None:
    built = await scene(svc, ["mine"])
    (c,) = await built.comments()

    await _refused(svc, built, c.hash[:7], ["see <!-- sq:body -->"], "manager", "marker")


async def test_a_legacy_shaped_line_in_any_discussion_of_the_item_is_refused(svc) -> None:
    built = await scene(svc, ["mine"], sub=True)
    (c,) = await built.comments()
    top = built.text().replace(
        "<!-- sq:discussion -->\n",
        "<!-- sq:discussion -->\n- [2026-01-01T00:00:00Z] Old Name:\n  - old\n",
        1,
    )
    built.path.write_text(top, encoding="utf-8")

    await _refused(
        svc, built, c.hash[:7], ["x"], "manager", r"line \d+ looks like a comment header"
    )


async def test_a_hash_that_no_longer_resolves_is_refused(svc) -> None:
    built = await scene(svc, ["a"])
    (c,) = await built.comments()
    at(900)
    await svc.edit_comment(built.item_id, c.hash[:7], ["b"], as_slug="manager")

    await _refused(svc, built, c.hash[:7], ["c"], "manager", "edited or removed since it was read")


async def test_an_edit_that_would_equal_another_comment_is_refused(svc) -> None:
    built = await scene(svc, ["alpha", "beta"])
    first, second = await built.comments()
    # same author and second as `first`, text of `second`: only `first` can collide
    built.path.write_text(
        built.text().replace(f"- [{second.timestamp}]", f"- [{first.timestamp}]"),
        encoding="utf-8",
    )
    first, second = await built.comments()
    assert first.timestamp == second.timestamp

    await _refused(svc, built, first.hash[:7], ["beta"], "manager", "already has this comment")


@pytest.mark.parametrize("verb", ["edit", "remove"])
async def test_a_retired_author_is_refused_by_the_service_itself(svc, verb) -> None:
    await svc.activate_role("qa")
    built = await scene(svc, ["from qa"], authors=["qa"])
    (c,) = await built.comments()
    role = await svc.roster_item("role", "qa")
    await svc.set_status(role.id, "Archived")
    before = _bytes(built)

    with pytest.raises(SquadsError, match="is retired; reactivate it"):
        if verb == "edit":
            await svc.edit_comment(built.item_id, c.hash[:7], ["x"], as_slug="qa")
        else:
            await svc.remove_comment(built.item_id, c.hash[:7], as_slug="qa")

    assert _bytes(built) == before
