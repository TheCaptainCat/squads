"""The shared ``.index.jsonl`` generator — pure rendering/parsing, no filesystem.

This is the format agent memory and the team bulletin board both reuse; the generator itself
is tested once here, independent of either feature, per the P1 (generic-engine-once) pillar.
"""

import json

from squads._content_index import (
    GENERATED_STAMP,
    SCHEMA,
    IndexEntry,
    header_record,
    parse_index,
    render_index,
)


def test_header_record_carries_the_format_tag_and_a_plain_text_do_not_hand_edit_stamp():
    header = header_record()
    assert header["schema"] == SCHEMA == "squads.index/1"
    assert header["generated"] == GENERATED_STAMP
    assert "do not hand-edit" in header["generated"]


def test_render_index_writes_the_header_as_the_first_line_then_one_entry_per_line():
    entries = [
        IndexEntry(slug="a", filename="a.md", description="first"),
        IndexEntry(slug="b", filename="b.md", description="second"),
    ]
    text = render_index(entries)
    lines = text.splitlines()
    assert len(lines) == 3
    header = json.loads(lines[0])
    assert header == header_record()
    assert json.loads(lines[1]) == {"slug": "a", "filename": "a.md", "description": "first"}
    assert json.loads(lines[2]) == {"slug": "b", "filename": "b.md", "description": "second"}


def test_render_index_preserves_caller_supplied_entry_order():
    """Line position is load-bearing (the board's positional ordinal *is* the line number), so
    the generator must never reorder/sort entries itself."""
    entries = [
        IndexEntry(slug="z", filename="z.md", description=""),
        IndexEntry(slug="a", filename="a.md", description=""),
    ]
    _, parsed = parse_index(render_index(entries))
    assert [e.slug for e in parsed] == ["z", "a"]


def test_render_index_with_no_entries_is_just_the_header_line():
    text = render_index([])
    lines = text.splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == header_record()


def test_parse_index_round_trips_render_index_output():
    entries = [
        IndexEntry(slug="scale-tests-slow", filename="scale-tests-slow.md", description="d1"),
        IndexEntry(slug="pyright-strict", filename="pyright-strict.md", description="d2"),
    ]
    header, parsed = parse_index(render_index(entries))
    assert header == header_record()
    assert parsed == entries


def test_parse_index_on_empty_text_returns_an_empty_header_and_no_entries():
    assert parse_index("") == ({}, [])
