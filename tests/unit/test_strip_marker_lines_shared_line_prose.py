"""``_sections.strip_marker_lines`` never rewrites a prose character: a tag sharing its line
with prose loses only itself and its touching whitespace, table-driven over tag position on
the line and where that line sits in the region."""

from squads import _sections as sections

_TAG = "sq:view:x"


def _keep_other(tag: str) -> bool:
    return tag != _TAG


def _strip(text: str) -> tuple[str, list[str]]:
    return sections.strip_marker_lines(text, _keep_other)


# --------------------------------------------------------- tag position on a line with prose


def test_tag_at_line_start_with_prose_only_after_it() -> None:
    out, removed = _strip(f"<!-- {_TAG} --> foo\nbar")
    assert removed == [_TAG]
    assert out == "foo\nbar"


def test_tag_mid_line_with_prose_before_and_after() -> None:
    out, removed = _strip(f"foo <!-- {_TAG} --> bar")
    assert removed == [_TAG]
    assert out == "foo bar"


def test_tag_at_line_end_with_prose_only_before_it() -> None:
    out, removed = _strip(f"foo <!-- {_TAG} -->\nbar")
    assert removed == [_TAG]
    assert out == "foo\nbar"


def test_tag_glued_to_prose_on_both_sides_with_no_touching_whitespace_at_all() -> None:
    out, removed = _strip(f"foo<!-- {_TAG} -->bar")
    assert removed == [_TAG]
    assert out == "foobar"


# --------------------------------------------------------------- where the line sits in the region


def test_the_shared_line_is_the_regions_first_line() -> None:
    out, removed = _strip(f"foo <!-- {_TAG} --> bar\nnext line.\nlast line.")
    assert removed == [_TAG]
    assert out == "foo bar\nnext line.\nlast line."


def test_the_shared_line_is_a_middle_line() -> None:
    out, removed = _strip(f"first line.\nfoo <!-- {_TAG} --> bar\nlast line.")
    assert removed == [_TAG]
    assert out == "first line.\nfoo bar\nlast line."


def test_the_shared_line_is_the_last_line_with_a_trailing_newline() -> None:
    out, removed = _strip(f"first line.\nfoo <!-- {_TAG} --> bar\n")
    assert removed == [_TAG]
    assert out == "first line.\nfoo bar\n"


def test_the_shared_line_is_the_last_line_with_no_trailing_newline() -> None:
    out, removed = _strip(f"first line.\nfoo <!-- {_TAG} --> bar")
    assert removed == [_TAG]
    assert out == "first line.\nfoo bar"


def test_the_shared_line_is_the_regions_only_line_no_trailing_newline() -> None:
    out, removed = _strip(f"foo <!-- {_TAG} --> bar")
    assert removed == [_TAG]
    assert out == "foo bar"


# ------------------------------------------------------------- a lone tag elsewhere is unaffected


def test_a_lone_tag_on_its_own_line_elsewhere_still_takes_its_whole_line() -> None:
    """A lone tag on its own line elsewhere still takes its whole line, undisturbed."""
    text = f"foo <!-- {_TAG} --> bar\n\n<!-- {_TAG} -->\n\nmore prose."
    out, removed = _strip(text)
    assert removed == [_TAG, _TAG]
    assert out == "foo bar\n\nmore prose."
