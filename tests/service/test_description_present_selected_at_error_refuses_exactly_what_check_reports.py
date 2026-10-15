"""`description_present@error` at the write doors. Over the summary shapes, a write on an item is
refused exactly when `check()` on the resulting state reports it; a create without a summary is
refused and one with it accepted; a write that also sets a summary is the way out; clearing a
summary is refused.
"""

import pytest

from _helpers import create_item
from _selection_table import (
    DESCRIPTION_PRESENT,
    TypeRow,
    member_findings,
    override_toml,
    service_with,
)
from squads._errors import SquadsError

pytestmark = pytest.mark.anyio

_ROWS = DESCRIPTION_PRESENT.accepting_rows()
_AT_ERROR = ("description_present@error",)
_MESSAGE = "description is empty"
_SHAPES = {"never-set": "", "spaces": "   ", "nbsp": chr(0xA0), "visible": "x"}


@pytest.mark.parametrize("shape", _SHAPES)
@pytest.mark.parametrize("row", _ROWS, ids=lambda r: r.id)
async def test_a_write_is_refused_exactly_when_check_reports_the_resulting_state(
    project, row: TypeRow, shape: str
) -> None:
    unselected = service_with(project.squad_dir, override_toml(row, ()))
    item = (await create_item(unselected, row.type, "t", description=_SHAPES[shape])).item
    svc = service_with(project.squad_dir, override_toml(row, _AT_ERROR))
    reported = bool(member_findings(await svc.check(), DESCRIPTION_PRESENT))
    try:
        await svc.update(item.id, add_labels=["touched"])
    except SquadsError as err:
        assert reported
        assert _MESSAGE in str(err)
    else:
        assert not reported


@pytest.mark.parametrize("shape", _SHAPES)
@pytest.mark.parametrize("row", _ROWS, ids=lambda r: r.id)
async def test_a_create_is_refused_exactly_when_the_summary_has_no_visible_character(
    project, row: TypeRow, shape: str
) -> None:
    svc = service_with(project.squad_dir, override_toml(row, _AT_ERROR))
    empty = not _SHAPES[shape].strip()
    try:
        await create_item(svc, row.type, "t", description=_SHAPES[shape])
    except SquadsError as err:
        assert empty
        assert _MESSAGE in str(err)
        assert [i for i in await svc.list_items() if i.type == row.type] == []
    else:
        assert not empty


@pytest.mark.parametrize("row", _ROWS, ids=lambda r: r.id)
async def test_the_way_out_is_a_write_that_also_sets_a_summary(project, row: TypeRow) -> None:
    unselected = service_with(project.squad_dir, override_toml(row, ()))
    item = (await create_item(unselected, row.type, "t")).item
    svc = service_with(project.squad_dir, override_toml(row, _AT_ERROR))
    with pytest.raises(SquadsError, match=_MESSAGE):
        await svc.update(item.id, add_labels=["touched"])
    await svc.update(item.id, description="Summarised.", add_labels=["touched"])
    with pytest.raises(SquadsError, match=_MESSAGE):
        await svc.update(item.id, description="")
    with pytest.raises(SquadsError, match=_MESSAGE):
        await svc.update(item.id, description="  ")
    assert member_findings(await svc.check(), DESCRIPTION_PRESENT) == []


async def test_a_status_move_needs_the_summary_in_the_same_command(project) -> None:
    row = TypeRow("task", "task")
    unselected = service_with(project.squad_dir, override_toml(row, ()))
    item = (await create_item(unselected, "task", "t")).item
    svc = service_with(project.squad_dir, override_toml(row, _AT_ERROR))
    with pytest.raises(SquadsError, match=_MESSAGE):
        await svc.update(item.id, status="Ready")
    moved = await svc.update(item.id, status="Ready", description="Summarised.")
    assert moved.status == "Ready"
