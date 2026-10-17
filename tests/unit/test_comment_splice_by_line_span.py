"""Replacing or removing comments in a discussion region by line span: every other line stays
byte-identical for each position, body shape, layout and line ending; the edit mark and the
legacy-header check."""

import itertools

import pytest

from squads import _discussion as discussion

TS = "2026-06-07T10:00:00Z"
EDIT_TS = "2026-06-08T09:00:00Z"

SHAPES = {
    "single": ["one line"],
    "multi-line": ["first\nsecond line", "another"],
    "fenced": ["Fix:\n```py\na = 1\n\nb = 2\n```"],
}


def _entry(n: int, shape: str, edited: str | None = None) -> str:
    return discussion.format_comment(
        TS, f"dev-{n}", f"Dev {n}", [f"{m} #{n}" for m in SHAPES[shape]], edited_ts=edited
    )


def _region(entries: list[str], layout: str, eol: str, preamble: str) -> str:
    """The region as the layouts we meet in files: entries separated by nothing, a blank line,
    or each followed by a blank line."""
    sep = {"compact": "", "blank-between": eol, "blank-after": eol}[layout]
    joined = (eol + sep).join(e.replace("\n", eol) for e in entries) + eol
    if layout == "blank-after":
        joined += eol
    return eol + (preamble + eol + eol if preamble else "") + joined


POSITIONS = {"first": 0, "middle": 1, "last": 2}
LAYOUTS = ["compact", "blank-between", "blank-after"]
EOLS = {"lf": "\n", "crlf": "\r\n"}
PREAMBLES = {"no-preamble": "", "preamble": "Notes before the first comment."}


def _rows():
    for pos, shape, layout, eol, pre in itertools.product(
        POSITIONS, SHAPES, LAYOUTS, EOLS, PREAMBLES
    ):
        yield pytest.param(pos, shape, layout, eol, pre, id=f"{pos}-{shape}-{layout}-{eol}-{pre}")


@pytest.mark.parametrize(("pos", "shape", "layout", "eol", "pre"), _rows())
def test_removing_a_comment_leaves_every_other_line_byte_identical(
    pos: str, shape: str, layout: str, eol: str, pre: str
) -> None:
    entries = [_entry(n, shape) for n in range(3)]
    at = POSITIONS[pos]
    region = _region(entries, layout, EOLS[eol], PREAMBLES[pre])
    survivors = [e for i, e in enumerate(entries) if i != at]
    cmts = discussion.split_discussion(region, sequence_id=1)

    out = discussion.replace_comments(region, [(cmts[at], None)])

    assert out == _region(survivors, layout, EOLS[eol], PREAMBLES[pre])


@pytest.mark.parametrize(("pos", "shape", "layout", "eol", "pre"), _rows())
def test_replacing_a_comment_leaves_every_other_line_byte_identical(
    pos: str, shape: str, layout: str, eol: str, pre: str
) -> None:
    entries = [_entry(n, shape) for n in range(3)]
    at = POSITIONS[pos]
    region = _region(entries, layout, EOLS[eol], PREAMBLES[pre])
    cmts = discussion.split_discussion(region, sequence_id=1)
    new = _entry(at, "multi-line", edited=EDIT_TS)

    out = discussion.replace_comments(region, [(cmts[at], new)])

    expected = [new if i == at else e for i, e in enumerate(entries)]
    assert out == _region(expected, layout, EOLS[eol], PREAMBLES[pre])


@pytest.mark.parametrize("pre", PREAMBLES.values(), ids=PREAMBLES.keys())
@pytest.mark.parametrize("eol", EOLS.values(), ids=EOLS.keys())
@pytest.mark.parametrize("layout", LAYOUTS)
def test_removing_the_only_comment_leaves_the_preamble_alone(
    pre: str, eol: str, layout: str
) -> None:
    region = _region([_entry(0, "single")], layout, eol, pre)
    (cmt,) = discussion.split_discussion(region, sequence_id=1)

    out = discussion.replace_comments(region, [(cmt, None)])

    assert out == eol + (pre + eol + eol if pre else "")


def test_a_region_without_a_final_newline_keeps_that_after_a_replacement() -> None:
    region = "\n" + _entry(0, "single") + "\n" + _entry(1, "single")
    cmts = discussion.split_discussion(region, sequence_id=1)

    out = discussion.replace_comments(region, [(cmts[1], _entry(1, "multi-line"))])

    assert out == "\n" + _entry(0, "single") + "\n" + _entry(1, "multi-line")


def test_a_group_is_edited_into_its_first_member_and_loses_the_rest() -> None:
    same = _entry(0, "single")
    region = "\n" + "\n".join([same, _entry(1, "single"), same]) + "\n"
    first, _, copy = discussion.split_discussion(region, sequence_id=1)
    assert first.hash == copy.hash

    new = _entry(0, "multi-line", edited=EDIT_TS)
    out = discussion.replace_comments(region, [(first, new), (copy, None)])

    assert out == "\n" + "\n".join([new, _entry(1, "single")]) + "\n"


def test_removing_a_whole_group_leaves_the_others_in_order() -> None:
    same = _entry(0, "single")
    entries = [_entry(1, "single"), same, _entry(2, "single"), same]
    region = "\n" + "\n".join(entries) + "\n"
    cmts = discussion.split_discussion(region, sequence_id=1)

    out = discussion.replace_comments(region, [(cmts[1], None), (cmts[3], None)])

    assert out == "\n" + "\n".join([entries[0], entries[2]]) + "\n"


def test_a_replacement_in_a_crlf_region_is_written_with_crlf() -> None:
    region = _region([_entry(0, "single")], "compact", "\r\n", "")
    (cmt,) = discussion.split_discussion(region, sequence_id=1)

    out = discussion.replace_comments(region, [(cmt, _entry(0, "multi-line"))])

    assert "\n" not in out.replace("\r\n", "")


# ------------------------------------------------------------------ the edit mark


def test_an_edit_mark_reads_back_and_is_never_a_hash_input() -> None:
    plain = discussion.format_comment(TS, "qa", "Mara", ["x"])
    marked = discussion.format_comment(TS, "qa", "Mara", ["x"], edited_ts=EDIT_TS)

    (a,) = discussion.split_discussion(plain, sequence_id=1)
    (b,) = discussion.split_discussion(marked, sequence_id=1)

    assert marked.splitlines()[0] == f"- [{TS}, edited {EDIT_TS}] `qa` Mara:"
    assert (a.edited_ts, b.edited_ts) == (None, EDIT_TS)
    assert (a.timestamp, b.timestamp) == (TS, TS)
    assert a.hash == b.hash
    assert discussion.match_comment_header(marked.splitlines()[0]) == (TS, "qa", "Mara")


def test_a_second_edit_replaces_the_mark_instead_of_adding_one() -> None:
    first = discussion.format_comment(TS, "qa", "Mara", ["x"], edited_ts=EDIT_TS)
    (cmt,) = discussion.split_discussion(first, sequence_id=1)
    later = "2026-06-09T12:00:00Z"

    out = discussion.replace_comments(
        first, [(cmt, discussion.format_comment(TS, "qa", "Mara", ["y"], edited_ts=later))]
    )

    (after,) = discussion.split_discussion(out, sequence_id=1)
    assert out.splitlines()[0] == f"- [{TS}, edited {later}] `qa` Mara:"
    assert out.count("edited") == 1
    assert (after.timestamp, after.edited_ts) == (TS, later)


# ------------------------------------------------------------------ legacy lines


@pytest.mark.parametrize(
    ("region", "found"),
    [
        pytest.param(f"- [{TS}] Mara Tester:\n  - old\n", [1], id="slug-less-header"),
        pytest.param(
            f"- [{TS}] `qa` Mara:\n  - x\n- [ ] stray prose\n", [3], id="prose-at-column-0"
        ),
        pytest.param(f"- [{TS}] `qa` Mara:\n  - x\n  - [ ] indented\n", [], id="indented-accepted"),
        pytest.param(f"- [{TS}] `qa` Mara:\n  - x\n    - [ ] nested\n", [], id="nested-accepted"),
        pytest.param(f"- [{TS}] `qa` Mara:\r\n  - x\r\n", [], id="well-formed-crlf"),
        pytest.param(f"- [{TS}, edited {EDIT_TS}] `qa` Mara:\n  - x\n", [], id="edit-mark-header"),
        pytest.param(f"- [{TS}, edited] `qa` Mara:\n", [1], id="malformed-edit-mark"),
        pytest.param("", [], id="empty"),
    ],
)
def test_a_column_zero_line_that_opens_like_a_header_but_is_not_one_is_found(
    region: str, found: list[int]
) -> None:
    assert [n for n, _ in discussion.legacy_header_lines(region)] == found
