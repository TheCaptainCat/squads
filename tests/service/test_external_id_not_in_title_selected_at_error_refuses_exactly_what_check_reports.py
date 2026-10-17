"""`external_id_not_in_title:<regex>@error` at the write doors. Over the pattern shapes, a write
on an item is refused exactly when `check()` on the resulting state reports it; a create whose
title matches is refused; retitling to a title the pattern no longer finds is the way out.
"""

from collections.abc import Awaitable, Callable

import pytest

from _helpers import create_item
from _selection_table import (
    EXTERNAL_ID_NOT_IN_TITLE,
    TRACKER_KEY,
    TypeRow,
    member_findings,
    override_toml,
    service_with,
)
from squads._errors import SquadsError
from squads._models._item import Item

pytestmark = pytest.mark.anyio

_TASK = TypeRow("task", "task")
_AT_ERROR = (f"external_id_not_in_title:{TRACKER_KEY}@error",)
_MESSAGE = "matches the external-id pattern"
_TITLES = {
    "key-at-start": "ABC-1 first",
    "key-in-middle": "fix ABC-1 now",
    "key-at-end": "fixes ABC-1",
    "no-key": "fix the flake",
    "lower-case": "abc-1 is not a key here",
    "two-keys": "ABC-1 and DEF-2",
}
_MATCHES = {"key-at-start", "key-in-middle", "key-at-end", "two-keys"}


@pytest.mark.parametrize("shape", _TITLES)
async def test_a_write_is_refused_exactly_when_check_reports_the_resulting_state(
    project, shape: str
) -> None:
    unselected = service_with(project.squad_dir, override_toml(_TASK, ()))
    item = (await create_item(unselected, "task", _TITLES[shape])).item
    svc = service_with(project.squad_dir, override_toml(_TASK, _AT_ERROR))
    reported = bool(member_findings(await svc.check(), EXTERNAL_ID_NOT_IN_TITLE))
    assert reported is (shape in _MATCHES)
    writes: list[Callable[[], Awaitable[Item]]] = [
        lambda: svc.update(item.id, add_labels=["touched"]),
        lambda: svc.update(item.id, status="Ready"),
    ]
    for write in writes:
        try:
            await write()
        except SquadsError as err:
            assert reported
            assert _MESSAGE in str(err)
        else:
            assert not reported


@pytest.mark.parametrize("shape", _TITLES)
async def test_a_create_is_refused_exactly_when_the_title_matches(project, shape: str) -> None:
    svc = service_with(project.squad_dir, override_toml(_TASK, _AT_ERROR))
    try:
        await create_item(svc, "task", _TITLES[shape])
    except SquadsError as err:
        assert shape in _MATCHES
        assert _MESSAGE in str(err)
        assert [i for i in await svc.list_items() if i.type == "task"] == []
    else:
        assert shape not in _MATCHES


async def test_retitling_to_a_clean_title_is_the_way_out(project) -> None:
    unselected = service_with(project.squad_dir, override_toml(_TASK, ()))
    item = (await create_item(unselected, "task", "fix ABC-1 now")).item
    svc = service_with(project.squad_dir, override_toml(_TASK, _AT_ERROR))
    with pytest.raises(SquadsError, match=_MESSAGE):
        await svc.update(item.id, add_labels=["touched"])
    with pytest.raises(SquadsError, match=_MESSAGE):
        await svc.update(item.id, title="still ABC-2 here")
    await svc.update(item.id, title="fix it now")
    await svc.update(item.id, add_labels=["touched"])
    assert member_findings(await svc.check(), EXTERNAL_ID_NOT_IN_TITLE) == []
