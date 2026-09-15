"""``_sections.iter_marker_spans`` — the positional counterpart to ``find_markers``: every
well-formed marker tag in a string, as ``(tag, start, end)``, in file order. Read-time view-tag
expansion is built on this rather than on ``find_markers`` because it must substitute matches
without re-scanning the substituted text — positions computed once, against the text exactly as
given, are what make that possible.
"""

from squads import _sections as sections


def test_no_markers_returns_an_empty_list() -> None:
    assert sections.iter_marker_spans("just some prose, no markers at all") == []


def test_a_single_marker_reports_its_tag_with_the_sq_prefix_still_on_and_its_exact_span() -> None:
    text = "before <!-- sq:view:x --> after"
    spans = sections.iter_marker_spans(text)
    assert len(spans) == 1
    tag, start, end = spans[0]
    assert tag == "sq:view:x"  # the raw form, matching find_markers's own convention
    assert text[start:end] == "<!-- sq:view:x -->"


def test_several_markers_are_reported_in_file_order_with_non_overlapping_spans() -> None:
    text = "<!-- sq:view:a --> middle <!-- sq:view:b -->"
    spans = sections.iter_marker_spans(text)
    assert [tag for tag, _, _ in spans] == ["sq:view:a", "sq:view:b"]
    (_, s0, e0), (_, s1, e1) = spans
    assert e0 <= s1  # non-overlapping and in order
    assert text[s0:e0] == "<!-- sq:view:a -->"
    assert text[s1:e1] == "<!-- sq:view:b -->"


def test_matches_every_well_formed_tag_the_same_way_find_markers_does() -> None:
    """The positional scan must agree with the tag-only scan on *which* strings match — it is
    a strict superset of information, not a different notion of "well-formed"."""
    text = "<!-- sq:body --> some prose <!-- sq:view:milestone_rollup --> more <!-- sq:body:end -->"
    assert [tag for tag, _, _ in sections.iter_marker_spans(text)] == sections.find_markers(text)


def test_a_quoted_tag_still_matches_position_is_not_a_safety_mechanism() -> None:
    """Mirrors ``find_markers``'s own documented control: backticks neutralise nothing, so a
    caller substituting on these spans must not assume quoting makes a span inert."""
    text = "prose mentioning `<!-- sq:view:x -->` inline"
    spans = sections.iter_marker_spans(text)
    assert len(spans) == 1
    assert spans[0][0] == "sq:view:x"
