from squads import _discussion as discussion
from squads._models._enums import Severity


def test_format_comment():
    out = discussion.format_comment("2026-06-07T10:00:00Z", "Robert Architect", ["a", "b"])
    assert out == "- [2026-06-07T10:00:00Z] Robert Architect:\n  - a\n  - b"


def test_extract_mentions():
    text = "ping @qa and @reviewer, not email me@host or @ alone"
    assert discussion.extract_mentions(text) == {"qa", "reviewer"}


def test_next_local_id():
    assert discussion.next_local_id("", "story") == "US1"
    text = "<!-- sq:story:US1 --><!-- sq:story:US2 -->"
    assert discussion.next_local_id(text, "story") == "US3"
    assert discussion.next_local_id("<!-- sq:subtask:ST5 -->", "subtask") == "ST6"


def test_list_blocks():
    block = discussion.build_story_block("US1", "As an admin, I want X")
    (info,) = discussion.list_blocks(block, "story")
    assert info.local_id == "US1"
    assert info.title == "As an admin, I want X"
    assert info.status == "Todo"  # initial, from the sq-owned :meta region


def test_set_block_status():
    block = discussion.build_subtask_block("ST1", "Validate")
    updated = discussion.set_block_status(block, "subtask", "ST1", "InProgress")
    assert discussion.list_blocks(updated, "subtask")[0].status == "InProgress"
    assert "[InProgress]" not in updated  # status lives in :meta, not the heading


def test_render_summary():
    text = discussion.build_finding_block("F1", "Null deref", severity=Severity.HIGH)
    out = discussion.render_summary("finding", discussion.list_blocks(text, "finding"))
    assert "| Finding | Severity | Status | Title |" in out
    assert "🟠 high" in out and "Open" in out
    assert discussion.render_summary("finding", []) == ""


def test_upgrade_legacy_block():
    # a pre-2 subtask: status in a [x] checkbox + (→ USn) in the heading, no :meta region
    legacy = (
        "<!-- sq:subtask:ST1 -->\n"
        "### ST1 — [x] Validate  (→ US2)\n\n"
        "<!-- sq:subtask:ST1:body -->\nreal body\n<!-- sq:subtask:ST1:body:end -->\n\n"
        "<!-- sq:subtask:ST1:discussion -->\n<!-- sq:subtask:ST1:discussion:end -->\n"
        "<!-- sq:subtask:ST1:end -->\n"
    )
    out = discussion.upgrade_legacy_block(legacy, "subtask", "ST1")
    (b,) = discussion.list_blocks(out, "subtask")
    assert (b.status, b.story, b.title) == ("Done", "US2", "Validate")
    assert "status: Done" in out and "story: US2" in out
    assert "real body" in out and "[x]" not in out  # body kept, checkbox gone
    assert discussion.upgrade_legacy_block(out, "subtask", "ST1") == out  # idempotent
