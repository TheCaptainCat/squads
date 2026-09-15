"""``sq repair``'s body-tag convergence: a marker-shaped ``sq:body`` region it has no model for
must not abort the whole corpus-wide sweep, and must not raise a bare exception when it declines.

Two properties, both driven: the guard's exception class (``SquadsError``, the ordinary
user-facing-error convention — ``CLAUDE.md``), and the guard's blast radius (this one file's
region is skipped and reported; every other file in the same corpus still converges). Before
this shape existed, ``_converge_body_tag`` raised a bare ``AssertionError`` and the corpus-wide
rebuild loop had no handler for it, so one damaged role/skill body aborted the whole sweep —
including every *other* role's own, unrelated convergence.
"""

import pytest

from squads._errors import SquadsError
from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._sections import get_section, replace_section

pytestmark = pytest.mark.anyio


async def _seed_marker_shaped_role(svc, slug: str):
    """A role whose ``sq:body`` holds a well-formed marker this sweep has no model for — the
    one shape ``_converge_body_tag`` refuses to guess at."""
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


async def _seed_legacy_role(svc, slug: str):
    """A role whose ``sq:body`` holds plain-prose legacy content — the ordinary shape this
    sweep converges cleanly, used here as the "other, unrelated file" the guard must not take
    down with it."""
    item = await svc.roster_item("role", slug) or await svc.activate_role(slug)
    path = item_file(svc.paths, item)
    text = replace_section(
        path.read_text(encoding="utf-8"), markers.BODY, "# Stored Name\n\nA stale rendering."
    )
    path.write_text(text, encoding="utf-8")
    return item, path


async def test_a_marker_shaped_body_is_reported_not_raised(svc) -> None:
    bad_item, bad_path = await _seed_marker_shaped_role(svc, "manager")

    result = await svc.repair()  # must not raise

    assert any(bad_item.id in msg for msg in result.skipped)
    # The region itself is left exactly as it was — the guard's whole point.
    region = (get_section(bad_path.read_text(encoding="utf-8"), markers.BODY) or "").strip()
    assert markers.open_marker("something-unexpected") in region


async def test_a_marker_shaped_body_does_not_block_a_healthy_files_own_convergence(svc) -> None:
    bad_item, bad_path = await _seed_marker_shaped_role(svc, "manager")
    good_item, good_path = await _seed_legacy_role(svc, "architect")

    result = await svc.repair()

    # The healthy role still converged onto its placement tag...
    good_region = (get_section(good_path.read_text(encoding="utf-8"), markers.BODY) or "").strip()
    assert good_region == markers.open_marker(markers.view_tag("role_definition"))
    assert good_item.id in result.stripped
    # ...while the bad one is reported, not silently dropped, and stays untouched.
    assert any(bad_item.id in msg for msg in result.skipped)
    bad_region = (get_section(bad_path.read_text(encoding="utf-8"), markers.BODY) or "").strip()
    assert "something-unexpected" in bad_region


async def test_converge_body_tag_raises_squads_error_not_a_bare_exception() -> None:
    from squads._services._maintenance import _converge_body_tag

    marker_shaped = (
        f"{markers.open_marker(markers.BODY)}\n"
        f"stray {markers.open_marker('something-unexpected')}\n"
        f"{markers.close_marker(markers.BODY)}\n"
    )
    with pytest.raises(SquadsError):
        _converge_body_tag(marker_shaped, "role_definition")
