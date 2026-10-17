"""One shape rule decides what counts as pronouns: trimmed, one line, 1 to 40 characters, no
control character, no sq marker tag. The accessor over a stored value returns the trimmed text
when it passes and reads anything else as unset."""

from datetime import UTC, datetime
from typing import Any

import pytest

from squads._errors import SquadsError
from squads._models._attributes import AttributeKey
from squads._models._item import Item
from squads._pronouns import checked_pronouns, pronouns, pronouns_problem

_NOW = datetime(2026, 1, 1, tzinfo=UTC)

# (id, raw value, trimmed value when valid else None)
VALUE_SHAPES: list[tuple[str, str, str | None]] = [
    ("slash-pair", "they/them", "they/them"),
    ("one-character", "x", "x"),
    ("forty-characters", "a" * 40, "a" * 40),
    ("forty-one-characters", "a" * 41, None),
    ("surrounding-whitespace", "  they/them \t", "they/them"),
    ("empty", "", None),
    ("whitespace-only", " \t ", None),
    ("embedded-newline", "they/\nthem", None),
    ("embedded-carriage-return", "they/\rthem", None),
    ("embedded-tab", "they/\tthem", None),
    ("other-control-character", "they\x07them", None),
    ("unicode-line-separator", f"they{chr(0x2028)}them", None),
    ("unicode-paragraph-separator", f"they{chr(0x2029)}them", None),
    ("bidi-override", f"they{chr(0x202E)}them", None),
    ("zero-width-space", f"they{chr(0x200B)}them", None),
    ("byte-order-mark", f"they{chr(0xFEFF)}them", None),
    ("forty-decomposed-accents", "e\u0301" * 40, "e\u0301" * 40),
    ("forty-one-decomposed-accents", "e\u0301" * 41, None),
    ("marker-tag", "<!-- sq:body -->", None),
    ("marker-tag-inside-text", "x <!-- sq:discussion:end --> y", None),
    ("square-brackets", "[x]", "[x]"),
    ("non-ascii", "elle/iel", "elle/iel"),
    ("forty-after-trim", " " + "a" * 40 + " ", "a" * 40),
]


def _role(stored: Any) -> Item:
    return Item(
        sequence_id=1,
        type="role",
        title="Whoever Slug",
        slug="whoever",
        slug_in_file=True,
        status="Active",
        path="agents/roles/ROLE-000001-whoever.md",
        created_at=_NOW,
        updated_at=_NOW,
        attributes={} if stored is None else {AttributeKey.PRONOUNS: stored},
    )


@pytest.mark.parametrize(
    ("shape", "raw", "trimmed"), VALUE_SHAPES, ids=[v[0] for v in VALUE_SHAPES]
)
def test_the_rule_accepts_exactly_the_shapes_that_trim_to_a_valid_value(
    shape: str, raw: str, trimmed: str | None
) -> None:
    assert (pronouns_problem(raw) is None) is (trimmed is not None)


@pytest.mark.parametrize(
    ("shape", "raw", "trimmed"), VALUE_SHAPES, ids=[v[0] for v in VALUE_SHAPES]
)
def test_the_accessor_returns_the_trimmed_value_or_reads_a_failing_one_as_unset(
    shape: str, raw: str, trimmed: str | None
) -> None:
    assert pronouns(_role(raw)) == trimmed


@pytest.mark.parametrize(
    "stored",
    [None, ["they/them"], 5, True, {"a": "b"}],
    ids=["absent", "list", "integer", "boolean", "mapping"],
)
def test_the_accessor_reads_a_value_of_another_kind_as_unset(stored: Any) -> None:
    assert pronouns(_role(stored)) is None


@pytest.mark.parametrize(
    ("shape", "raw", "trimmed"), VALUE_SHAPES, ids=[v[0] for v in VALUE_SHAPES]
)
def test_the_storable_form_is_trimmed_blank_is_nothing_and_a_bad_value_is_refused(
    shape: str, raw: str, trimmed: str | None
) -> None:
    if not raw.strip():
        assert checked_pronouns(raw) is None
    elif trimmed is None:
        with pytest.raises(SquadsError, match=r"^pronouns "):
            checked_pronouns(raw)
    else:
        assert checked_pronouns(raw) == trimmed


def test_an_absent_value_stores_nothing() -> None:
    assert checked_pronouns(None) is None
