"""``sq repair``'s retired-region sweep (``_retired_region_tags`` /
``_strip_retired_regions``, ``_services/_maintenance.py``) needs **no change** for the
unpaired ``sq:view:<name>`` family, and this proves it rather than asserting it in a comment.

The sweep admits only the fixed ``sq:summary`` tag and tags ending in ``:head`` by name, and
separately skips any tag whose region is not balanced in the file at all — so a view tag is
excluded twice over: it never matches the name shape, and it has no closing marker to make a
balanced region in the first place. A body carrying a view tag — alone, alongside authored
prose, alongside a retired region that genuinely does get stripped, and across a repeated
sweep — must come back byte-identical.
"""

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
    await svc.insert_view(task.id, _BUNDLED_VIEW)
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
    await svc.insert_view(task.id, _BUNDLED_VIEW)
    path = _path(svc, task)
    before = path.read_bytes()

    await svc.repair()

    assert path.read_bytes() == before


#: A summary region in the shape the retired writer produced -- nothing on the live write path
#: produces this any more (that is the whole premise of the sweep), so it is planted directly
#: on disk exactly as tests/service/test_repair_strips_only_retired_regions.py does.
_SUMMARY_REGION = """<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | a story |
<!-- sq:summary:end -->

"""


async def test_a_view_tag_survives_while_a_genuinely_retired_region_in_the_same_file_is_stripped(
    svc,
) -> None:
    """The sweep still does its real job on the same file -- the exemption is narrow to the
    view family, not a side effect of the sweep going inert."""
    feat = (await create_item(svc, "feature", "F")).item
    await svc.add_story(feat.id, "a story")
    await svc.insert_view(feat.id, _BUNDLED_VIEW)
    path = _path(svc, feat)
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        markers.open_marker(markers.STORIES),
        _SUMMARY_REGION + markers.open_marker(markers.STORIES),
        1,
    )
    path.write_text(text, encoding="utf-8")
    assert "sq:summary" in text  # sanity: a retired region really is present

    await svc.repair()

    after_text = path.read_text(encoding="utf-8")
    assert "sq:summary" not in after_text  # the retired region is gone -- the sweep still works
    assert markers.view_tag(_BUNDLED_VIEW) in after_text  # the view tag rode through untouched


async def test_repeated_sweeps_leave_a_view_tag_bearing_file_byte_identical(svc) -> None:
    """Idempotence: a second ``sq repair`` on an already-clean, view-tag-bearing file is a
    true no-op, not merely one that reports nothing changed."""
    task = (await create_item(svc, "task", "T")).item
    await svc.insert_view(task.id, _BUNDLED_VIEW)
    path = _path(svc, task)

    await svc.repair()
    after_first = path.read_bytes()
    await svc.repair()

    assert path.read_bytes() == after_first
