"""`body_written` reads the item's file, which the create/update gate does not hold, so it is
report-only: at `@error` every door (create, update, status, import) still accepts the write
and `check()` reports the finding at `error`. It reports beside `subentity_body_written` on one
item, one finding per check.
"""

import json

import pytest

from _helpers import create_item
from _selection_table import (
    BODY_WRITTEN_MEMBER,
    SUBENTITY_BODY_FRAGMENT,
    TypeRow,
    member_findings,
    override_toml,
    service_with,
)

pytestmark = pytest.mark.anyio

_TASK = TypeRow("task", "task", kind="subtask")


@pytest.mark.parametrize("entry", ["body_written", "body_written@warn", "body_written@error"])
async def test_no_door_refuses_an_item_whose_body_is_unwritten(project, entry: str) -> None:
    level = "error" if entry.endswith("@error") else "warn"
    svc = service_with(project.squad_dir, override_toml(_TASK, (entry,)))
    item = (await create_item(svc, "task", "no body")).item
    await svc.update(item.id, add_labels=["touched"])
    await svc.update(item.id, status="Ready")
    imported = await svc.import_events(
        json.dumps({"op": "create", "type": "task", "title": "imp", "as": "manager", "handle": "h"})
    )
    assert imported.applied is not None, imported.plan.issues
    found = member_findings(imported.applied.findings, BODY_WRITTEN_MEMBER)
    assert [(lvl, i) for lvl, i, _ in found] == [(level, imported.plan.handle_to_id["h"])]

    reported = member_findings(await svc.check(), BODY_WRITTEN_MEMBER)
    assert {i for _, i, _ in reported} == {item.id, imported.plan.handle_to_id["h"]}
    assert {lvl for lvl, _, _ in reported} == {level}


async def test_an_unwritten_body_and_an_unwritten_subtask_earn_one_finding_each(project) -> None:
    svc = service_with(project.squad_dir, override_toml(_TASK, ("body_written",)))
    task = (await create_item(svc, "task", "t")).item
    await svc.add_block(task.id, "subtask", "a subtask")
    issues = [i for i in await svc.check() if i.item == task.id]
    assert len(member_findings(issues, BODY_WRITTEN_MEMBER)) == 1
    assert len([i for i in issues if SUBENTITY_BODY_FRAGMENT in i.message]) == 1


async def test_writing_the_body_clears_the_finding(project) -> None:
    svc = service_with(project.squad_dir, override_toml(_TASK, ("body_written@error",)))
    item = (await create_item(svc, "task", "t")).item
    assert member_findings(await svc.check(), BODY_WRITTEN_MEMBER)
    await svc.set_body(item.id, "Now written.")
    assert member_findings(await svc.check(), BODY_WRITTEN_MEMBER) == []
