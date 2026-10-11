"""`no_status_banner` runs for a type only when that type's own `validators` list names it.
The selection table drives every type row through every selection shape and every banner input
shape: with nothing selected nothing is reported on any input; selected, each offending input
earns the same message the check always produced, at the level the entry declares, and each
clean input stays silent. Every silence is asserted on a type that selects the check.
"""

import pytest

from _helpers import create_item
from _selection_table import (
    ALL_ROWS,
    BANNER_CLEAN,
    BANNER_OFFENDERS,
    BUNDLED_ROWS,
    TypeRow,
    banner_findings,
    override_toml,
    plant_banner_items,
    service_with,
    write_override,
)
from squads._errors import SquadsError
from squads._services import _service as service

pytestmark = pytest.mark.anyio

#: Selection shape -> (validators entries, level the finding carries).
SELECTED_SHAPES = {
    "bare": (("no_status_banner",), "warn"),
    "warn-suffix": (("no_status_banner@warn",), "warn"),
    "error-suffix": (("no_status_banner@error",), "error"),
}


def _expected(row: TypeRow, level: str) -> dict[str, tuple[str, str]]:
    """The findings the offending inputs earn on a type that selects the check."""
    found: dict[str, tuple[str, str]] = {}
    for name, (body, _description, message) in BANNER_OFFENDERS.items():
        if body is not None and not row.body_authorable:
            continue
        found[name] = (
            level,
            f"{message} — move state to frontmatter or a dated discussion comment",
        )
    return found


def _other_type(row: TypeRow) -> TypeRow:
    return next(r for r in BUNDLED_ROWS if r.type not in {row.type, "role"})


@pytest.mark.parametrize("row", ALL_ROWS, ids=lambda r: r.id)
async def test_nothing_is_reported_on_any_input_when_the_type_selects_nothing(project, row) -> None:
    svc = service_with(project.squad_dir, override_toml(row, ()))
    planted = await plant_banner_items(svc, row)
    assert planted
    assert banner_findings(await svc.check(), planted) == {}


@pytest.mark.parametrize("shape", SELECTED_SHAPES)
@pytest.mark.parametrize("row", ALL_ROWS, ids=lambda r: r.id)
async def test_a_selecting_type_reports_each_offender_and_no_clean_input(
    project, row, shape
) -> None:
    entries, level = SELECTED_SHAPES[shape]
    svc = service_with(project.squad_dir, override_toml(row, entries))
    planted = await plant_banner_items(svc, row)
    assert set(BANNER_CLEAN) & set(planted)  # a clean neighbour exists on this very type
    assert banner_findings(await svc.check(), planted) == _expected(row, level)


@pytest.mark.parametrize("row", ALL_ROWS, ids=lambda r: r.id)
async def test_selecting_the_check_on_a_different_type_leaves_this_type_silent(
    project, row
) -> None:
    other = _other_type(row)
    toml = override_toml(row, (), others={other.type: ("no_status_banner",)})
    svc = service_with(project.squad_dir, toml)
    own = await plant_banner_items(svc, row)
    selecting = await plant_banner_items(svc, other)
    issues = await svc.check()
    assert banner_findings(issues, own) == {}
    assert banner_findings(issues, selecting) == _expected(other, "warn")


@pytest.mark.parametrize("row", ALL_ROWS, ids=lambda r: r.id)
async def test_writing_the_body_succeeds_even_when_the_check_is_selected_at_error(
    project, row
) -> None:
    svc = service_with(project.squad_dir, override_toml(row, ("no_status_banner@error",)))
    planted = await plant_banner_items(svc, row)
    assert planted  # every write above went through
    assert any(i.level == "error" for i in await svc.check())


async def test_a_number_on_the_check_is_refused_when_the_spec_loads(project) -> None:
    row = next(r for r in BUNDLED_ROWS if r.type == "decision")
    with pytest.raises(SquadsError, match="takes no param"):
        service_with(project.squad_dir, override_toml(row, ("no_status_banner:5",)))


async def test_an_epic_list_without_the_splat_reports_the_banner_and_accepts_a_parent(
    project,
) -> None:
    write_override(project.squad_dir, '[items.epic]\nvalidators = ["no_status_banner"]\n')
    svc = service.open_service()
    feature = (await create_item(svc, "feature", "F")).item
    epic = (await create_item(svc, "epic", "E", parent=feature.id)).item
    await svc.set_body(epic.id, "STATUS: Proposed")
    assert [i.item for i in await svc.check() if "banner" in i.message] == [epic.id]


async def test_an_epic_list_with_the_splat_reports_the_banner_and_still_refuses_a_parent(
    project,
) -> None:
    row = next(r for r in BUNDLED_ROWS if r.type == "epic")
    svc = service_with(project.squad_dir, override_toml(row, ("no_status_banner",)))
    feature = (await create_item(svc, "feature", "F")).item
    with pytest.raises(SquadsError, match="takes no parent"):
        await create_item(svc, "epic", "E", parent=feature.id)
    epic = (await create_item(svc, "epic", "E")).item
    await svc.set_body(epic.id, "STATUS: Proposed")
    assert [i.item for i in await svc.check() if "banner" in i.message] == [epic.id]
