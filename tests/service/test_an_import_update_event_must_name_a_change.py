"""An import `update` event that names only its target is an issue, and nothing is written."""

import json

import pytest

from _helpers import create_item

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize(
    ("change", "ok"),
    [({}, False), ({"description": "d"}, True), ({"add_labels": ["x"]}, True)],
    ids=["no-field", "description", "label"],
)
async def test_an_update_event_needs_a_field(svc, change, ok) -> None:
    item = (await create_item(svc, "task", "t")).item
    event = {"op": "update", "target": item.id, "as": "manager", **change}

    result = await svc.import_events(json.dumps(event))

    assert result.plan.ok is ok
    assert (result.applied is not None) is ok
    if not ok:
        assert any("nothing to update" in i.message for i in result.plan.issues)
