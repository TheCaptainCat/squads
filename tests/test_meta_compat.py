"""The frozen legacy ``:meta`` helpers the migrations rely on (decoupled from `_discussion`)."""

from squads import _sections as sections
from squads._migrations import _meta_compat
from squads._models._enums import Status


def _legacy_subtask() -> str:
    # a pre-2 subtask: status in a [x] checkbox + (→ USn) in the heading, no :meta region
    return (
        "<!-- sq:subtask:ST1 -->\n"
        "### ST1 — [x] Validate  (→ US2)\n\n"
        "<!-- sq:subtask:ST1:body -->\nreal body\n<!-- sq:subtask:ST1:body:end -->\n\n"
        "<!-- sq:subtask:ST1:discussion -->\n<!-- sq:subtask:ST1:discussion:end -->\n"
        "<!-- sq:subtask:ST1:end -->\n"
    )


def test_upgrade_legacy_block_then_parse():
    out = _meta_compat.upgrade_legacy_block(_legacy_subtask(), "subtask", "ST1")
    (b,) = _meta_compat.list_blocks(out, "subtask")
    assert (b.status, b.story, b.title) == ("Done", "US2", "Validate")
    assert "status: Done" in out and "story: US2" in out
    assert "real body" in out and "[x]" not in out  # body kept, checkbox gone
    assert _meta_compat.upgrade_legacy_block(out, "subtask", "ST1") == out  # idempotent


def test_to_subentity_types_the_state():
    out = _meta_compat.upgrade_legacy_block(_legacy_subtask(), "subtask", "ST1")
    (b,) = _meta_compat.list_blocks(out, "subtask")
    sub = _meta_compat.to_subentity(b)
    assert sub.local_id == "ST1"
    assert sub.status is Status.DONE
    assert sub.story == "US2"


def test_has_meta_and_drop_meta():
    out = _meta_compat.upgrade_legacy_block(_legacy_subtask(), "subtask", "ST1")
    assert _meta_compat.has_meta(out, "subtask")
    dropped = _meta_compat.drop_meta(out, "subtask", "ST1")
    assert not _meta_compat.has_meta(dropped, "subtask")
    assert sections.get_section(dropped, "subtask:ST1:meta") is None
    assert "real body" in dropped  # prose preserved
