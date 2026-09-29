"""``sq repair``'s retired-region sweep leaves a ``sq:view:<name>`` tag untouched, alone,
alongside authored prose, alongside a region that genuinely does get stripped, and across a
repeated sweep — always byte-identical."""

from pathlib import Path

import pytest

from _helpers import create_item
from squads._index._resolver import item_file
from squads._models import _markers as markers

pytestmark = pytest.mark.anyio

_BUNDLED_VIEW = "milestone_rollup"


def _path(svc, item) -> Path:
    return item_file(svc.paths, item)


async def test_a_body_carrying_a_view_tag_alone_survives_the_sweep_byte_identical(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    await svc.add_view(task.id, _BUNDLED_VIEW)
    path = _path(svc, task)
    before = path.read_bytes()

    await svc.repair()

    assert path.read_bytes() == before
    assert markers.view_tag(_BUNDLED_VIEW) in path.read_text(encoding="utf-8")


async def test_a_view_tag_alongside_authored_prose_survives_the_sweep_byte_identical(
    svc,
) -> None:
    task = (await create_item(svc, "task", "T")).item
    await svc.set_body(task.id, "Authored scope prose worth keeping.")
    await svc.add_view(task.id, _BUNDLED_VIEW)
    path = _path(svc, task)
    before = path.read_bytes()

    await svc.repair()

    assert path.read_bytes() == before


#: A summary region in the shape the retired writer produced, planted directly on disk.
_SUMMARY_REGION = """<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | a story |
<!-- sq:summary:end -->

"""


async def test_a_view_tag_survives_while_a_genuinely_retired_region_in_the_same_file_is_stripped(
    svc,
) -> None:
    """A view tag survives while a genuinely retired region in the same file is stripped."""
    feat = (await create_item(svc, "feature", "F")).item
    await svc.add_story(feat.id, "a story")
    await svc.add_view(feat.id, _BUNDLED_VIEW)
    path = _path(svc, feat)
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        markers.open_marker(markers.STORIES),
        _SUMMARY_REGION + markers.open_marker(markers.STORIES),
        1,
    )
    path.write_text(text, encoding="utf-8")
    assert "sq:summary" in text

    await svc.repair()

    after_text = path.read_text(encoding="utf-8")
    assert "sq:summary" not in after_text
    assert markers.view_tag(_BUNDLED_VIEW) in after_text


async def test_repeated_sweeps_leave_a_view_tag_bearing_file_byte_identical(svc) -> None:
    """A second ``sq repair`` on an already-clean, view-tag-bearing file is a true no-op."""
    task = (await create_item(svc, "task", "T")).item
    await svc.add_view(task.id, _BUNDLED_VIEW)
    path = _path(svc, task)

    await svc.repair()
    after_first = path.read_bytes()
    await svc.repair()

    assert path.read_bytes() == after_first
