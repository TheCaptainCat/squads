"""The bulk importer's ``sub-status`` event carries its own ``force`` flag, and that flag means
what it means everywhere else: it waives the lifecycle edge, not the kind's declared vocabulary.

This is the second door onto the sub-entity status core, and the only import route in — an
``add-sub`` event carrying a status the kind does not declare is refused by the same seed-side
check the interactive door uses. The importer validates the whole file against a shadow index
before it writes anything, so a refusal here has to surface as a pre-pass issue with the corpus
untouched, not as an applied write the integrity gate later complains about.
"""

import json

import pytest

from _helpers import create_item

pytestmark = pytest.mark.anyio


def _lines(*events: dict[str, object]) -> str:
    return "\n".join(json.dumps(e) for e in events)


async def _task_with_one_subtask(svc):
    task = (await create_item(svc, "task", "Imported into")).item
    block = await svc.add_subtask(task.id, "Only subtask")
    return task, block.local_id


async def test_a_forced_sub_status_event_cannot_write_a_status_the_kind_does_not_declare(svc):
    task, local_id = await _task_with_one_subtask(svc)

    result = await svc.import_events(
        _lines(
            {
                "op": "sub-status",
                "as": "manager",
                "target": task.id,
                "kind": "subtask",
                "local": local_id,
                "status": "Verified",
                "force": True,
            }
        )
    )

    assert not result.plan.ok
    assert result.applied is None
    assert any("not a valid subtask status" in i.message for i in result.plan.issues)
    (subtask,) = await svc.list_subtasks(task.id)
    assert subtask.status == "Todo"
    assert [i for i in await svc.check() if i.level == "error"] == []


async def test_a_forced_sub_status_event_still_applies_an_edge_the_machine_forbids(svc):
    task, local_id = await _task_with_one_subtask(svc)
    assert not svc.spec.subentity_can_transition("subtask", "Todo", "Done")

    result = await svc.import_events(
        _lines(
            {
                "op": "sub-status",
                "as": "manager",
                "target": task.id,
                "kind": "subtask",
                "local": local_id,
                "status": "Done",
                "force": True,
            }
        )
    )

    assert result.plan.ok, result.plan.issues
    (subtask,) = await svc.list_subtasks(task.id)
    assert subtask.status == "Done"


async def test_one_bad_forced_sub_status_event_holds_back_the_whole_file(svc):
    """The pre-pass is all-or-nothing, so the refusal must not land the file's other events
    either — otherwise a rejected status still leaves a half-imported corpus behind."""
    task, local_id = await _task_with_one_subtask(svc)

    result = await svc.import_events(
        _lines(
            {"op": "create", "as": "manager", "type": "task", "title": "Would-be sibling"},
            {
                "op": "sub-status",
                "as": "manager",
                "target": task.id,
                "kind": "subtask",
                "local": local_id,
                "status": "Verified",
                "force": True,
            },
        )
    )

    assert not result.plan.ok
    titles = [i.title for i in await svc.list_items()]
    assert "Would-be sibling" not in titles
