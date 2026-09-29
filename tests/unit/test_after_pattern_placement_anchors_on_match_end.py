"""Where an ``after(<regex>)`` view lands: right after the line holding the match's last
character, pinned across pattern shape and body position, exercising placement directly."""

import re

import pytest

from squads._models import _markers as markers
from squads._views import place_view_tags
from squads._workflow import bundled_spec
from squads._workflow._models import ViewSource, ViewSpec

_TAG = markers.open_marker(markers.view_tag("probe"))

# A three-section body, one heading per paragraph, used as every case's prose. "first"/
# "middle"/"last" below name which section a pattern targets.
_LINES = ["## Scope", "Some scope prose.", "## Details", "Some detail prose.", "## End"]


def _body(*, trailing_newline: bool) -> str:
    text = "\n".join(_LINES)
    return f"{text}\n" if trailing_newline else text


def _place(pattern: str, body: str) -> str:
    spec = bundled_spec().model_copy(
        update={
            "views": {
                "probe": ViewSpec(source=ViewSource(kind="self"), position=f"after({pattern})")
            }
        }
    )
    return place_view_tags(
        "",
        body,
        seeded=frozenset({"probe"}),
        spec=spec,
        item_type="task",
        addr=1,
    )


def _line_index_after_tag(out: str) -> int:
    """The 0-based count of prose lines from ``_LINES`` that precede the tag."""
    lines = out.splitlines()
    tag_at = lines.index(_TAG)
    prose_before = [ln for ln in lines[:tag_at] if ln]
    return len(prose_before)


# --------------------------------------------------------------------- pattern shape x position

# Each entry: (pattern, expected count of _LINES preceding the tag). Body has a trailing
# newline throughout this table — the no-trailing-newline last-line case is its own test below,
# since it is the one shape a subset of these patterns cannot even match.
_SHAPES = [
    pytest.param(r"^## Scope\n", 1, id="ends_in_literal_newline-first_line"),
    pytest.param(r"^## Scope$", 1, id="ends_in_dollar-first_line"),
    pytest.param(r"^## Sco", 1, id="ends_mid_line-first_line"),
    pytest.param(r"^## Details\n", 3, id="ends_in_literal_newline-middle_line"),
    pytest.param(r"^## Details$", 3, id="ends_in_dollar-middle_line"),
    pytest.param(r"^## Det", 3, id="ends_mid_line-middle_line"),
    pytest.param(r"^## Scope\nSome scope prose\.\n", 2, id="spans_multiple_lines"),
    pytest.param(r"(?=## Details)", 3, id="empty_match-anchors_forward_on_its_own_line"),
]


@pytest.mark.parametrize(("pattern", "expected_lines_before"), _SHAPES)
def test_after_pattern_lands_right_after_the_matched_line(
    pattern: str, expected_lines_before: int
) -> None:
    out = _place(pattern, _body(trailing_newline=True))
    assert _line_index_after_tag(out) == expected_lines_before


def test_newline_ending_and_dollar_ending_patterns_agree_on_the_first_line() -> None:
    a = _place(r"^## Scope\n", _body(trailing_newline=True))
    b = _place(r"^## Scope$", _body(trailing_newline=True))
    assert a == b


def test_newline_ending_and_dollar_ending_patterns_agree_on_a_middle_line() -> None:
    a = _place(r"^## Details\n", _body(trailing_newline=True))
    b = _place(r"^## Details$", _body(trailing_newline=True))
    assert a == b


# ------------------------------------------------------------------------- last line, both edges


def test_after_pattern_matching_the_last_line_with_a_trailing_newline_lands_at_the_end() -> None:
    out = _place(r"^## End\n", _body(trailing_newline=True))
    assert _line_index_after_tag(out) == len(_LINES)
    assert out.rstrip("\n").endswith(_TAG)


def test_after_pattern_matching_the_last_line_with_no_trailing_newline_lands_at_the_end() -> None:
    """With no trailing newline, only a ``$``-anchored pattern can match the last line at all."""
    out = _place(r"^## End$", _body(trailing_newline=False))
    assert _line_index_after_tag(out) == len(_LINES)
    assert out.rstrip("\n").endswith(_TAG)


def test_a_literal_newline_ending_pattern_falls_back_to_bottom_with_no_trailing_newline() -> None:
    """No match falls back to bottom, same as any other non-matching pattern."""
    out = _place(r"^## End\n", _body(trailing_newline=False))
    assert _line_index_after_tag(out) == len(_LINES)


# ------------------------------------------------------------------------------------- idempotence


@pytest.mark.parametrize(("pattern", "_expected"), _SHAPES)
def test_a_second_identical_write_produces_identical_bytes(pattern: str, _expected: int) -> None:
    """A second identical write produces identical bytes, for every pattern shape in the table."""
    once = _place(pattern, _body(trailing_newline=True))
    spec = bundled_spec().model_copy(
        update={
            "views": {
                "probe": ViewSpec(source=ViewSource(kind="self"), position=f"after({pattern})")
            }
        }
    )
    twice = place_view_tags(
        once,
        None,
        seeded=frozenset({"probe"}),
        spec=spec,
        item_type="task",
        addr=1,
    )
    assert twice == once


# ------------------------------------------------------------------------------- sanity on regex


def test_the_probe_patterns_actually_compile_and_match_what_the_table_assumes() -> None:
    """Every literal-newline/dollar pattern pair in the table matches the same substring."""
    body = _body(trailing_newline=True)
    for nl_pattern, dollar_pattern in (
        (r"^## Scope\n", r"^## Scope$"),
        (r"^## Details\n", r"^## Details$"),
    ):
        m_nl = re.search(nl_pattern, body, re.MULTILINE)
        m_dollar = re.search(dollar_pattern, body, re.MULTILINE)
        assert m_nl is not None
        assert m_dollar is not None
        assert m_nl.end() - 1 == m_dollar.end()
