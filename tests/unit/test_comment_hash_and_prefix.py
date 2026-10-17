"""A comment's derived hash: what it covers and ignores, the canonical text it reads, the short
form per scope, and how a prefix resolves within one scope."""

import hashlib
from typing import Any

import pytest

from squads import _discussion as discussion
from squads._errors import SquadsError

TS = "2026-06-07T10:00:00Z"
HEADER = f"- [{TS}] `architect` Robert Architect:"


def _hash_of(region: str, *, sequence_id: int = 5, scope: str = "") -> str:
    (comment,) = discussion.split_discussion(region, sequence_id=sequence_id, scope=scope)
    return comment.hash


def _expected(text: str, *, seq: int = 5, scope: str = "", slug: str = "architect") -> str:
    payload = "\0".join(("sq-comment-1", str(seq), scope, slug, TS, text))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# (region as stored, canonical text the hash must cover)
CANONICAL_ROWS = [
    pytest.param(f"{HEADER}\n  - a\n  - b\n", "  - a\n  - b", id="lf"),
    pytest.param(f"{HEADER}\r\n  - a\r\n  - b\r\n", "  - a\n  - b", id="crlf"),
    pytest.param(f"{HEADER}\r  - a\r  - b\r", "  - a\n  - b", id="lone-cr"),
    pytest.param(f"{HEADER}\n  - a \t\n  - b  \n", "  - a\n  - b", id="trailing-spaces-and-tabs"),
    pytest.param(f"{HEADER}\n\n\n  - a\n  - b\n\n\n", "  - a\n  - b", id="outer-blank-lines"),
    pytest.param(f"{HEADER}\n  \t\n  - a\n   \n", "  - a", id="outer-blank-lines-with-spaces"),
    pytest.param(
        f"{HEADER}\n  - ```\n\n    x\n\n    ```\n", "  - ```\n\n    x\n\n    ```", id="inner-blank"
    ),
    pytest.param(f"{HEADER}\n  - a\0b\n", "  - a\0b", id="nul-in-text"),
    pytest.param(f"{HEADER}\n  - é\n", "  - é", id="no-unicode-normalisation"),
    pytest.param(f"{HEADER}\n", "", id="no-bullet-lines"),
    pytest.param(HEADER, "", id="header-only-no-newline"),
]


@pytest.mark.parametrize(("region", "text"), CANONICAL_ROWS)
def test_the_hash_covers_the_canonical_text(region: str, text: str) -> None:
    assert _hash_of(region) == _expected(text)


@pytest.mark.parametrize(
    ("a", "b"),
    [
        pytest.param("  - a\n\n  - b", "  - a\n  - b", id="inner-blank-line-counts"),
        pytest.param("  - a", "- a", id="bullet-indent-counts"),
        pytest.param("  - a\n    b", "  - a\n  b", id="continuation-indent-counts"),
        pytest.param("  - é", "  - é", id="decomposed-accent-differs"),
    ],
)
def test_a_byte_beyond_the_canonical_rules_changes_the_hash(a: str, b: str) -> None:
    assert _hash_of(f"{HEADER}\n{a}\n") != _hash_of(f"{HEADER}\n{b}\n")


def test_the_hash_matches_a_pinned_vector() -> None:
    region = f"{HEADER}\n  - first\n  - second\n"

    assert _hash_of(region) == "c5a299e6ddf214c97589830b300978cfb363307c3c21844b5deb7abaef663cc7"
    (nested,) = discussion.split_discussion(
        "- [2026-10-15T10:00:00Z] `qa` Mara Tester:\n  - Fixed in a1b2c3d.\n",
        sequence_id=12,
        scope="subtask:ST2",
    )
    assert nested.hash == "3bb8a4c26bf3299a93447943baaacc2f3b9c49707244ac51aa911b5222bd43f8"


@pytest.mark.parametrize(
    ("field", "region", "kwargs"),
    [
        pytest.param("sequence", f"{HEADER}\n  - a\n", {"sequence_id": 6}, id="sequence-number"),
        pytest.param("scope", f"{HEADER}\n  - a\n", {"scope": "subtask:ST1"}, id="scope"),
        pytest.param("slug", HEADER.replace("`architect`", "`qa`") + "\n  - a\n", {}, id="slug"),
        pytest.param(
            "timestamp", HEADER.replace("10:00:00", "10:00:01") + "\n  - a\n", {}, id="timestamp"
        ),
        pytest.param("text", f"{HEADER}\n  - b\n", {}, id="text"),
    ],
)
def test_each_hash_input_changes_the_hash(field: str, region: str, kwargs: dict[str, Any]) -> None:
    assert _hash_of(region, **kwargs) != _hash_of(f"{HEADER}\n  - a\n"), field


@pytest.mark.parametrize(
    "header",
    [
        pytest.param(HEADER.replace("Robert Architect", "Someone Else"), id="display-name"),
        pytest.param(
            f"- [{TS}, edited 2026-06-08T09:00:00Z] `architect` Robert Architect:", id="edit-mark"
        ),
    ],
)
def test_the_name_and_the_edit_mark_are_not_hash_inputs(header: str) -> None:
    assert _hash_of(f"{header}\n  - a\n") == _hash_of(f"{HEADER}\n  - a\n")


def test_every_comment_of_a_region_gets_its_own_hash_and_line_span() -> None:
    region = f"preamble\n{HEADER}\n  - a\n\n{HEADER}\n  - b\n"

    first, second = discussion.split_discussion(region, sequence_id=5)

    assert first.hash != second.hash
    assert (first.span, second.span) == ((1, 4), (4, 6))


# ------------------------------------------------------------------ short form


def _fake(*hashes: str) -> list[discussion.Comment]:
    return [discussion.Comment(TS, "A", "a", "- x", hash=h) for h in hashes]


@pytest.mark.parametrize(
    ("hashes", "shown"),
    [
        pytest.param(["a" * 64], ["a" * 7], id="one"),
        pytest.param(["a" * 64, "b" * 64], ["a" * 7, "b" * 7], id="distinct-at-seven"),
        pytest.param(
            ["abcdefg1" + "0" * 56, "abcdefg2" + "0" * 56],
            ["abcdefg1", "abcdefg2"],
            id="seven-collide-widen-both",
        ),
        pytest.param(
            ["abcdefg1" + "0" * 56, "abcdefg2" + "0" * 56, "b" * 64],
            ["abcdefg1", "abcdefg2", "bbbbbbbb"],
            id="widening-applies-to-every-hash-in-the-scope",
        ),
        pytest.param(["a" * 64, "a" * 64], ["a" * 7, "a" * 7], id="duplicate-group-is-one-hash"),
    ],
)
def test_the_short_form_widens_across_the_scope_until_its_hashes_differ(
    hashes: list[str], shown: list[str]
) -> None:
    assert discussion.short_hashes(_fake(*hashes)) == shown


# ------------------------------------------------------------------ prefix resolution

H1 = "a1b2c3d4" + "0" * 56
H2 = "a1b2ffff" + "0" * 56
H3 = "9f8e7d6c" + "1" * 56
SCOPE = _fake(H1, H2, H3)
WHERE = "TASK-5's discussion"


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        pytest.param("9f8e", [H3], id="unique-four"),
        pytest.param("9F8E7D6", [H3], id="upper-case"),
        pytest.param(H3, [H3], id="full-hash"),
        pytest.param("a1b2c", [H1], id="unique-five"),
    ],
)
def test_a_unique_prefix_resolves_to_its_comment(token: str, expected: list[str]) -> None:
    assert [c.hash for c in discussion.resolve_hash(SCOPE, token, where=WHERE)] == expected


def test_a_duplicate_group_is_one_hash_and_resolves_whole() -> None:
    twice = _fake(H1, H1, H3)

    assert len(discussion.resolve_hash(twice, "a1b2", where=WHERE)) == 2


@pytest.mark.parametrize(
    ("token", "message"),
    [
        pytest.param("a1b2", "is ambiguous in TASK-5's discussion", id="ambiguous"),
        pytest.param("a1b", "not a comment hash", id="too-short"),
        pytest.param("a1b2zz", "not a comment hash", id="non-hex"),
        pytest.param("some text", "-m or --file", id="prose"),
        pytest.param("", "not a comment hash", id="empty"),
        pytest.param("deadbeef", "no comment deadbeef in TASK-5's discussion", id="unknown"),
    ],
)
def test_a_prefix_that_cannot_address_one_comment_is_refused(token: str, message: str) -> None:
    with pytest.raises(SquadsError, match=message):
        discussion.resolve_hash(SCOPE, token, where=WHERE)


def test_an_ambiguous_prefix_lists_each_candidate() -> None:
    with pytest.raises(SquadsError) as exc:
        discussion.resolve_hash(SCOPE, "a1b2", where=WHERE)

    assert "a1b2c3d (a, " + TS + ")" in str(exc.value)
    assert "a1b2fff (a, " + TS + ")" in str(exc.value)


def test_an_unknown_hash_asks_whether_it_was_edited_or_removed() -> None:
    with pytest.raises(SquadsError, match=r"edited or removed since it was read\?"):
        discussion.resolve_hash(SCOPE, "deadbeef", where=WHERE)


def test_a_hash_found_only_in_another_scope_is_refused_naming_its_address() -> None:
    other = discussion.OtherScope("subtask ST2", "sq task 5 subtask 2 comment", _fake(H3))

    with pytest.raises(SquadsError) as exc:
        discussion.resolve_hash(_fake(H1), "9f8e7d6", where=WHERE, elsewhere=[other])

    assert "it is in subtask ST2 (sq task 5 subtask 2 comment 9f8e7d6 ...)" in str(exc.value)


def test_a_scope_never_resolves_a_hash_of_another_scope() -> None:
    other = discussion.OtherScope("subtask ST2", "sq task 5 subtask 2 comment", _fake(H3))

    with pytest.raises(SquadsError):
        discussion.resolve_hash(_fake(H1), "9f8e", where=WHERE, elsewhere=[other])
