"""The comment-header grammar: what ``format_comment`` writes for each author shape, and which
column-0 lines the one shared pattern reads back as a header (and which it must not)."""

import pytest

from squads import _discussion as discussion
from squads._errors import SquadsError

TS = "2026-06-07T10:00:00Z"

# (slug, name given to the writer, header line written, name read back)
WRITE_ROWS = [
    pytest.param("architect", "Robert Architect", "Robert Architect", id="bundled-role"),
    pytest.param("python-dev", "Elias Python", "Elias Python", id="developer-role"),
    pytest.param("op-pierre", "Pierre Chat", "Pierre Chat", id="operator"),
    pytest.param("operator", "Operator", "Operator", id="anonymous-sentinel"),
    pytest.param("squads", "squads", "squads", id="system-entry"),
    pytest.param("qa", "Mara: the Tester", "Mara: the Tester", id="colon-in-name"),
    pytest.param("qa", "Mara `QA` Tester", "Mara `QA` Tester", id="backtick-in-name"),
    pytest.param("qa", "Zoë Müller", "Zoë Müller", id="accents"),
    pytest.param("qa", "Mara: ", "Mara:", id="trailing-colon-then-space"),
    pytest.param("qa", "Name ends:", "Name ends:", id="name-ending-in-a-colon"),
    pytest.param("qa", "Mara\nTester", "Mara Tester", id="line-break-collapses"),
    pytest.param(
        "qa", f"Mara{chr(0x2028)}Tester", "Mara Tester", id="unicode-line-break-collapses"
    ),
    pytest.param("qa", "", "qa", id="empty-name-falls-back-to-the-slug"),
    pytest.param("qa", " \n ", "qa", id="blank-name-falls-back-to-the-slug"),
    pytest.param("a1-b2", "Edge", "Edge", id="digits-and-hyphen-in-slug"),
]


@pytest.mark.parametrize(("slug", "given", "shown"), WRITE_ROWS)
def test_a_written_header_reads_back_as_the_same_timestamp_slug_and_name(
    slug: str, given: str, shown: str
) -> None:
    out = discussion.format_comment(TS, slug, given, ["first", "second"])

    assert out.splitlines()[0] == f"- [{TS}] `{slug}` {shown}:"
    assert discussion.match_comment_header(out.splitlines()[0]) == (TS, slug, shown)
    (comment,) = discussion.split_discussion(out)
    assert (comment.timestamp, comment.author_slug, comment.author) == (TS, slug, shown)
    assert comment.body == "- first\n- second"


@pytest.mark.parametrize(
    "line",
    [
        pytest.param("  - [2026-06-07T10:00:00Z] `qa` Mara:", id="indented"),
        pytest.param("- [x] Done:", id="checkbox"),
        pytest.param("  - [x] Done:", id="indented-checkbox"),
        pytest.param("- [2026-06-07T10:00:00Z] `qa` Mara", id="no-closing-colon"),
        pytest.param("- [2026-06-07T10:00:00Z] Mara Tester:", id="legacy-header"),
        pytest.param("- [2026-06-07T10:00:00Z] `QA` Mara:", id="uppercase-slug"),
        pytest.param("- [2026-06-07T10:00:00Z] `qa_x` Mara:", id="underscore-slug"),
        pytest.param("- [2026-06-07T10:00:00Z] `-qa` Mara:", id="leading-hyphen-slug"),
        pytest.param("- [2026-06-07T10:00:00Z] `` Mara:", id="empty-slug"),
        pytest.param("- [2026-06-07T10:00:00] `qa` Mara:", id="timestamp-without-z"),
        pytest.param("- [2026-06-07 10:00:00Z] `qa` Mara:", id="timestamp-with-space"),
        pytest.param("- [2026-06-07T10:00:00Z] `qa`Mara:", id="no-space-after-slug"),
        pytest.param("- [2026-06-07T10:00:00Z] `qa` :", id="no-name"),
        pytest.param("* [2026-06-07T10:00:00Z] `qa` Mara:", id="other-bullet"),
    ],
)
def test_a_line_that_is_not_in_the_grammar_is_not_a_header(line: str) -> None:
    assert discussion.match_comment_header(line) is None
    assert discussion.split_discussion(line) == []


def test_an_indented_header_shaped_line_stays_inside_the_comment_body() -> None:
    region = (
        f"- [{TS}] `qa` Mara:\n"
        "  - checklist\n"
        "    - [2026-06-07T11:00:00Z] `bob` Bob:\n"
        "  - [x] Done:\n"
    )

    (comment,) = discussion.split_discussion(region)

    assert comment.author_slug == "qa"
    assert "`bob` Bob:" in comment.body
    assert "[x] Done:" in comment.body


@pytest.mark.parametrize(
    "slug", ["Bad Actor", "QA", "", "-lead", "under_score", "has`tick", "line\nbreak"]
)
def test_the_writer_refuses_a_slug_outside_the_grammar(slug: str) -> None:
    with pytest.raises(SquadsError, match="cannot write a comment as"):
        discussion.format_comment(TS, slug, "Anyone", ["x"])
