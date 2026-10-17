"""The generated article follows how the name is spoken, not its first letter."""

import pytest

from squads._cli._common import article


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("epic", "an"),
        ("investigation", "an"),
        ("analysis", "an"),
        ("task", "a"),
        ("review", "a"),
        ("user_story", "a"),
        ("unit", "a"),
        ("union", "a"),
        ("utility", "a"),
        ("european", "a"),
        ("umbrella", "an"),
        ("under_review", "an"),
        ("hour", "an"),
        ("honest_check", "an"),
        ("hotfix", "a"),
        ("Epic", "an"),
    ],
)
def test_the_article_follows_the_first_sound(word: str, expected: str) -> None:
    assert article(word) == expected
