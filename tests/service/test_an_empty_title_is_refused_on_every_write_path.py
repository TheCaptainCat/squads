"""A blank title (empty, whitespace, or only format characters) is refused before any write by
item creation, item update and the import events that reach them. A sub-entity title may be
absent: a blank one, on add or update, is stored as none. A title that slugs to nothing is valid
and is stored."""

import json

import pytest

from _helpers import create_item
from squads._errors import SquadsError
from squads._services._base import is_blank

pytestmark = pytest.mark.anyio


def _event(**event) -> str:
    return json.dumps({"as": "manager", **event})


async def _create(svc, title):
    return await create_item(svc, "task", title)


async def _update(svc, title):
    item = (await create_item(svc, "task", "t")).item
    await svc.update(item.id, title=title)


async def _add_subtask(svc, title):
    item = (await create_item(svc, "task", "t")).item
    await svc.add_block(item.id, "subtask", title)
    return item


async def _update_subtask(svc, title):
    item = (await create_item(svc, "task", "t")).item
    await svc.add_block(item.id, "subtask", "s")
    await svc.update_block(item.id, "subtask", "ST1", title=title)
    return item


async def _import_create(svc, title):
    result = await svc.import_events(_event(op="create", type="task", title=title))
    _refuse_unless_applied(result)


async def _import_update(svc, title):
    item = (await create_item(svc, "task", "t")).item
    result = await svc.import_events(_event(op="update", target=item.id, title=title))
    _refuse_unless_applied(result)


def _refuse_unless_applied(result) -> None:
    if result.applied is None:
        raise SquadsError("; ".join(i.message for i in result.plan.issues))


_PATHS = [_create, _update, _import_create, _import_update]
_BLANKS = ["", "   ", "\u200b", "\ufeff", " \u200b\n"]
_BLANK_IDS = ["empty", "whitespace", "zero-width-space", "bom", "mixed"]


@pytest.mark.parametrize("path", _PATHS, ids=lambda p: p.__name__.strip("_"))
@pytest.mark.parametrize("title", _BLANKS, ids=_BLANK_IDS)
async def test_a_blank_title_is_refused(svc, path, title) -> None:
    with pytest.raises(SquadsError, match="title"):
        await path(svc, title)

    assert not any(is_blank(i.title) for i in await svc.list_items())


@pytest.mark.parametrize("path", [_create, _update], ids=lambda p: p.__name__.strip("_"))
async def test_a_title_that_slugs_to_nothing_is_stored(svc, path) -> None:
    await path(svc, "!!!")

    assert any(i.title == "!!!" for i in await svc.list_items())


@pytest.mark.parametrize("title", _BLANKS, ids=_BLANK_IDS)
@pytest.mark.parametrize("path", [_add_subtask, _update_subtask], ids=["add", "update"])
async def test_a_blank_subentity_title_is_stored_as_none(svc, path, title) -> None:
    task = await path(svc, title)

    (sub,) = (await svc.get(task.id)).subentities
    assert sub.title == ""
