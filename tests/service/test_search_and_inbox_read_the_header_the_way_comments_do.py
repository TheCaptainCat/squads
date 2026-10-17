"""Search attributes a hit to the comment whose header precedes it, using the same column-0
pattern ``comments`` uses, so an indented header-shaped line inside a comment is never mistaken
for a second comment. The snippet and location text stay name-based display text."""

import pytest

from _helpers import create_item
from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._sections import append_to_section

pytestmark = pytest.mark.anyio

TS = "2026-06-07T10:00:00Z"


async def _with_comment_holding_a_header_shaped_line(svc):
    task = (await create_item(svc, "task", "Target")).item
    await svc.comment(task.id, ["first comment"], as_slug="manager")
    path = item_file(svc.paths, task)
    text = path.read_text(encoding="utf-8")
    text = append_to_section(
        text,
        markers.DISCUSSION,
        f"- [{TS}] `manager` Catherine Manager:\n"
        "  - checklist\n"
        f"    - [{TS}] `qa` Mara Tester:\n"
        "  - [x] Done: zanzibar\n",
    )
    path.write_text(text, encoding="utf-8")
    return task


async def test_the_comment_list_and_the_search_scan_count_the_same_comments(svc):
    task = await _with_comment_holding_a_header_shaped_line(svc)
    (result,), _ = await svc.search("zanzibar")

    (hit,) = result.hits
    assert len(await svc.comments(task.id)) == 2
    assert hit.region == "discussion#2"
    assert hit.location == f"discussion — comment 2 (Catherine Manager, {TS})"
    assert hit.snippet == f"[{TS}] Catherine Manager: - [x] Done: zanzibar"


async def test_a_hit_in_a_plain_comment_keeps_the_name_based_snippet(svc):
    task = (await create_item(svc, "task", "Target")).item
    await svc.comment(task.id, ["find the quokka here"], as_slug="manager")

    (result,), _ = await svc.search("quokka")

    (hit,) = result.hits
    assert hit.region == "discussion#1"
    assert hit.location == f"discussion — comment 1 (Catherine Manager, {TS})"
    assert hit.snippet == f"[{TS}] Catherine Manager: - find the quokka here"


async def test_inbox_still_finds_a_mention_inside_a_comment(svc):
    task = (await create_item(svc, "task", "Target")).item
    await svc.comment(task.id, ["ping @qa about this"], as_slug="manager")

    hits, _ = await svc.inbox("qa")

    assert [h.item.id for h in hits] == [task.id]
    assert any("ping @qa about this" in ln.text for ln in hits[0].lines)
