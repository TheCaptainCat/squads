"""``reinstate_absent_body_region``, tested as a pure function of a file's raw text: turns a
hand-deleted ``sq:body``/``sq:body:end`` pair into a clean, safe reinstatement, or a clean
refusal when reinstating would be a guess about which lines are authored."""

from squads._models import _markers as markers
from squads._sections import get_section
from squads._views import reinstate_absent_body_region

_FRONTMATTER = "---\nid: ROLE-1\ntype: role\n---\n"
_TAIL = "\n## Discussion\n\n<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n"
_TAG = markers.open_marker(markers.view_tag("role_definition"))
_OTHER_TAG = markers.open_marker(markers.view_tag("some_other_view"))


def test_a_present_pair_is_left_alone() -> None:
    """Nothing to reinstate when the pair is already there."""
    body = f"{markers.open_marker(markers.BODY)}\nstuff\n{markers.close_marker(markers.BODY)}\n"
    text = f"{_FRONTMATTER}{body}{_TAIL}"
    assert reinstate_absent_body_region(text) is None


def test_the_leading_tag_alone_is_safely_wrapped() -> None:
    text = f"{_FRONTMATTER}{_TAG}{_TAIL}"
    out = reinstate_absent_body_region(text)
    assert out is not None
    region = get_section(out, markers.BODY)
    assert region is not None
    assert _TAG in region
    assert "## Discussion" in out


def test_several_leading_tags_are_all_wrapped_together() -> None:
    text = f"{_FRONTMATTER}{_TAG}\n\n{_OTHER_TAG}{_TAIL}"
    out = reinstate_absent_body_region(text)
    assert out is not None
    region = get_section(out, markers.BODY) or ""
    assert _TAG in region
    assert _OTHER_TAG in region


def test_a_genuinely_empty_span_is_wrapped_as_an_empty_region() -> None:
    text = f"{_FRONTMATTER}{_TAIL}"
    out = reinstate_absent_body_region(text)
    assert out is not None
    assert (get_section(out, markers.BODY) or "").strip() == ""
    assert "## Discussion" in out


def test_a_blank_only_file_with_no_tail_at_all_is_wrapped() -> None:
    """A blank-only file with no tail at all is still safely wrapped."""
    text = f"{_FRONTMATTER}\n\n"
    out = reinstate_absent_body_region(text)
    assert out is not None
    assert (get_section(out, markers.BODY) or "").strip() == ""


def test_real_prose_right_after_the_frontmatter_is_refused() -> None:
    """Real prose right after the frontmatter, with no tag or marker, is refused."""
    text = f"{_FRONTMATTER}Some hand-typed replacement text.{_TAIL}"
    assert reinstate_absent_body_region(text) is None


def test_real_prose_after_a_leading_tag_is_also_refused() -> None:
    """Real prose after a leading tag is also refused, rather than orphaning it."""
    text = f"{_FRONTMATTER}{_TAG}\nAn author's own sentence, not a heading.{_TAIL}"
    assert reinstate_absent_body_region(text) is None


def test_no_frontmatter_at_all_is_refused() -> None:
    text = f"{_TAG}{_TAIL}"
    assert reinstate_absent_body_region(text) is None


# ------------------------------------------- heading-led prose: table over region/tag shape


def test_heading_led_prose_with_no_discussion_region_at_all_is_refused() -> None:
    """Heading-led prose with no discussion region at all is refused, never guessed at."""
    text = f"{_FRONTMATTER}# Dev Agent\n\nA minimal developer role for corpus testing.\n"
    assert reinstate_absent_body_region(text) is None


def test_heading_led_prose_after_a_leading_tag_with_no_discussion_region_is_refused() -> None:
    """The same shape, with a leading tag ahead of the heading-led prose, is also refused."""
    text = f"{_FRONTMATTER}{_TAG}\n# Dev Agent\n\nA minimal developer role.\n"
    assert reinstate_absent_body_region(text) is None


def test_heading_led_prose_running_on_into_the_real_discussion_region_is_refused() -> None:
    """Heading-led prose running on into the real discussion region is refused, not
    mistaken for that region's own heading."""
    text = f"{_FRONTMATTER}# Dev Agent\n\nA minimal developer role for corpus testing.\n{_TAIL}"
    assert reinstate_absent_body_region(text) is None


def test_heading_led_prose_followed_by_an_unrelated_marker_is_refused() -> None:
    """A heading followed by an unrelated marker is refused; only the discussion pair works."""
    text = (
        f"{_FRONTMATTER}# Dev Agent\n\nSome prose.\n"
        f"{markers.open_marker('note')}\nstuff\n{markers.close_marker('note')}\n"
    )
    assert reinstate_absent_body_region(text) is None


def test_the_genuine_discussion_heading_is_still_accepted() -> None:
    """The genuine discussion heading is still accepted and wrapped."""
    text = f"{_FRONTMATTER}{_TAG}{_TAIL}"
    out = reinstate_absent_body_region(text)
    assert out is not None
    region = get_section(out, markers.BODY)
    assert region is not None
    assert _TAG in region
    assert "## Discussion" in out


def test_the_headings_own_depth_and_text_are_never_read_only_the_marker() -> None:
    """The heading's own depth and text are never read, only the marker that follows it."""
    text = f"{_FRONTMATTER}{_TAG}\n### Notes\n\n{markers.open_marker(markers.DISCUSSION)}\n"
    out = reinstate_absent_body_region(text)
    assert out is not None
    region = get_section(out, markers.BODY)
    assert region is not None
    assert _TAG in region


def test_reinstating_never_deletes_or_reorders_a_single_byte_elsewhere() -> None:
    """Reinstating never deletes or reorders a single byte elsewhere."""
    text = f"{_FRONTMATTER}{_TAG}{_TAIL}"
    out = reinstate_absent_body_region(text)
    assert out is not None
    assert out.startswith(_FRONTMATTER)
    assert out.endswith(_TAIL)
