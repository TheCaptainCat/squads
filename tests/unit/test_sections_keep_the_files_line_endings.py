"""Section edits keep the file's own line terminator: a replace of a section's own content is an
identity, and a padded or appended snippet is written with the terminator the section uses."""

import pytest

from squads import _sections as sections
from squads._models import _markers as markers

TAG = markers.DISCUSSION
EOLS = {"lf": "\n", "crlf": "\r\n", "cr": "\r"}


def _doc(eol: str, inner: str = "a\nb\n") -> str:
    inner = inner.replace("\n", eol)
    return eol.join(
        ["intro", f"{markers.open_marker(TAG)}{eol}{inner}{markers.close_marker(TAG)}", "outro"]
    )


@pytest.mark.parametrize("eol", EOLS.values(), ids=EOLS.keys())
@pytest.mark.parametrize("inner", ["a\nb\n", "", "x\n\ny\n"], ids=["lines", "empty", "blank"])
def test_replacing_a_section_with_its_own_content_is_an_identity(eol: str, inner: str) -> None:
    doc = _doc(eol, inner) if inner else _doc(eol, "")
    got = sections.get_section(doc, TAG)
    assert got is not None

    assert sections.replace_section(doc, TAG, got) == doc


@pytest.mark.parametrize("eol", EOLS.values(), ids=EOLS.keys())
def test_new_content_is_padded_with_the_sections_terminator(eol: str) -> None:
    out = sections.replace_section(_doc(eol), TAG, "- x")

    assert sections.get_section(out, TAG) == f"{eol}- x{eol}"


@pytest.mark.parametrize("eol", EOLS.values(), ids=EOLS.keys())
def test_an_emptied_section_holds_one_terminator(eol: str) -> None:
    out = sections.replace_section(_doc(eol), TAG, "")

    assert sections.get_section(out, TAG) == eol


@pytest.mark.parametrize("eol", EOLS.values(), ids=EOLS.keys())
def test_an_appended_snippet_is_written_with_the_sections_terminator(eol: str) -> None:
    out = sections.append_to_section(_doc(eol), TAG, "- x\n  - y")

    assert sections.get_section(out, TAG) == f"{eol}a{eol}b{eol}- x{eol}  - y{eol}"
    assert out.count("\n") == _doc(eol).count("\n") + (0 if eol == "\r" else 2)


def test_an_appended_snippet_already_in_crlf_is_not_doubled() -> None:
    out = sections.append_to_section(_doc("\r\n"), TAG, "- x\r\n  - y")

    assert "\r\r" not in out


@pytest.mark.parametrize("sep", [chr(0x2028), "\x0c", "\x0b", "\x85"])
def test_a_line_separator_inside_a_line_does_not_shift_region_line_numbers(sep: str) -> None:
    doc = f"intro{sep}more\n{markers.open_marker(TAG)}\nx\n{markers.close_marker(TAG)}\n"

    assert sections.region_lines(doc, TAG) == (2, 4)
    assert len(sections.split_lines(doc)) == 4
