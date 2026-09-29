"""Across every writer that can touch a ``sq:body`` region in one chain, the seeded tag stays
exactly once, ``sq check`` stays clean, and repeating a step changes no byte."""

import json

import pytest

from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._sections import get_section

pytestmark = pytest.mark.anyio

_TAG = markers.view_tag("milestone_rollup")
_TAG_MARKER = markers.open_marker(_TAG)
_DISABLED_MARKER = markers.open_marker(markers.view_tag("milestone_rollup", disabled=True))


def _region(svc, item) -> str:
    path = item_file(svc.paths, item)
    return (get_section(path.read_text(encoding="utf-8"), markers.BODY) or "").strip()


async def _assert_exactly_once_and_clean(svc, item) -> str:
    region = _region(svc, item)
    tag_count = region.count(_TAG_MARKER) + region.count(_DISABLED_MARKER)
    assert tag_count == 1, f"expected exactly one milestone_rollup tag, found {tag_count}: " + repr(
        region
    )
    issues = [i for i in await svc.check() if i.item == item.id]
    assert not issues, issues
    return region


async def test_the_tag_survives_exactly_once_and_check_stays_clean_across_every_writer(
    svc,
) -> None:
    created = await svc.create(
        "milestone", "Pipeline invariants", author="manager", body="An explicit creation body."
    )
    milestone = created.item
    region = await _assert_exactly_once_and_clean(svc, milestone)
    assert region.startswith("An explicit creation body.")
    idempotent = await _assert_exactly_once_and_clean(svc, milestone)
    assert idempotent == region

    await svc.set_body(milestone.id, "Replaced scope prose.", force=True)
    region = await _assert_exactly_once_and_clean(svc, milestone)
    await svc.set_body(milestone.id, "Replaced scope prose.", force=True)
    assert await _assert_exactly_once_and_clean(svc, milestone) == region

    await svc.set_body(milestone.id, "More detail.", append=True)
    region = await _assert_exactly_once_and_clean(svc, milestone)
    assert region.startswith("Replaced scope prose.")
    assert "More detail." in region

    lines = json.dumps(
        {
            "op": "body",
            "target": milestone.id,
            "body": "Imported prose.",
            "force": True,
            "as": "manager",
        }
    )
    result = await svc.import_events(lines)
    assert result.plan.ok, [i.message for i in result.plan.issues]
    region = await _assert_exactly_once_and_clean(svc, milestone)
    assert region.startswith("Imported prose.")

    added = await svc.add_view(milestone.id, "milestone_rollup")
    assert added is False, "the tag is already present; view add must report a no-op"
    region = await _assert_exactly_once_and_clean(svc, milestone)

    disabled = await svc.disable_view(milestone.id, "milestone_rollup")
    assert disabled is True
    region = await _assert_exactly_once_and_clean(svc, milestone)
    assert _DISABLED_MARKER in region
    disabled_again = await svc.disable_view(milestone.id, "milestone_rollup")
    assert disabled_again is False
    assert await _assert_exactly_once_and_clean(svc, milestone) == region

    reenabled = await svc.add_view(milestone.id, "milestone_rollup")
    assert reenabled is True
    region = await _assert_exactly_once_and_clean(svc, milestone)
    assert _TAG_MARKER in region
    assert _DISABLED_MARKER not in region
