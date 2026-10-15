"""`sq import` of an item whose title is over the selected number: at `warn` the item is
created and the finding is reported in the result; at `@error` the pre-pass refuses the event
and nothing is written.
"""

import json

import pytest

from _selection_table import ITEM_TITLE_MAX, TypeRow, member_findings, override_toml, service_with

pytestmark = pytest.mark.anyio

_TASK = TypeRow("task", "task")


def _event(title: str, handle: str) -> str:
    return json.dumps(
        {"op": "create", "type": "task", "title": title, "as": "manager", "handle": handle}
    )


async def test_an_import_over_the_number_is_reported_at_warn(project) -> None:
    svc = service_with(project.squad_dir, override_toml(_TASK, ("item_title_max:80",)))
    text = _event("x" * 81, "long") + "\n" + _event("x" * 80, "exact")
    result = await svc.import_events(text)
    assert result.applied is not None, result.plan.issues
    found = member_findings(result.applied.findings, ITEM_TITLE_MAX)
    assert [(level, item) for level, item, _ in found] == [
        ("warn", result.plan.handle_to_id["long"])
    ]


async def test_an_import_over_the_number_is_refused_by_the_pre_pass_at_error(project) -> None:
    svc = service_with(project.squad_dir, override_toml(_TASK, ("item_title_max:80@error",)))
    result = await svc.import_events(_event("x" * 81, "long"))
    assert result.applied is None
    assert any(ITEM_TITLE_MAX.fragment in i.message for i in result.plan.issues), result.plan.issues
    assert [i for i in await svc.list_items() if i.type == "task"] == []
    clean = await svc.import_events(_event("x" * 80, "exact"))
    assert clean.applied is not None, clean.plan.issues
