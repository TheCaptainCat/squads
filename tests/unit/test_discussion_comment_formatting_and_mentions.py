"""The ``_discussion.py`` pure-function layer's remainder: comment formatting (including a
multiline message and a fenced-code-block nesting properly under its bullet), ``@mention``
extraction, and local-id sequencing. The head/summary-rendering half of this same file is
already covered at tests/unit/test_subentity_head_and_summary_rendering.py — this is the rest.
"""

from squads import _discussion as discussion
from squads._models._subentity import SubEntity


def test_format_comment_renders_a_dated_bullet_list() -> None:
    out = discussion.format_comment("2026-06-07T10:00:00Z", "Robert Architect", ["a", "b"])
    assert out == "- [2026-06-07T10:00:00Z] Robert Architect:\n  - a\n  - b"


def test_format_comment_nests_a_multiline_message_under_its_own_bullet() -> None:
    out = discussion.format_comment(
        "2026-06-07T10:00:00Z", "Olivia Lead", ["Parser\nhandles scopes", "@qa verify"]
    )
    assert out == (
        "- [2026-06-07T10:00:00Z] Olivia Lead:\n  - Parser\n    handles scopes\n  - @qa verify"
    )


def test_format_comment_nests_a_fenced_code_block_including_its_blank_lines() -> None:
    out = discussion.format_comment(
        "2026-06-07T10:00:00Z", "Dev", ["Fix:\n```py\na = 1\n\nb = 2\n```"]
    )
    assert out == (
        "- [2026-06-07T10:00:00Z] Dev:\n  - Fix:\n    ```py\n    a = 1\n    \n    b = 2\n    ```"
    )


def test_extract_mentions_finds_at_role_tokens_and_ignores_lookalikes() -> None:
    text = "ping @qa and @reviewer, not email me@host or @ alone"
    assert discussion.extract_mentions(text) == {"qa", "reviewer"}


def _sub(local_id: str, **kw) -> SubEntity:
    return SubEntity(local_id=local_id, status=kw.pop("status", "Todo"), **kw)


def test_next_local_id_continues_the_existing_sequence_per_kind() -> None:
    assert discussion.next_local_id([], "story") == "US1"
    assert discussion.next_local_id([_sub("US1"), _sub("US2")], "story") == "US3"
    assert discussion.next_local_id([_sub("ST5")], "subtask") == "ST6"
