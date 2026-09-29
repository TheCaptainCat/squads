"""``slugify`` maps accented Latin letters to ASCII and leaves plain ASCII input unchanged."""

import re
import unicodedata

import pytest

from squads import _util
from squads._util import legacy_slugify, operator_slug, slugify

_CASES = [
    pytest.param("Plain ASCII title", "plain-ascii-title", id="ascii-unchanged"),
    pytest.param("already-a-slug_2", "already-a-slug-2", id="ascii-punctuation"),
    pytest.param("Réduire", "reduire", id="precomposed"),
    pytest.param("Élodie", "elodie", id="leading-capital-accent"),
    pytest.param("Ça marche", "ca-marche", id="accent-at-boundary"),
    pytest.param("Ça", "ca", id="accent-only-word"),
    pytest.param(unicodedata.normalize("NFD", "Réduire"), "reduire", id="decomposed-nfd"),
    pytest.param("Straße", "strasse", id="sharp-s"),
    pytest.param("Æther", "aether", id="ae-upper"),
    pytest.param("æther", "aether", id="ae-lower"),
    pytest.param("Øresund", "oresund", id="o-slash-upper"),
    pytest.param("Œuvre", "oeuvre", id="oe-upper"),
    pytest.param("Łódź", "lodz", id="l-stroke"),
    pytest.param("Đorđe", "dorde", id="d-stroke"),
    pytest.param("Crème brûlée, à la façon!", "creme-brulee-a-la-facon", id="mixed-punctuation"),
    pytest.param("ﬁne", "fine", id="compatibility-ligature"),
    pytest.param("Þór Ðað", "thor-dad", id="thorn-and-eth"),
    pytest.param("Ħal ŧin", "hal-tin", id="h-and-t-stroke"),
    pytest.param("\u0131stanbul", "istanbul", id="dotless-i"),
    pytest.param("日本語", "untitled", id="non-latin-falls-back"),
    pytest.param("", "untitled", id="empty"),
    pytest.param("   ", "untitled", id="whitespace-only"),
]


@pytest.mark.parametrize(("text", "expected"), _CASES)
def test_slugify(text, expected):
    assert slugify(text) == expected


def test_max_len_cut_lands_after_a_multi_character_expansion():
    assert slugify("a" * 59 + "ß") == "a" * 59
    assert slugify("a" * 58 + "ß") == "a" * 58 + "ss"
    assert slugify("ß" * 40, max_len=7) == "ss" * 3
    assert slugify("ab-" + "þ", max_len=4) == "ab"
    assert slugify("a" * 70) == "a" * 60


@pytest.mark.parametrize(
    ("text", "old_output"),
    [
        pytest.param("Élodie", "lodie", id="leading-accent"),
        pytest.param("Größe prüfen", "gr-e-pr-fen", id="umlauts-and-sharp-s"),
        pytest.param("Plain ASCII", "plain-ascii", id="ascii"),
        pytest.param("日本語", "untitled", id="non-latin"),
        pytest.param("x" * 70, "x" * 60, id="long"),
    ],
)
def test_the_earlier_rule_is_pinned_to_its_old_outputs(text, old_output):
    assert legacy_slugify(text) == old_output


def test_the_earlier_rule_shares_nothing_with_the_live_one(monkeypatch):
    monkeypatch.setattr(_util, "_slug_strip", re.compile(r"[^a-z]+"))
    monkeypatch.setattr(_util, "_TRANSLITERATIONS", ())
    assert legacy_slugify("Élodie 42") == "lodie-42"


def test_operator_slug_uses_the_transliterated_first_name():
    assert operator_slug("Élodie Martin") == "op-elodie"
