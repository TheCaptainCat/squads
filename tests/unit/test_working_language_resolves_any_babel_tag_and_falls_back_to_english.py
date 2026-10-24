"""``working_language`` is a language tag Babel recognises, shown as written; anything else,
including a non-string TOML value, resolves to English with a problem. The config model writes
the key only when set."""

from datetime import date, datetime, time

import pytest

from squads._language import WorkingLanguage, resolve_working_language
from squads._models._config import SquadsConfig

ENGLISH = WorkingLanguage("en", "English")

VALID = [
    (None, ENGLISH),
    ("en", ENGLISH),
    ("fr", WorkingLanguage("fr", "French")),
    ("pt-br", WorkingLanguage("pt-br", "Portuguese (Brazil)")),
    ("sr-Latn", WorkingLanguage("sr-Latn", "Serbian (Latin)")),
    ("zh-Hant-TW", WorkingLanguage("zh-Hant-TW", "Chinese (Traditional, Taiwan)")),
]
# (value as read, how the problem shows it). Underscore form, private-use extension, empty,
# whitespace, unknown codes, aliases and the two non-languages Babel would expand or accept
# (`und`, `root`), then values that are not strings, TOML dates and times among them.
MALFORMED: list[tuple[object, str]] = [
    ("fr_FR", '"fr_FR"'),
    ("en-US-x-foo", '"en-US-x-foo"'),
    ("", '""'),
    ("  ", '"  "'),
    ("xx", '"xx"'),
    ("tlh", '"tlh"'),
    ("français", '"français"'),
    ("und", '"und"'),
    ("root", '"root"'),
    ("iw", '"iw"'),
    ("fra", '"fra"'),
    (5, "5"),
    (True, "true"),
    (["fr"], '["fr"]'),
    (date(1979, 5, 27), "1979-05-27"),
    (time(7, 32), "07:32:00"),
    (datetime(1979, 5, 27, 7, 32), "1979-05-27 07:32:00"),
]


@pytest.mark.parametrize(("raw", "expected"), VALID)
def test_a_known_tag_resolves_as_written_with_its_english_name(
    raw: str | None, expected: WorkingLanguage
) -> None:
    assert resolve_working_language(raw) == (expected, None)


@pytest.mark.parametrize(("raw", "shown"), MALFORMED)
def test_an_unrecognised_value_resolves_to_english_and_shows_itself_as_written(
    raw: object, shown: str
) -> None:
    language, problem = resolve_working_language(raw)

    assert language == ENGLISH
    assert problem is not None
    assert f"working_language {shown} in" in problem
    assert "not a language tag squads recognises" in problem
    assert "English" in problem


def test_the_key_is_written_only_when_it_is_a_string() -> None:
    assert "working_language" not in SquadsConfig().to_toml()
    assert 'working_language = "pt-BR"' in SquadsConfig(working_language="pt-BR").to_toml()


def test_a_non_string_value_loads_as_read() -> None:
    assert SquadsConfig.from_toml_dict({"working_language": 5}).working_language == 5
