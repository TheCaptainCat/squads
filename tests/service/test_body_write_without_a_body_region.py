"""A body write on a file without a complete ``sq:body`` region fails with a SquadsError and
leaves the file untouched; ``sq check`` reports a work item whose region is gone entirely.
"""

import pytest

from squads._errors import SquadsError
from squads._index._resolver import item_file
from squads._models import _markers as markers

pytestmark = pytest.mark.anyio

OPEN = markers.open_marker(markers.BODY)
CLOSE = markers.close_marker(markers.BODY)


def break_region(text: str, state: str) -> str:
    if state == "both":
        return text.replace(f"{OPEN}\n", "").replace(f"{CLOSE}\n", "")
    if state == "open-only":
        return text.replace(f"{CLOSE}\n", "")
    if state == "close-only":
        return text.replace(f"{OPEN}\n", "")
    return text


@pytest.mark.parametrize("append", [False, True])
@pytest.mark.parametrize("state", ["both", "open-only", "close-only"])
async def test_a_write_without_a_complete_region_fails_cleanly(svc, state: str, append: bool):
    item = (await svc.create("task", "t", author="manager")).item
    path = item_file(svc.paths, item)
    path.write_text(break_region(path.read_text(encoding="utf-8"), state), encoding="utf-8")
    before = path.read_bytes()
    index_before = (svc.paths.squad_dir / ".squads.json").read_bytes()

    with pytest.raises(SquadsError) as raised:
        await svc.set_body(item.id, "new prose", append=append)

    message = str(raised.value)
    assert item.id in message
    assert path.name in message
    assert "sq:body" in message
    assert "restore" in message
    assert path.read_bytes() == before
    assert (svc.paths.squad_dir / ".squads.json").read_bytes() == index_before


@pytest.mark.parametrize("append", [False, True])
async def test_a_write_with_an_intact_region_still_works(svc, append: bool):
    item = (await svc.create("task", "t", author="manager")).item

    await svc.set_body(item.id, "new prose", append=append)

    assert "new prose" in item_file(svc.paths, item).read_text(encoding="utf-8")


@pytest.mark.parametrize("item_type", ["task", "bug"])
async def test_check_reports_a_work_item_with_no_body_region(svc, item_type: str):
    item = (await svc.create(item_type, "t", author="manager")).item
    path = item_file(svc.paths, item)
    path.write_text(break_region(path.read_text(encoding="utf-8"), "both"), encoding="utf-8")

    found = [i for i in await svc.check() if i.item == path.name]

    assert [(i.level, "missing sq:body region" in i.message) for i in found] == [("error", True)]


async def test_check_reports_only_the_unclosed_marker_when_one_marker_is_left(svc):
    item = (await svc.create("task", "t", author="manager")).item
    path = item_file(svc.paths, item)
    path.write_text(break_region(path.read_text(encoding="utf-8"), "open-only"), encoding="utf-8")

    found = [i for i in await svc.check() if i.item == path.name]

    assert [i.message for i in found] == ["unclosed marker <!-- sq:body -->"]


async def test_check_is_silent_on_an_intact_task(svc):
    item = (await svc.create("task", "t", author="manager")).item

    assert not [i for i in await svc.check() if i.item == item_file(svc.paths, item).name]
