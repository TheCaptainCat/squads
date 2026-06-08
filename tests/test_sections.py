from squads import _sections as sections


def test_append_only_touches_target_section():
    text = (
        "intro prose\n"
        "<!-- sq:body -->\nhand-written body\n<!-- sq:body:end -->\n"
        "<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n"
    )
    out = sections.append_to_section(text, "discussion", "- [t] Robert Architect:")
    assert "hand-written body" in out  # body untouched
    assert "intro prose" in out
    assert out.count("<!-- sq:body -->") == 1
    disc = sections.get_section(out, "discussion")
    body = sections.get_section(out, "body")
    assert disc is not None and body is not None
    assert "- [t] Robert Architect:" in disc
    assert body.strip() == "hand-written body"


def test_nested_discussion_marker_is_distinct():
    text = (
        "<!-- sq:subtask:ST1:discussion -->\n<!-- sq:subtask:ST1:discussion:end -->\n"
        "<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n"
    )
    out = sections.append_to_section(text, "subtask:ST1:discussion", "- nested")
    nested = sections.get_section(out, "subtask:ST1:discussion")
    top = sections.get_section(out, "discussion")
    assert nested is not None and top is not None
    assert "- nested" in nested
    assert top.strip() == ""  # top-level untouched


def test_frontmatter_roundtrip_preserves_body():
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


def test_find_markers():
    text = "<!-- sq:body --><!-- sq:body:end --><!-- sq:discussion -->"
    assert sections.find_markers(text) == ["sq:body", "sq:body:end", "sq:discussion"]
