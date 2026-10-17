"""`Service.check()` over the selection table. For every opt-in policy check and every type row
that accepts it, an offender and a clean neighbour are planted under a spec that selects
nothing; then the same squad is reopened under each selection shape. Unselected, nothing is
reported; selected, the offender earns exactly one finding at the shape's level and the clean
neighbour stays silent; selected on another type only, this type stays silent while the other
reports.
"""

import pytest

from _helpers import create_item
from _selection_table import (
    MEMBERS,
    Member,
    Shape,
    TypeRow,
    member_findings,
    override_toml,
    service_with,
)

pytestmark = pytest.mark.anyio

_SHAPE_CELLS = [
    (m, r, name, shape)
    for m in MEMBERS.values()
    for r in m.accepting_rows()
    for name, shape in m.shapes.items()
]
_SHAPE_IDS = [f"{m.name}-{r.id}-{name}" for m, r, name, _ in _SHAPE_CELLS]
_ROW_CELLS = [(m, r) for m in MEMBERS.values() for r in m.accepting_rows()]
_ROW_IDS = [f"{m.name}-{r.id}" for m, r in _ROW_CELLS]


@pytest.mark.parametrize(("member", "row", "name", "shape"), _SHAPE_CELLS, ids=_SHAPE_IDS)
async def test_a_type_reports_its_offender_exactly_when_it_selects_the_check(
    project, member: Member, row: TypeRow, name: str, shape: Shape
) -> None:
    planted = await member.plant(service_with(project.squad_dir, override_toml(row, ())), row)
    svc = service_with(project.squad_dir, override_toml(row, shape.entries))
    found = member_findings(await svc.check(), member)
    if shape.level is None:
        assert found == [], name
        return
    assert [(lvl, item) for lvl, item, _ in found] == [(shape.level, planted.offender)]
    assert found[0][2] == planted.message
    assert planted.clean not in {item for _, item, _ in found}


@pytest.mark.parametrize(("member", "row"), _ROW_CELLS, ids=_ROW_IDS)
async def test_selecting_the_check_on_another_type_leaves_this_type_silent(
    project, member: Member, row: TypeRow
) -> None:
    other = next(r for r in member.accepting_rows() if r.type != row.type and r.id != row.id)
    here = await member.plant(service_with(project.squad_dir, override_toml(row, ())), row)
    toml = override_toml(row, ()) + "\n" + override_toml(other, member.plain)
    svc = service_with(project.squad_dir, toml)
    elsewhere = await member.plant(svc, other)
    items = {item for _, item, _ in member_findings(await svc.check(), member)}
    assert elsewhere.offender in items
    assert here.offender not in items


@pytest.mark.parametrize("member", MEMBERS.values(), ids=lambda m: m.name)
async def test_a_squad_that_selects_nothing_reports_no_finding_of_the_check(
    project, member: Member
) -> None:
    svc = service_with(project.squad_dir, "")
    for row in member.accepting_rows():
        if row.declaration:
            continue
        await member.plant(svc, row)
    assert member_findings(await svc.check(), member) == []
    await create_item(svc, "task", "neighbour")
    assert member_findings(await svc.check(), member) == []
