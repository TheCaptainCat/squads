"""`item_title_max:<n>` over the title shapes: on every type that accepts it, a title of at most
the number is silent and a longer one is reported, counting characters rather than bytes; a
retitle that crosses the number moves the finding in step; and an epic's list replaced without
the splat form drops its bundled `no_parent` while the splat form keeps it.
"""

import pytest

from _helpers import create_item
from _selection_table import (
    ITEM_TITLE_MAX,
    TypeRow,
    member_findings,
    override_toml,
    service_with,
)
from squads._errors import SquadsError

pytestmark = pytest.mark.anyio

_ROWS = ITEM_TITLE_MAX.accepting_rows()
_LETTERS = {"ascii": "x", "non-ascii": "é"}


def _lengths(number: int) -> list[int]:
    return [number - 1, number, number + 1, 200]


@pytest.mark.parametrize("letter", _LETTERS)
@pytest.mark.parametrize("number", [80, 120])
@pytest.mark.parametrize("row", _ROWS, ids=lambda r: r.id)
async def test_a_title_is_reported_exactly_when_it_is_longer_than_the_number(
    project, row: TypeRow, number: int, letter: str
) -> None:
    unselected = service_with(project.squad_dir, override_toml(row, ()))
    planted = {
        length: (await create_item(unselected, row.type, _LETTERS[letter] * length)).item.id
        for length in _lengths(number)
    }
    svc = service_with(project.squad_dir, override_toml(row, (f"item_title_max:{number}",)))
    reported = {item for _, item, _ in member_findings(await svc.check(), ITEM_TITLE_MAX)}
    for length, item_id in planted.items():
        assert (item_id in reported) is (length > number), (letter, length)


@pytest.mark.parametrize("row", _ROWS, ids=lambda r: r.id)
async def test_the_message_carries_the_length_and_the_threshold(project, row: TypeRow) -> None:
    unselected = service_with(project.squad_dir, override_toml(row, ()))
    await create_item(unselected, row.type, "y" * 121)
    svc = service_with(project.squad_dir, override_toml(row, ("item_title_max:120",)))
    (finding,) = member_findings(await svc.check(), ITEM_TITLE_MAX)
    assert finding[2] == (
        "advisory: title is 121 chars (threshold: 120)"
        " — an item title is a one-line handle; put the detail in the body"
    )


@pytest.mark.parametrize("row", _ROWS, ids=lambda r: r.id)
async def test_a_retitle_that_crosses_the_number_moves_the_finding(project, row: TypeRow) -> None:
    svc = service_with(project.squad_dir, override_toml(row, ("item_title_max:80",)))
    item = (await create_item(svc, row.type, "x" * 80)).item
    assert member_findings(await svc.check(), ITEM_TITLE_MAX) == []

    unselected = service_with(project.squad_dir, override_toml(row, ()))
    await unselected.update(item.id, title="x" * 81)
    svc = service_with(project.squad_dir, override_toml(row, ("item_title_max:80",)))
    assert [i for _, i, _ in member_findings(await svc.check(), ITEM_TITLE_MAX)] == [item.id]

    await svc.update(item.id, title="x" * 79)
    assert member_findings(await svc.check(), ITEM_TITLE_MAX) == []


@pytest.mark.parametrize("splat", [False, True], ids=["replaced", "spliced"])
async def test_an_epic_list_replaced_without_the_splat_form_loses_its_bundled_parent_rule(
    project, splat: bool
) -> None:
    row = TypeRow("epic", "epic")
    toml = override_toml(row, ("item_title_max:10",), splat=splat)
    svc = service_with(project.squad_dir, toml)
    feature = (await create_item(svc, "feature", "f")).item
    long_title = "e" * 11

    if splat:
        with pytest.raises(SquadsError, match="takes no parent"):
            await create_item(svc, "epic", long_title, parent=feature.id)
        epic = (await create_item(svc, "epic", long_title)).item
    else:
        epic = (await create_item(svc, "epic", long_title, parent=feature.id)).item
    assert [i for _, i, _ in member_findings(await svc.check(), ITEM_TITLE_MAX)] == [epic.id]
