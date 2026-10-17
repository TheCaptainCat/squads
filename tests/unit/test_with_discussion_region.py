"""``with_discussion_region`` appends an empty top-level discussion region after the body region
and changes nothing else: it keeps the file's line endings, leaves a file that has the region as
it is, and leaves a file without a body region as it is.
"""

import pytest

from squads._sections import with_discussion_region

BODY = "<!-- sq:body -->\nprose\n<!-- sq:body:end -->"
REGION = "\n## Discussion\n\n<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n"

CASES = {
    "newline-terminated": (BODY + "\n", BODY + "\n" + REGION),
    "no-final-newline": (BODY, BODY + "\n" + REGION),
    "frontmatter-first": (
        "---\nid: X\n---\n" + BODY + "\n",
        "---\nid: X\n---\n" + BODY + "\n" + REGION,
    ),
    "crlf": (
        BODY.replace("\n", "\r\n") + "\r\n",
        BODY.replace("\n", "\r\n") + "\r\n" + REGION.replace("\n", "\r\n"),
    ),
    "crlf-without-final-newline": (
        BODY.replace("\n", "\r\n"),
        BODY.replace("\n", "\r\n") + "\r\n" + REGION.replace("\n", "\r\n"),
    ),
    "text-after-the-body": (BODY + "\ntail\n", BODY + "\n" + REGION + "tail\n"),
    "already-present": (BODY + "\n" + REGION, BODY + "\n" + REGION),
    "already-present-with-a-comment": (
        BODY + "\n\n<!-- sq:discussion -->\n- c\n<!-- sq:discussion:end -->\n",
        BODY + "\n\n<!-- sq:discussion -->\n- c\n<!-- sq:discussion:end -->\n",
    ),
    "no-body-region": ("just text\n", "just text\n"),
}


@pytest.mark.parametrize("name", list(CASES))
def test_the_region_is_appended_once_in_the_files_line_endings(name) -> None:
    text, expected = CASES[name]
    once = with_discussion_region(text)
    assert once == expected
    assert with_discussion_region(once) == once
