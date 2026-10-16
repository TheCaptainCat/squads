"""A role's or generated skill's own view cannot be disabled, so no check finding or error about
its tag names `view disable`: a table of broken tag shapes, each read through `sq check`."""

import pytest

from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._sections import get_section, replace_section

pytestmark = pytest.mark.anyio

_ENABLED = markers.open_marker(markers.view_tag("role_definition"))
_DISABLED = markers.open_marker(markers.view_tag("role_definition", disabled=True))

#: shape -> the body region the role is left with
SHAPES = {
    "missing-tag": "",
    "duplicate-tag": f"{_ENABLED}\n{_ENABLED}",
    "conflicting-states": f"{_ENABLED}\n{_DISABLED}",
}


@pytest.mark.parametrize("shape", list(SHAPES))
async def test_no_finding_names_view_disable_for_a_generated_hosts_own_view(shape, svc) -> None:
    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    path = item_file(svc.paths, role)
    text = path.read_text(encoding="utf-8")
    assert get_section(text, markers.BODY) is not None
    path.write_text(replace_section(text, markers.BODY, SHAPES[shape]), encoding="utf-8")

    issues = await svc.check()

    assert [i for i in issues if i.item == path.name], "the shape is reported"
    assert not [i.message for i in issues if "view disable" in i.message]


async def test_an_absent_region_names_only_the_restoring_command(svc) -> None:
    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    path = item_file(svc.paths, role)
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace(markers.open_marker(markers.BODY), "")
        .replace(markers.close_marker(markers.BODY), "")
        .replace(_ENABLED, ""),
        encoding="utf-8",
    )

    issues = await svc.check()

    found = [i.message for i in issues if i.item == path.name]
    assert any("view add role_definition" in m for m in found), found
    assert not [m for m in found if "view disable" in m]
