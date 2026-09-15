"""``_sections.insert_unpaired_marker``/``remove_unpaired_marker`` — the marker-safe primitive
a placement verb inserts or removes a self-closing (unpaired) marker line through, anchored at
one region's end.

Table-driven over marker *position* within the region (start/middle/end, several tags, a tag
adjacent to another region's markers) and body *shape* (empty, no tag at all) — the failure mode
this project keeps hitting is a test that only exercises the shape its author had in mind.
"""

import pytest

from squads import _sections as sections

_BODY = "body"
_TAG = "view:milestone_rollup"
_OTHER_TAG = "view:other"
_MARKER = "<!-- sq:view:milestone_rollup -->"


def _body_region(inner: str) -> str:
    return f"<!-- sq:body -->{inner}<!-- sq:body:end -->"


# --------------------------------------------------------------------------- insert


def test_insert_into_an_empty_region_anchors_at_the_end() -> None:
    text = _body_region("\n")
    out, inserted = sections.insert_unpaired_marker(text, _BODY, _TAG)
    assert inserted is True
    assert sections.get_section(out, _BODY) == f"\n{_MARKER}\n"


def test_insert_after_existing_prose_anchors_at_the_regions_end() -> None:
    text = _body_region("\nSome authored prose.\n")
    out, inserted = sections.insert_unpaired_marker(text, _BODY, _TAG)
    assert inserted is True
    assert sections.get_section(out, _BODY) == f"\nSome authored prose.\n{_MARKER}\n"
    assert "Some authored prose." in out  # authored text preserved verbatim


def test_insert_is_idempotent_when_the_tag_is_already_present_anywhere_in_the_region() -> None:
    """Already present at the *start* of the region — not just where insert would itself have
    placed it — still short-circuits: idempotency checks presence, not position."""
    text = _body_region(f"\n{_MARKER}\nSome prose after it.\n")
    out, inserted = sections.insert_unpaired_marker(text, _BODY, _TAG)
    assert inserted is False
    assert out == text  # returned unchanged, not merely equal in content
    assert out.count(_MARKER) == 1  # never duplicated


def test_insert_already_present_in_the_middle_is_still_idempotent() -> None:
    text = _body_region(f"\nBefore.\n{_MARKER}\nAfter.\n")
    out, inserted = sections.insert_unpaired_marker(text, _BODY, _TAG)
    assert inserted is False
    assert out == text


def test_insert_a_second_distinct_tag_adds_it_without_disturbing_the_first() -> None:
    text = _body_region(f"\nProse.\n{_MARKER}\n")
    out, inserted = sections.insert_unpaired_marker(text, _BODY, _OTHER_TAG)
    assert inserted is True
    inner = sections.get_section(out, _BODY)
    assert inner is not None
    assert _MARKER in inner
    assert "<!-- sq:view:other -->" in inner
    assert inner.index(_MARKER) < inner.index("<!-- sq:view:other -->")  # order preserved


def test_insert_leaves_a_sibling_region_and_its_markers_untouched() -> None:
    """A tag adjacent to another region's markers: inserting into ``body`` must not touch the
    neighbouring ``discussion`` region at all."""
    text = (
        _body_region("\nProse.\n")
        + "\n<!-- sq:discussion -->\n- a comment\n<!-- sq:discussion:end -->\n"
    )
    out, inserted = sections.insert_unpaired_marker(text, _BODY, _TAG)
    assert inserted is True
    assert sections.get_section(out, "discussion") == "\n- a comment\n"
    assert out.count("<!-- sq:discussion -->") == 1
    assert out.count("<!-- sq:discussion:end -->") == 1


def test_insert_into_a_missing_region_raises_key_error() -> None:
    with pytest.raises(KeyError):
        sections.insert_unpaired_marker("no markers here at all", _BODY, _TAG)


# --------------------------------------------------------------------------- remove


def test_remove_the_only_tag_restores_the_empty_region() -> None:
    text = _body_region(f"\n{_MARKER}\n")
    out, removed = sections.remove_unpaired_marker(text, _BODY, _TAG)
    assert removed is True
    assert sections.get_section(out, _BODY) == "\n"


def test_remove_a_tag_at_the_start_of_the_region_preserves_prose_that_follows() -> None:
    text = _body_region(f"\n{_MARKER}\nProse after it.\n")
    out, removed = sections.remove_unpaired_marker(text, _BODY, _TAG)
    assert removed is True
    assert sections.get_section(out, _BODY) == "\nProse after it.\n"


def test_remove_a_tag_in_the_middle_preserves_prose_on_both_sides() -> None:
    text = _body_region(f"\nBefore.\n{_MARKER}\nAfter.\n")
    out, removed = sections.remove_unpaired_marker(text, _BODY, _TAG)
    assert removed is True
    assert sections.get_section(out, _BODY) == "\nBefore.\nAfter.\n"


def test_remove_a_tag_at_the_end_preserves_prose_before_it() -> None:
    text = _body_region(f"\nProse before it.\n{_MARKER}\n")
    out, removed = sections.remove_unpaired_marker(text, _BODY, _TAG)
    assert removed is True
    assert sections.get_section(out, _BODY) == "\nProse before it.\n"


def test_remove_only_the_named_tag_leaves_a_second_view_tag_verbatim() -> None:
    text = _body_region(f"\n{_MARKER}\n<!-- sq:view:other -->\n")
    out, removed = sections.remove_unpaired_marker(text, _BODY, _TAG)
    assert removed is True
    assert sections.get_section(out, _BODY) == "\n<!-- sq:view:other -->\n"


def test_remove_leaves_a_sibling_region_and_its_markers_untouched() -> None:
    text = (
        _body_region(f"\n{_MARKER}\nProse.\n")
        + "\n<!-- sq:discussion -->\n- a comment\n<!-- sq:discussion:end -->\n"
    )
    out, removed = sections.remove_unpaired_marker(text, _BODY, _TAG)
    assert removed is True
    assert sections.get_section(out, "discussion") == "\n- a comment\n"


def test_remove_an_absent_tag_from_an_empty_region_is_a_safe_no_op() -> None:
    text = _body_region("\n")
    out, removed = sections.remove_unpaired_marker(text, _BODY, _TAG)
    assert removed is False
    assert out == text


def test_remove_an_absent_tag_from_a_body_carrying_only_prose_is_a_safe_no_op() -> None:
    text = _body_region("\nJust ordinary prose, no tag at all.\n")
    out, removed = sections.remove_unpaired_marker(text, _BODY, _TAG)
    assert removed is False
    assert out == text


def test_remove_from_a_missing_region_raises_key_error() -> None:
    with pytest.raises(KeyError):
        sections.remove_unpaired_marker("no markers here at all", _BODY, _TAG)


# ----------------------------------------------------------- remove: duplicate tag


def test_remove_a_duplicated_tag_removes_every_occurrence_not_just_the_first() -> None:
    """The duplicate state ``sq check`` reports as an error: ``view rm`` must actually take
    the view off the document, not report success while a second copy still renders it."""
    text = _body_region(f"\n{_MARKER}\nBetween.\n{_MARKER}\n")
    out, removed = sections.remove_unpaired_marker(text, _BODY, _TAG)
    assert removed is True
    inner = sections.get_section(out, _BODY)
    assert inner is not None
    assert _MARKER not in inner
    assert "Between." in inner


def test_remove_a_triplicated_tag_removes_all_three() -> None:
    text = _body_region(f"\n{_MARKER}\n{_MARKER}\n{_MARKER}\n")
    out, removed = sections.remove_unpaired_marker(text, _BODY, _TAG)
    assert removed is True
    assert sections.get_section(out, _BODY) == "\n"


def test_remove_a_duplicated_tag_leaves_a_different_named_tag_untouched() -> None:
    """Control: the different-name case keeps its existing behaviour verbatim — only the
    duplicate of the *named* tag is affected."""
    text = _body_region(f"\n{_MARKER}\n<!-- sq:view:other -->\n{_MARKER}\n")
    out, removed = sections.remove_unpaired_marker(text, _BODY, _TAG)
    assert removed is True
    assert sections.get_section(out, _BODY) == "\n<!-- sq:view:other -->\n"


# ------------------------------------------------------- remove: byte preservation


def test_remove_splices_without_normalising_a_region_with_no_leading_or_trailing_newline() -> None:
    """A shape squads itself never writes (every write path already goes through
    ``replace_section`` at least once) but an adopted corpus can carry: the region's inner
    content neither starts nor ends with a newline. Removing the tag must not introduce one —
    every other byte, including the absent newlines, survives verbatim."""
    text = f"<!-- sq:body -->prose{_MARKER}more prose<!-- sq:body:end -->"
    out, removed = sections.remove_unpaired_marker(text, _BODY, _TAG)
    assert removed is True
    # Exactly the marker's own bytes are gone; the two originally-adjacent words are left
    # directly concatenated -- no newline the region never had is introduced on either side.
    assert sections.get_section(out, _BODY) == "prosemore prose"
    assert not out.startswith("<!-- sq:body -->\n")  # no leading newline added
    assert out == "<!-- sq:body -->prosemore prose<!-- sq:body:end -->"


def test_remove_does_not_call_replace_section(monkeypatch: pytest.MonkeyPatch) -> None:
    """Structural proof the removal path splices directly rather than routing through
    ``replace_section``'s newline-normalising rewrite."""
    calls: list[str] = []
    original = sections.replace_section

    def spy(text: str, tag: str, new_inner: str) -> str:
        calls.append(tag)
        return original(text, tag, new_inner)

    monkeypatch.setattr(sections, "replace_section", spy)
    text = _body_region(f"\n{_MARKER}\nProse.\n")
    sections.remove_unpaired_marker(text, _BODY, _TAG)
    assert calls == [], "remove_unpaired_marker must not call replace_section"


# --------------------------------------------------------------------------- non-view control


def test_the_primitive_is_vocabulary_blind_a_non_view_unpaired_tag_behaves_identically() -> None:
    """Control: ``_sections.py`` must not special-case ``view:`` — any self-closing tag
    inserts and removes the same way, since the primitive operates on marker shape only."""
    other = "checkpoint:abc"
    other_marker = "<!-- sq:checkpoint:abc -->"
    text = _body_region("\nProse.\n")

    out, inserted = sections.insert_unpaired_marker(text, _BODY, other)
    assert inserted is True
    inner = sections.get_section(out, _BODY)
    assert inner is not None
    assert other_marker in inner

    out2, removed = sections.remove_unpaired_marker(out, _BODY, other)
    assert removed is True
    assert sections.get_section(out2, _BODY) == "\nProse.\n"
