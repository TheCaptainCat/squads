"""A roster host whose ``sq:body`` marker pair is hand-deleted, tag text left unwrapped, is a
shape ``sq repair``/``sync``/``migrate up`` all recover safely, ``sq check`` reports as a
finding, and whose named remedy (``view add``/``view disable``) succeeds."""

import pytest

from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._sections import get_section

pytestmark = pytest.mark.anyio


async def _delete_body_markers(svc, item) -> None:
    path = item_file(svc.paths, item)
    text = path.read_text(encoding="utf-8")
    text = text.replace(f"{markers.open_marker(markers.BODY)}\n", "").replace(
        f"{markers.close_marker(markers.BODY)}\n", ""
    )
    path.write_text(text, encoding="utf-8")


async def test_repair_no_longer_crashes_and_heals_the_region(svc) -> None:
    item = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    await _delete_body_markers(svc, item)
    path = item_file(svc.paths, item)
    assert get_section(path.read_text(encoding="utf-8"), markers.BODY) is None

    await svc.repair()

    region = get_section(path.read_text(encoding="utf-8"), markers.BODY)
    assert region is not None
    assert markers.open_marker(markers.view_tag("role_definition")) in region


async def test_check_reports_a_finding_for_the_absent_region(svc) -> None:
    item = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    await _delete_body_markers(svc, item)

    issues = await svc.check()

    messages = [i.message for i in issues if i.item == item_file(svc.paths, item).name]
    assert any("missing sq:body region" in m for m in messages)


async def test_the_named_view_add_remedy_actually_works(svc) -> None:
    item = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    await _delete_body_markers(svc, item)

    changed = await svc.add_view(item.id, "role_definition")

    assert changed
    path = item_file(svc.paths, item)
    region = get_section(path.read_text(encoding="utf-8"), markers.BODY)
    assert region is not None
    assert markers.open_marker(markers.view_tag("role_definition")) in region
    issues = await svc.check()
    assert not [i for i in issues if i.item == path.name]


async def test_the_named_view_disable_remedy_also_works(svc) -> None:
    item = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    await _delete_body_markers(svc, item)

    changed = await svc.disable_view(item.id, "role_definition")

    assert changed
    path = item_file(svc.paths, item)
    region = get_section(path.read_text(encoding="utf-8"), markers.BODY)
    assert region is not None
    assert markers.open_marker(markers.view_tag("role_definition", disabled=True)) in region


async def test_real_prose_in_the_way_is_a_clean_refusal_not_a_crash(svc) -> None:
    """Real, unheaded prose in the region's span makes `view add`/`view disable` refuse cleanly."""
    from squads._errors import SquadsError

    item = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    path = item_file(svc.paths, item)
    text = path.read_text(encoding="utf-8")
    text = text.replace(f"{markers.open_marker(markers.BODY)}\n", "").replace(
        f"{markers.close_marker(markers.BODY)}\n", ""
    )
    text = text.replace(
        markers.open_marker(markers.view_tag("role_definition")),
        "An author's own hand-typed replacement, not a heading.",
    )
    path.write_text(text, encoding="utf-8")

    with pytest.raises(SquadsError, match="no sq:body region"):
        await svc.add_view(item.id, "role_definition")

    await svc.repair()
    assert get_section(path.read_text(encoding="utf-8"), markers.BODY) is None
