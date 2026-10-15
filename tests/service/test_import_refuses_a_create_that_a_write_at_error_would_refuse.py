"""The bulk importer's pre-pass is the fourth write door: for each check that can refuse a write,
selected at `@error`, an imported create in the reported state is refused with nothing written,
and the same event in a clean state is applied.
"""

import json

import pytest

from _selection_table import (
    ASSIGNEE_PRESENT,
    DESCRIPTION_PRESENT,
    EXTERNAL_ID_NOT_IN_TITLE,
    Member,
    TypeRow,
    override_toml,
    service_with,
)

pytestmark = pytest.mark.anyio

_TASK = TypeRow("task", "task")

#: Member -> (the event fields that put the created item in the reported state, the fields
#: that keep it out of it). Every event also carries a title, a type and an actor.
_CASES: dict[str, tuple[Member, dict[str, object], dict[str, object]]] = {
    "description": (
        DESCRIPTION_PRESENT,
        {"title": "no summary"},
        {"title": "summarised", "description": "A summary."},
    ),
    "assignee": (
        ASSIGNEE_PRESENT,
        {"title": "active and unassigned", "status": "InProgress"},
        {"title": "active and assigned", "status": "InProgress", "assignee": "manager"},
    ),
    "external-id": (
        EXTERNAL_ID_NOT_IN_TITLE,
        {"title": "Fix ABC-123 flake"},
        {"title": "Fix the flake"},
    ),
}


def _event(fields: dict[str, object]) -> str:
    return json.dumps({"op": "create", "type": "task", "as": "manager", "handle": "h", **fields})


@pytest.mark.parametrize("case", _CASES)
async def test_the_pre_pass_refuses_the_reported_state_and_applies_the_clean_one(
    project, case: str
) -> None:
    member, offending, clean = _CASES[case]
    entry = member.plain[0] + "@error"
    svc = service_with(project.squad_dir, override_toml(_TASK, (entry,)))

    refused = await svc.import_events(_event(offending))
    assert refused.applied is None
    assert any(member.fragment in i.message for i in refused.plan.issues), refused.plan.issues
    assert [i for i in await svc.list_items() if i.type == "task"] == []

    applied = await svc.import_events(_event(clean))
    assert applied.applied is not None, applied.plan.issues
