"""A sub-entity container restored on a write encloses every block of its kind that survived,
in id order, under one heading; prose between the blocks refuses the write instead."""

import re
from typing import Any

import pytest

from _helpers import create_item, squad_tree
from squads._errors import SquadsError
from squads._models import _markers as markers

pytestmark = pytest.mark.anyio

# host type, kind, container tag, container heading
_KINDS = [
    pytest.param("task", "subtask", "subtasks", "Subtasks", id="subtask"),
    pytest.param("feature", "story", "stories", "User Stories", id="story"),
    pytest.param("review", "finding", "findings", "Findings", id="finding"),
]


async def _host(svc: Any, host: str, kind: str, count: int = 2) -> tuple[str, Any]:
    item = (await create_item(svc, host, "Host")).item
    for n in range(count):
        await svc.add_block(item.id, kind, f"block {n + 1}")
    return item.id, svc.paths.abspath((await svc.get(item.id)).path)


def _without_container(text: str, tag: str, heading: str, *, drop_heading: bool = False) -> str:
    gone = {markers.open_marker(tag), markers.close_marker(tag)}
    if drop_heading:
        gone.add(f"## {heading}")
    return "".join(ln for ln in text.splitlines(keepends=True) if ln.strip() not in gone)


def _assert_enclosed(text: str, kind: str, tag: str, heading: str, ids: list[str]) -> None:
    assert len(re.findall(rf"^## {heading}$", text, re.MULTILINE)) == 1
    assert text.count(markers.open_marker(tag)) == text.count(markers.close_marker(tag)) == 1
    start, end = text.index(markers.open_marker(tag)), text.index(markers.close_marker(tag))
    opens = [m.start() for m in re.finditer(rf"<!-- sq:{kind}:[^:]+? -->", text)]
    assert len(opens) == len(ids)
    assert all(start < at < end for at in opens)
    assert [text.index(markers.open_marker(f"{kind}:{i}")) for i in ids] == sorted(opens)


@pytest.mark.parametrize("first_write", ["body", "add"])
@pytest.mark.parametrize("keep_heading", [True, False], ids=["heading-kept", "heading-gone"])
@pytest.mark.parametrize(("host", "kind", "tag", "heading"), _KINDS)
async def test_a_restored_container_wraps_the_surviving_blocks(
    svc, host: str, kind: str, tag: str, heading: str, keep_heading: bool, first_write: str
) -> None:
    item_id, path = await _host(svc, host, kind)
    text = _without_container(path.read_text(), tag, heading, drop_heading=not keep_heading)
    path.write_text(text, newline="")
    first, second = [s.local_id for s in (await svc.get(item_id)).subentities]

    if first_write == "body":
        await svc.set_block_body(item_id, kind, first, "prose", force=True, append=False)
    await svc.add_block(item_id, kind, "block 3")

    ids = [s.local_id for s in (await svc.get(item_id)).subentities]
    assert ids[:2] == [first, second] and len(ids) == 3
    _assert_enclosed(path.read_text(), kind, tag, heading, ids)
    assert [
        i for i in await svc.check() if i.level in ("error", "warn") and "outside" in i.message
    ] == []


@pytest.mark.parametrize(("host", "kind", "tag", "heading"), _KINDS)
@pytest.mark.parametrize("crlf", [False, True], ids=["lf", "crlf"])
async def test_a_container_removed_with_its_only_block_comes_back_around_the_new_block(
    svc, host: str, kind: str, tag: str, heading: str, crlf: bool
) -> None:
    item_id, path = await _host(svc, host, kind, count=1)
    (only,) = [s.local_id for s in (await svc.get(item_id)).subentities]
    text = path.read_text()
    start = text.index(markers.open_marker(tag))
    end = text.index(markers.close_marker(tag)) + len(markers.close_marker(tag))
    text = text[:start] + text[end:]
    path.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode())

    await svc.set_block_body(item_id, kind, only, "prose", force=True, append=False)

    after = path.read_bytes().decode()
    assert ("\n" not in after.replace("\r\n", "")) if crlf else ("\r" not in after)
    _assert_enclosed(after.replace("\r\n", "\n"), kind, tag, heading, [only])


async def test_blocks_out_of_id_order_are_enclosed_in_id_order(svc) -> None:
    item_id, path = await _host(svc, "task", "subtask")
    text = path.read_text()
    a = text.index(markers.open_marker("subtask:ST1"))
    b = text.index(markers.open_marker("subtask:ST2"))
    end = text.index(markers.close_marker("subtasks"))
    swapped = text[:a] + text[b:end] + "\n" + text[a:b].rstrip("\n") + "\n" + text[end:]
    path.write_text(_without_container(swapped, "subtasks", "Subtasks"), newline="")

    await svc.set_block_body(item_id, "subtask", "ST1", "prose", force=True, append=False)

    _assert_enclosed(path.read_text(), "subtask", "subtasks", "Subtasks", ["ST1", "ST2"])


async def test_prose_between_the_surviving_blocks_refuses_the_write(svc, project) -> None:
    item_id, path = await _host(svc, "task", "subtask")
    text = _without_container(path.read_text(), "subtasks", "Subtasks")
    text = text.replace(
        markers.open_marker("subtask:ST2"),
        "Hand-written paragraph.\n\n" + markers.open_marker("subtask:ST2"),
    )
    path.write_text(text, newline="")
    before = squad_tree(project.root)

    with pytest.raises(SquadsError) as raised:
        await svc.set_block_body(item_id, "subtask", "ST1", "prose", force=True, append=False)

    assert "\n" not in str(raised.value).strip()
    assert item_id in str(raised.value) and "subtasks" in str(raised.value)
    assert squad_tree(project.root) == before


async def test_check_reports_a_block_outside_its_container(svc) -> None:
    _, path = await _host(svc, "task", "subtask")
    path.write_text(_without_container(path.read_text(), "subtasks", "Subtasks"), newline="")

    issues = [i for i in await svc.check() if i.item == path.name]

    assert {i.rule for i in issues if "outside" in i.message} == {"block_in_container"}
    assert len([i for i in issues if i.rule == "block_in_container"]) == 2


async def test_check_is_quiet_when_every_block_is_inside(svc) -> None:
    await _host(svc, "task", "subtask")

    assert [i for i in await svc.check() if i.rule == "block_in_container"] == []


@pytest.mark.parametrize(("host", "kind", "tag", "heading"), _KINDS)
async def test_prose_between_surviving_blocks_refuses_an_add_too(
    svc, project, host: str, kind: str, tag: str, heading: str
) -> None:
    item_id, path = await _host(svc, host, kind)
    _, second = [s.local_id for s in (await svc.get(item_id)).subentities]
    text = _without_container(path.read_text(), tag, heading)
    marker = markers.open_marker(f"{kind}:{second}")
    path.write_text(text.replace(marker, "Hand-written paragraph.\n\n" + marker), newline="")
    before = squad_tree(project.root)

    with pytest.raises(SquadsError) as raised:
        await svc.add_block(item_id, kind, "block 3")

    assert "\n" not in str(raised.value).strip() and item_id in str(raised.value)
    assert squad_tree(project.root) == before


@pytest.mark.parametrize("gone", ["open", "close"])
@pytest.mark.parametrize(("host", "kind", "tag", "heading"), _KINDS)
async def test_a_half_present_container_is_a_clean_error_for_an_add_and_untouched_by_a_write(
    svc, project, host: str, kind: str, tag: str, heading: str, gone: str
) -> None:
    item_id, path = await _host(svc, host, kind)
    first = (await svc.get(item_id)).subentities[0].local_id
    marker = markers.open_marker(tag) if gone == "open" else markers.close_marker(tag)
    path.write_text(path.read_text().replace(marker + "\n", "", 1), newline="")

    await svc.set_block_body(item_id, kind, first, "prose", force=True, append=False)

    text = path.read_text()
    assert text.count(markers.open_marker(tag)) + text.count(markers.close_marker(tag)) == 1
    before = squad_tree(project.root)
    with pytest.raises(SquadsError) as raised:
        await svc.add_block(item_id, kind, "block 3")
    assert "half present" in str(raised.value) and "\n" not in str(raised.value).strip()
    assert squad_tree(project.root) == before
    issues = [i for i in await svc.check() if i.item == path.name]
    assert [i for i in issues if i.rule == "block_in_container"] == []


async def test_blocks_inside_the_discussion_region_refuse_the_restore(svc, project) -> None:
    item_id, path = await _host(svc, "task", "subtask")
    text = _without_container(path.read_text(), "subtasks", "Subtasks")
    start, end = text.index(markers.open_marker("subtask:ST1")), text.index("\n## Discussion\n") + 1
    blocks = text[start:end]
    text = text[:start] + text[end:]
    text = text.replace(
        markers.close_marker(markers.DISCUSSION), blocks + markers.close_marker(markers.DISCUSSION)
    )
    path.write_text(text, newline="")
    before = squad_tree(project.root)

    with pytest.raises(SquadsError) as raised:
        await svc.set_block_body(item_id, "subtask", "ST1", "prose", force=True, append=False)

    assert "discussion region" in str(raised.value)
    assert squad_tree(project.root) == before


@pytest.mark.parametrize(("host", "kind", "tag", "heading"), _KINDS)
async def test_an_author_heading_between_the_heading_and_the_blocks_keeps_one_container_heading(
    svc, host: str, kind: str, tag: str, heading: str
) -> None:
    item_id, path = await _host(svc, host, kind)
    first = (await svc.get(item_id)).subentities[0].local_id
    text = _without_container(path.read_text(), tag, heading)
    marker = markers.open_marker(f"{kind}:{first}")
    path.write_text(text.replace(marker, "## Notes\n\nAuthor notes.\n\n" + marker, 1), newline="")

    await svc.set_block_body(item_id, kind, first, "prose", force=True, append=False)

    ids = [s.local_id for s in (await svc.get(item_id)).subentities]
    _assert_enclosed(path.read_text(), kind, tag, heading, ids)
