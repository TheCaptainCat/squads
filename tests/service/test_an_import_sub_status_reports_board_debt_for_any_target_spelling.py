"""An imported `sub-status` event reports the board-debt findings of the item it touched however
its target is spelled: bare number, lower-case id, padded or unpadded full id.
"""

import json

import pytest

from _helpers import create_item
from _selection_table import (
    DESCRIPTION_PRESENT,
    TypeRow,
    member_findings,
    override_toml,
    service_with,
)

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("spelling", ["{n}", "task-{n}", "TASK-{n}", "TASK-{n:06d}"])
async def test_the_target_spelling_does_not_change_what_is_reported(project, spelling: str) -> None:
    row = TypeRow("task", "task", kind="subtask")
    svc = service_with(project.squad_dir, override_toml(row, ("description_present",)))
    task = (await create_item(svc, "task", "no summary")).item
    await svc.add_block(task.id, "subtask", "a subtask")
    event = {
        "op": "sub-status",
        "target": spelling.format(n=task.sequence_id),
        "kind": "subtask",
        "local": "ST1",
        "status": "InProgress",
        "as": "manager",
    }
    result = await svc.import_events(json.dumps(event))
    assert result.applied is not None, result.plan.issues
    assert [i for _, i, _ in member_findings(result.applied.findings, DESCRIPTION_PRESENT)] == [
        task.id
    ]
