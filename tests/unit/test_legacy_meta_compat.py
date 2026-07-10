"""The frozen legacy `:meta` region helpers the pre-0.3 migration runner relies on."""

from squads import _sections as sections
from squads._migrations import _meta_compat


def _legacy_subtask() -> str:
    # a pre-0.3 subtask: status as a [x] checkbox + (-> USn) in the heading, no :meta region
    return (
        "<!-- sq:subtask:ST1 -->\n"
        "### ST1 — [x] Validate  (→ US2)\n\n"
        "<!-- sq:subtask:ST1:body -->\nreal body\n<!-- sq:subtask:ST1:body:end -->\n\n"
        "<!-- sq:subtask:ST1:discussion -->\n<!-- sq:subtask:ST1:discussion:end -->\n"
        "<!-- sq:subtask:ST1:end -->\n"
    )


def test_upgrading_a_legacy_block_types_status_story_and_title():
    out = _meta_compat.upgrade_legacy_block(_legacy_subtask(), "subtask", "ST1")
    (block,) = _meta_compat.list_blocks(out, "subtask")
    assert (block.status, block.story, block.title) == ("Done", "US2", "Validate")
    assert "status: Done" in out and "story: US2" in out
    assert "real body" in out and "[x]" not in out  # body kept, checkbox gone
    assert _meta_compat.upgrade_legacy_block(out, "subtask", "ST1") == out  # idempotent


def test_upgraded_block_converts_to_a_typed_subentity():
    out = _meta_compat.upgrade_legacy_block(_legacy_subtask(), "subtask", "ST1")
    (block,) = _meta_compat.list_blocks(out, "subtask")
    sub = _meta_compat.to_subentity(block)
    assert sub.local_id == "ST1"
    assert sub.status == "Done"
    assert sub.story == "US2"


def test_meta_region_can_be_detected_then_dropped_leaving_prose_intact():
    out = _meta_compat.upgrade_legacy_block(_legacy_subtask(), "subtask", "ST1")
    assert _meta_compat.has_meta(out, "subtask")
    dropped = _meta_compat.drop_meta(out, "subtask", "ST1")
    assert not _meta_compat.has_meta(dropped, "subtask")
    assert sections.get_section(dropped, "subtask:ST1:meta") is None
    assert "real body" in dropped
