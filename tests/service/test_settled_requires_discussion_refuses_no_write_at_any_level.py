"""`settled_requires_discussion` reads the item's file, which the create/update gate does not hold,
so it is report-only: at every level the transition to a settled status is accepted on every
door, `check()` reports the item at the declared level, and one comment clears it.
"""

import json

import pytest

from _helpers import create_item
from _selection_table import (
    SETTLED_REQUIRES_DISCUSSION,
    TypeRow,
    member_findings,
    override_toml,
    service_with,
)

pytestmark = pytest.mark.anyio

_TASK = TypeRow("task", "task")


@pytest.mark.parametrize("entry", ["", "@warn", "@error"])
async def test_no_door_refuses_the_move_to_a_settled_status(project, entry: str) -> None:
    level = "error" if entry == "@error" else "warn"
    svc = service_with(
        project.squad_dir, override_toml(_TASK, (f"settled_requires_discussion{entry}",))
    )
    via_status = (await create_item(svc, "task", "via status")).item
    for status in ("Ready", "InProgress", "Done"):
        await svc.update(via_status.id, status=status)
    created_settled = (await create_item(svc, "task", "created settled", status="Done")).item
    imported = await svc.import_events(
        json.dumps(
            {
                "op": "create",
                "type": "task",
                "title": "imp",
                "as": "manager",
                "handle": "h",
                "status": "Done",
            }
        )
    )
    assert imported.applied is not None, imported.plan.issues
    found = member_findings(imported.applied.findings, SETTLED_REQUIRES_DISCUSSION)
    assert [(lvl, i) for lvl, i, _ in found] == [(level, imported.plan.handle_to_id["h"])]

    reported = member_findings(await svc.check(), SETTLED_REQUIRES_DISCUSSION)
    assert {i for _, i, _ in reported} == {
        via_status.id,
        created_settled.id,
        imported.plan.handle_to_id["h"],
    }
    assert {lvl for lvl, _, _ in reported} == {level}
    await svc.comment(via_status.id, ["Done."], as_slug="manager")
    remaining = member_findings(await svc.check(), SETTLED_REQUIRES_DISCUSSION)
    assert via_status.id not in {i for _, i, _ in remaining}
