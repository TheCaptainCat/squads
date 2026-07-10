"""The marker-safe section-edit primitive itself (``_sections.py``, CLAUDE.md invariant #3) —
the lowest layer every higher-level marker-safe claim in this suite is ultimately built on
(the marker-injection guard, tests/service/test_marker_injection_guard.py; the sub-entity
head/summary mechanism, tests/unit/test_subentity_head_and_summary_rendering.py): ``append``
touches only its target section and leaves the rest of the file untouched; a nested
discussion-region marker is distinguished from the top-level one; frontmatter round-trips
while the body is preserved verbatim; and ``find_markers``' strict regex is the primitive
that makes all of this possible.
"""

from squads import _sections as sections


def test_append_only_touches_its_target_section() -> None:
    text = (
        "intro prose\n"
        "<!-- sq:body -->\nhand-written body\n<!-- sq:body:end -->\n"
        "<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n"
    )
    out = sections.append_to_section(text, "discussion", "- [t] Robert Architect:")
    assert "hand-written body" in out
    assert "intro prose" in out
    assert out.count("<!-- sq:body -->") == 1
    disc = sections.get_section(out, "discussion")
    body = sections.get_section(out, "body")
    assert disc is not None and body is not None
    assert "- [t] Robert Architect:" in disc
    assert body.strip() == "hand-written body"


def test_a_nested_discussion_marker_is_distinct_from_the_top_level_one() -> None:
    text = (
        "<!-- sq:subtask:ST1:discussion -->\n<!-- sq:subtask:ST1:discussion:end -->\n"
        "<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n"
    )
    out = sections.append_to_section(text, "subtask:ST1:discussion", "- nested")
    nested = sections.get_section(out, "subtask:ST1:discussion")
    top = sections.get_section(out, "discussion")
    assert nested is not None and top is not None
    assert "- nested" in nested
    assert top.strip() == ""  # the top-level region is untouched


def test_frontmatter_round_trips_while_the_body_is_preserved_verbatim() -> None:
    text = (
        "---\nid: TASK-000001\nstatus: Draft\n---\n"
        "<!-- sq:body -->\nkeep me\n<!-- sq:body:end -->\n"
    )
    data, _body = sections.split_frontmatter(text)
    assert data["status"] == "Draft"
    new = sections.replace_frontmatter(text, {"id": "TASK-000001", "status": "Done"})
    assert "keep me" in new
    assert new.count("---") == 2  # exactly one frontmatter block
    assert sections.split_frontmatter(new)[0]["status"] == "Done"


def test_find_markers_strict_regex_is_the_primitive_everything_else_relies_on() -> None:
    text = "<!-- sq:body --><!-- sq:body:end --><!-- sq:discussion -->"
    assert sections.find_markers(text) == ["sq:body", "sq:body:end", "sq:discussion"]
