"""`item_title_max:<n>@error` at the write doors. Over the title shapes, a write on an item is
refused exactly when `check()` on the resulting state reports the finding; a create over the
number leaves no file and no index entry; retitling to the number is the way out. Selected at
`warn`, the check is not evaluated on a write.
"""

import unicodedata

import pytest

from _helpers import create_item
from _selection_table import (
    ITEM_TITLE_MAX,
    TITLE_THRESHOLD,
    TypeRow,
    member_findings,
    override_toml,
    service_with,
)
from squads._errors import SquadsError
from squads._services import _validators as validators

pytestmark = pytest.mark.anyio

_TASK_ROW = TypeRow("task", "task")
_ROWS = ITEM_TITLE_MAX.accepting_rows()
_AT_ERROR = (f"item_title_max:{TITLE_THRESHOLD}@error",)
_SHAPES = {
    "under": "x" * (TITLE_THRESHOLD - 1),
    "at": "x" * TITLE_THRESHOLD,
    "over": "x" * (TITLE_THRESHOLD + 1),
    "long": "x" * 200,
    "non-ascii-at": "é" * TITLE_THRESHOLD,
    "decomposed-at": "e\u0301" * TITLE_THRESHOLD,
    "decomposed-over": "e\u0301" * (TITLE_THRESHOLD + 1),
    "non-ascii-over": "é" * (TITLE_THRESHOLD + 1),
}
_MESSAGE = "an item title is a one-line handle"
_NOT_AN_ADVISORY = "advisory"


@pytest.mark.parametrize("shape", _SHAPES)
@pytest.mark.parametrize("row", _ROWS, ids=lambda r: r.id)
async def test_a_write_is_refused_exactly_when_check_reports_the_resulting_state(
    project, row: TypeRow, shape: str
) -> None:
    unselected = service_with(project.squad_dir, override_toml(row, ()))
    item = (await create_item(unselected, row.type, _SHAPES[shape])).item
    svc = service_with(project.squad_dir, override_toml(row, _AT_ERROR))
    reported = bool(member_findings(await svc.check(), ITEM_TITLE_MAX))
    try:
        await svc.update(item.id, add_labels=["touched"])
    except SquadsError as err:
        assert reported
        assert _MESSAGE in str(err)
    else:
        assert not reported


@pytest.mark.parametrize("shape", _SHAPES)
@pytest.mark.parametrize("row", _ROWS, ids=lambda r: r.id)
async def test_a_create_is_refused_exactly_when_the_title_is_over_the_number(
    project, row: TypeRow, shape: str
) -> None:
    svc = service_with(project.squad_dir, override_toml(row, _AT_ERROR))
    before = set(svc.paths.squad_dir.rglob("*.md"))
    over = len(unicodedata.normalize("NFC", _SHAPES[shape])) > TITLE_THRESHOLD
    try:
        created = (await create_item(svc, row.type, _SHAPES[shape])).item
    except SquadsError as err:
        assert over
        assert _MESSAGE in str(err)
        assert set(svc.paths.squad_dir.rglob("*.md")) == before
        assert not [i for i in (await svc.list_items()) if i.type == row.type]
    else:
        assert not over
        assert created.id


@pytest.mark.parametrize("row", _ROWS, ids=lambda r: r.id)
async def test_retitling_to_the_number_is_the_way_out(project, row: TypeRow) -> None:
    unselected = service_with(project.squad_dir, override_toml(row, ()))
    item = (await create_item(unselected, row.type, "x" * 200)).item
    svc = service_with(project.squad_dir, override_toml(row, _AT_ERROR))
    with pytest.raises(SquadsError, match=_MESSAGE):
        await svc.update(item.id, add_labels=["touched"])
    await svc.update(item.id, title="x" * TITLE_THRESHOLD)
    await svc.update(item.id, add_labels=["touched"])
    assert member_findings(await svc.check(), ITEM_TITLE_MAX) == []


async def test_a_status_move_on_an_item_over_the_number_is_refused(project) -> None:
    row = TypeRow("task", "task")
    unselected = service_with(project.squad_dir, override_toml(row, ()))
    item = (await create_item(unselected, "task", "x" * 200)).item
    svc = service_with(project.squad_dir, override_toml(row, _AT_ERROR))
    with pytest.raises(SquadsError, match=_MESSAGE):
        await svc.update(item.id, status="Ready")
    await svc.update(item.id, title="short", status="Ready")


@pytest.mark.parametrize(
    "entry", [f"item_title_max:{TITLE_THRESHOLD}", f"item_title_max:{TITLE_THRESHOLD}@warn"]
)
async def test_a_member_selected_at_warn_is_not_evaluated_on_a_write(
    project, monkeypatch: pytest.MonkeyPatch, entry: str
) -> None:
    row = TypeRow("task", "task")
    svc = service_with(project.squad_dir, override_toml(row, (entry,)))
    calls: list[str] = []
    real = validators.CATALOG["item_title_max"]

    def counted(ctx):
        calls.append(ctx.item.id)
        return real(ctx)

    monkeypatch.setitem(validators.CATALOG, "item_title_max", counted)
    item = (await create_item(svc, "task", "x" * 200)).item
    await svc.update(item.id, add_labels=["touched"])
    assert calls == []
    assert [i for _, i, _ in member_findings(await svc.check(), ITEM_TITLE_MAX)] == [item.id]


async def test_the_refusal_does_not_call_itself_an_advisory(project) -> None:
    svc = service_with(project.squad_dir, override_toml(_TASK_ROW, _AT_ERROR))
    with pytest.raises(SquadsError) as raised:
        await create_item(svc, "task", "x" * 200)
    assert _MESSAGE in str(raised.value)
    assert _NOT_AN_ADVISORY not in str(raised.value)
