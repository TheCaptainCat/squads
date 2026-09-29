"""A marker-shaped ``sq:body`` region ``sq repair`` has no model for is left untouched,
silently, and never aborts the whole corpus-wide sweep or blocks another file's convergence."""

import pytest

from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._sections import get_section, replace_section
from squads._workflow import bundled_spec

pytestmark = pytest.mark.anyio


async def _seed_marker_shaped_role(svc, slug: str):
    """Seed a role whose ``sq:body`` holds a well-formed marker this sweep has no model for."""
    item = await svc.roster_item("role", slug) or await svc.activate_role(slug)
    path = item_file(svc.paths, item)
    text = path.read_text(encoding="utf-8")
    text = replace_section(
        text,
        markers.BODY,
        f"unexpected stray content {markers.open_marker('something-unexpected')}",
    )
    path.write_text(text, encoding="utf-8")
    return item, path


async def _seed_empty_role(svc, slug: str):
    """Seed a role whose ``sq:body`` is genuinely empty."""
    item = await svc.roster_item("role", slug) or await svc.activate_role(slug)
    path = item_file(svc.paths, item)
    text = replace_section(path.read_text(encoding="utf-8"), markers.BODY, "")
    path.write_text(text, encoding="utf-8")
    return item, path


async def test_a_marker_shaped_body_is_left_untouched_not_raised(svc) -> None:
    bad_item, bad_path = await _seed_marker_shaped_role(svc, "manager")

    result = await svc.repair()

    assert bad_item.id not in result.stripped
    region = (get_section(bad_path.read_text(encoding="utf-8"), markers.BODY) or "").strip()
    assert markers.open_marker("something-unexpected") in region


async def test_a_marker_shaped_body_does_not_block_a_healthy_files_own_convergence(svc) -> None:
    """A marker-shaped role must never stop a different file's own convergence in the same pass."""
    bad_item, bad_path = await _seed_marker_shaped_role(svc, "manager")
    _good_item, good_path = await _seed_empty_role(svc, "architect")

    result = await svc.repair()

    good_region = (get_section(good_path.read_text(encoding="utf-8"), markers.BODY) or "").strip()
    assert good_region == markers.open_marker(markers.view_tag("role_definition"))
    assert bad_item.id not in result.stripped
    bad_region = (get_section(bad_path.read_text(encoding="utf-8"), markers.BODY) or "").strip()
    assert "something-unexpected" in bad_region


async def test_converge_body_tag_never_raises_for_marker_shaped_content() -> None:
    """The strict licence has no raise branch for marker-shaped content."""
    from squads._services._maintenance import _converge_body_tag

    marker_shaped = (
        f"{markers.open_marker(markers.BODY)}\n"
        f"stray {markers.open_marker('something-unexpected')}\n"
        f"{markers.close_marker(markers.BODY)}\n"
    )
    out = _converge_body_tag(marker_shaped, "role_definition", bundled_spec(), "role", "dev-agent")
    assert out == marker_shaped
