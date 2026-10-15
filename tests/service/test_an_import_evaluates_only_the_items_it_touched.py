"""`sq import` reports the catalog on the items it wrote and no others: a member counted on an
untouched item of a selecting type is not called, however the import ends.
"""

import json

import pytest

from _helpers import create_item
from _selection_table import TypeRow, override_toml, service_with
from squads._services import _validators as validators

pytestmark = pytest.mark.anyio


async def test_an_import_does_not_evaluate_a_check_on_an_untouched_item(
    project, monkeypatch: pytest.MonkeyPatch
) -> None:
    row = TypeRow("task", "task")
    svc = service_with(
        project.squad_dir, override_toml(row, ("external_id_not_in_title:[A-Z]+-[0-9]+",))
    )
    untouched = (await create_item(svc, "task", "untouched ABC-1")).item
    calls: list[str] = []
    real = validators.CATALOG["external_id_not_in_title"]

    def counted(ctx):
        calls.append(ctx.item.id)
        return real(ctx)

    monkeypatch.setitem(validators.CATALOG, "external_id_not_in_title", counted)
    event = {
        "op": "create",
        "type": "task",
        "title": "imported DEF-2",
        "as": "manager",
        "handle": "h",
    }
    result = await svc.import_events(json.dumps(event))
    assert result.applied is not None, result.plan.issues
    imported = result.plan.handle_to_id["h"]
    assert untouched.id not in calls
    assert set(calls) == {imported}
    assert [f.item for f in result.applied.findings if "external-id" in f.message] == [imported]
