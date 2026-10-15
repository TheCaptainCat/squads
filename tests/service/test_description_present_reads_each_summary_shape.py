"""`description_present` over the summary shapes of every type that accepts it: a summary that
is empty or only whitespace of any kind is reported, a visible character is not; setting a
summary clears the finding and clearing it brings the finding back.
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

pytestmark = pytest.mark.anyio

#: Summary shape -> (the summary, whether it is reported).
_SHAPES = {
    "never-set": ("", True),
    "spaces-only": ("   ", True),
    "tab-only": ("\t", True),
    "newline-only": ("\n", True),
    "mixed-whitespace": (" \t\n ", True),
    "non-breaking-space-only": (chr(0xA0), True),
    "one-visible-character": ("x", False),
    "a-sentence": ("Adds the thing.", False),
}


@pytest.mark.parametrize("shape", _SHAPES)
@pytest.mark.parametrize("row", DESCRIPTION_PRESENT.accepting_rows(), ids=lambda r: r.id)
async def test_a_summary_is_reported_exactly_when_it_holds_no_visible_character(
    project, row: TypeRow, shape: str
) -> None:
    summary, reported = _SHAPES[shape]
    svc = service_with(project.squad_dir, override_toml(row, ("description_present",)))
    item = (await create_item(svc, row.type, "t", description=summary)).item
    found = member_findings(await svc.check(), DESCRIPTION_PRESENT)
    assert [i for _, i, _ in found] == ([item.id] if reported else []), repr(summary)


@pytest.mark.parametrize("row", DESCRIPTION_PRESENT.accepting_rows(), ids=lambda r: r.id)
async def test_setting_the_summary_clears_the_finding_and_clearing_it_brings_it_back(
    project, row: TypeRow
) -> None:
    svc = service_with(project.squad_dir, override_toml(row, ("description_present",)))
    item = (await create_item(svc, row.type, "t")).item
    assert member_findings(await svc.check(), DESCRIPTION_PRESENT)
    await svc.update(item.id, description="Now summarised.")
    assert member_findings(await svc.check(), DESCRIPTION_PRESENT) == []
    unselected = service_with(project.squad_dir, override_toml(row, ()))
    await unselected.update(item.id, description="")
    svc = service_with(project.squad_dir, override_toml(row, ("description_present",)))
    assert [i for _, i, _ in member_findings(await svc.check(), DESCRIPTION_PRESENT)] == [item.id]
