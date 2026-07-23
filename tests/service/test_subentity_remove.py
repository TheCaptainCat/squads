"""``Service.remove_block`` — hard-delete a story/subtask/finding sub-entity: drops it from the
parent's frontmatter, excises its whole marker-scoped span (heading + head + body + discussion),
re-renders the roll-up summary, and reflogs the removal. Mirrors `remove_work_item`'s hard-delete
contract at the sub-entity scope.
"""

import pytest

from squads._errors import SquadsError
from squads._index import _reflog
from squads._index._reflog import reflog_path
from squads._itemfile import read_frontmatter

pytestmark = pytest.mark.anyio


async def _read_text(svc, item_id: str) -> str:
    item = await svc.get(item_id)
    return svc.paths.abspath(item.path).read_text(encoding="utf-8")


async def test_removing_a_story_drops_it_from_frontmatter_and_the_body(svc):
    feat = (await svc.create("feature", "F")).item
    await svc.add_story(feat.id, "Keep me", body="keep body")
    await svc.add_story(feat.id, "Remove me", body="gone body")

    await svc.remove_block(feat.id, "story", "US2")

    item = await svc.get(feat.id)
    assert [s.local_id for s in item.subentities] == ["US1"]
    text = await _read_text(svc, feat.id)
    assert "US2" not in text
    assert "gone body" not in text
    assert "keep body" in text  # sibling block untouched
    assert "<!-- sq:story:US1 -->" in text
    assert "<!-- sq:story:US1:end -->" in text


async def test_removing_a_subtask_drops_it_and_keeps_its_sibling(svc):
    task = (await svc.create("task", "T")).item
    await svc.add_subtask(task.id, "Keep me", body="keep body")
    await svc.add_subtask(task.id, "Remove me", body="gone body")

    await svc.remove_block(task.id, "subtask", "ST2")

    item = await svc.get(task.id)
    assert [s.local_id for s in item.subentities] == ["ST1"]
    text = await _read_text(svc, task.id)
    assert "ST2" not in text
    assert "keep body" in text


async def test_removing_a_finding_drops_it_and_keeps_its_sibling(svc):
    rev = (await svc.create("review", "R")).item
    await svc.add_finding(rev.id, "Keep me", severity="high", body="keep body")
    await svc.add_finding(rev.id, "Remove me", severity="low", body="gone body")

    await svc.remove_block(rev.id, "finding", "F2")

    item = await svc.get(rev.id)
    assert [s.local_id for s in item.subentities] == ["F1"]
    text = await _read_text(svc, rev.id)
    assert "F2" not in text
    assert "keep body" in text


async def test_the_rolled_up_summary_table_reflects_the_removal(svc):
    feat = (await svc.create("feature", "F")).item
    await svc.add_story(feat.id, "Keep me")
    await svc.add_story(feat.id, "Remove me")

    await svc.remove_block(feat.id, "story", "US2")

    text = await _read_text(svc, feat.id)
    summary = text.split("<!-- sq:summary -->")[1].split("<!-- sq:summary:end -->")[0]
    assert "Keep me" in summary
    assert "Remove me" not in summary


async def test_the_parent_file_stays_valid_frontmatter_after_removal(svc):
    feat = (await svc.create("feature", "F")).item
    await svc.add_story(feat.id, "Only one")
    await svc.remove_block(feat.id, "story", "US1")

    text = await _read_text(svc, feat.id)
    fm = read_frontmatter(text=text)
    assert fm.get("subentities", []) == []


async def test_removing_a_nonexistent_local_id_raises(svc):
    feat = (await svc.create("feature", "F")).item
    with pytest.raises(SquadsError):
        await svc.remove_block(feat.id, "story", "US9")


async def test_removing_a_story_still_mapped_by_a_subtask_is_refused(svc):
    feat = (await svc.create("feature", "F")).item
    await svc.add_story(feat.id, "Login")
    task = (await svc.create("task", "T", parent=feat.id)).item
    await svc.add_subtask(task.id, "Wire it up", story="US1")

    with pytest.raises(SquadsError, match="US1"):
        await svc.remove_block(feat.id, "story", "US1")

    # refused, so both sides are untouched
    assert [s.local_id for s in (await svc.get(feat.id)).subentities] == ["US1"]


async def test_removing_a_story_with_no_mapped_subtasks_succeeds(svc):
    feat = (await svc.create("feature", "F")).item
    await svc.add_story(feat.id, "Unmapped")
    task = (await svc.create("task", "T", parent=feat.id)).item
    await svc.add_subtask(task.id, "Unrelated")  # no --story given

    await svc.remove_block(feat.id, "story", "US1")
    assert (await svc.get(feat.id)).subentities == []


async def test_a_reflog_entry_is_written_for_the_removal(svc, frozen_time):
    feat = (await svc.create("feature", "F")).item
    await svc.add_story(feat.id, "Doomed")
    await svc.remove_block(feat.id, "story", "US1")

    lines = await _reflog.read_lines(reflog_path(svc.paths.squad_dir))
    matching = [ln for ln in lines if ln.op == "subentity" and ln.delta.get("op") == "remove"]
    assert len(matching) == 1
    assert matching[0].target == feat.id
    assert matching[0].delta["kind"] == "story"
    assert matching[0].delta["local_id"] == "US1"
    assert matching[0].delta["title"] == "Doomed"


async def test_a_freed_non_highest_local_id_is_not_reissued(svc):
    """Removing a middle sub-entity leaves a genuine gap: the max is unaffected, so the freed
    id is never handed to a later addition (see the note on `discussion.next_local_id`)."""
    feat = (await svc.create("feature", "F")).item
    await svc.add_story(feat.id, "US1")
    await svc.add_story(feat.id, "US2")
    await svc.remove_block(feat.id, "story", "US1")

    added = await svc.add_story(feat.id, "US3, for real this time")
    assert added.local_id == "US3"


async def test_a_freed_highest_local_id_is_reissued(svc):
    """The known, accepted exception: removing the highest-numbered sub-entity frees its
    number back up, since `next_local_id` recomputes from the live max rather than a
    persisted high-water mark. Pinned so a future change to this behaviour is a deliberate
    decision, not a silent regression."""
    feat = (await svc.create("feature", "F")).item
    await svc.add_story(feat.id, "US1")
    await svc.add_story(feat.id, "US2")
    await svc.remove_block(feat.id, "story", "US2")

    added = await svc.add_story(feat.id, "reissued")
    assert added.local_id == "US2"
