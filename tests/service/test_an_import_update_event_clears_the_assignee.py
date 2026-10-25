"""An import `update` event removes an assignee with `clear_assignee`; it refuses an empty
`assignee` and `assignee` together with `clear_assignee`, and clearing an absent assignee writes
nothing."""

import json
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from _helpers import create_item
from squads._context import bind_context, get_context

pytestmark = pytest.mark.anyio


def _import(svc, item_id, **event):
    line = {"op": "update", "target": item_id, "as": "manager", **event}
    return svc.import_events(json.dumps(line))


async def test_an_update_event_clears_the_assignee(svc) -> None:
    item = (await create_item(svc, "task", "t", assignee="manager")).item

    result = await _import(svc, item.id, clear_assignee=True)

    assert result.applied is not None
    assert (await svc.get(item.id)).assignee is None


@pytest.mark.parametrize(
    "event",
    [{"assignee": ""}, {"assignee": "manager", "clear_assignee": True}],
    ids=["empty", "both"],
)
async def test_a_contradictory_or_empty_assignee_is_an_issue_and_writes_nothing(svc, event) -> None:
    item = (await create_item(svc, "task", "t", assignee="manager")).item

    result = await _import(svc, item.id, **event)

    assert not result.plan.ok
    assert result.applied is None
    assert (await svc.get(item.id)).assignee == "manager"


async def test_clearing_an_absent_assignee_writes_nothing(svc) -> None:
    item = (await create_item(svc, "task", "t")).item
    before = (await svc.get(item.id)).updated_at
    bind_context(replace(get_context(), clock_override=datetime(2030, 1, 1, tzinfo=UTC)))

    result = await _import(svc, item.id, clear_assignee=True)

    assert result.plan.ok
    assert (await svc.get(item.id)).updated_at == before
