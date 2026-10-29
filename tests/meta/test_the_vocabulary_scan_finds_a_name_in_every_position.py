"""Repo gate: the scan behind the vocabulary guards sees a bundled name wherever the source can
spell it, and stays silent on what is not a reference to the vocabulary."""

from pathlib import Path

import pytest

from squads._workflow import bundled_spec
from tests.meta import _vocabulary as vocabulary

_CATEGORIES = (
    vocabulary.REF,
    vocabulary.STATUS,
    vocabulary.KIND,
    vocabulary.TYPE,
    vocabulary.FIELD,
)


def _a_name(category: str) -> str:
    """A multi-character name of *category* the bundled spec declares and the engine does not."""
    names = vocabulary.vocabulary(bundled_spec(), category)
    return next(n for n in sorted(names) if len(n) > 1 and n not in vocabulary.engine_words())


def _plant(root: Path, relative: str, text: str) -> None:
    path = root / "src" / "squads" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _found(root: Path, category: str) -> list[str]:
    return [hit.name for hit in vocabulary.tree_hits(root, bundled_spec(), category)]


@pytest.mark.parametrize("category", _CATEGORIES)
def test_a_planted_name_is_found_in_every_position(tmp_path: Path, category: str) -> None:
    name = _a_name(category)
    positions = {
        "a bare string": ("_a.py", f'KIND = "{name}"\n'),
        "a flag": ("_b.py", f'FLAG = "--{name}"\n'),
        "a verb": ("_c.py", f'VERB = "add-{name}"\n'),
        "a code span of a string": ("_d.py", f'HELP = "Run `sq {name} show`."\n'),
        "a code span split by an f-string": ("_e.py", f'HELP = f"Run `{{x}}` or `{name}`."\n'),
        "a command line": ("_f.py", f'HELP = "sq create {name}"\n'),
        "a quoted template literal": ("t.md.j2", f"{{{{ label('{name}') }}}}\n"),
        "a template code span": ("u.md.j2", f"Run `sq {name} show`.\n"),
    }
    for where, (relative, text) in positions.items():
        planted = tmp_path / where.replace(" ", "-")
        _plant(planted, relative, text)
        assert name in _found(planted, category), f"{name!r} not found as {where}"


@pytest.mark.parametrize("directory", sorted(vocabulary.SPEC_LAYER_DIRS))
def test_the_scan_stops_at_the_spec_layer(tmp_path: Path, directory: str) -> None:
    name = _a_name(vocabulary.TYPE)
    _plant(tmp_path, f"{directory}/_a.py", f'KIND = "{name}"\n')

    assert _found(tmp_path, vocabulary.TYPE) == []


def test_the_scan_reads_prose_and_comments_as_prose(tmp_path: Path) -> None:
    name = _a_name(vocabulary.TYPE)
    _plant(
        tmp_path,
        "_a.py",
        f'"""A {name} is named here."""\n# a {name} in a comment\nTEXT = "a {name} in prose"\n',
    )
    _plant(tmp_path, "t.md.j2", f"{{# `{name}` in a template comment #}}\nA {name} in prose.\n")

    assert _found(tmp_path, vocabulary.TYPE) == []


def test_the_scan_leaves_a_word_the_engine_defines_alone(tmp_path: Path) -> None:
    badge_codes = vocabulary.vocabulary(bundled_spec(), vocabulary.FIELD)
    spelled_like_engine = sorted(set(badge_codes) & vocabulary.engine_words())
    assert spelled_like_engine, "no bundled badge code is also an engine word"
    _plant(tmp_path, "_a.py", f'INTENT = "{spelled_like_engine[0]}"\n')

    assert _found(tmp_path, vocabulary.FIELD) == []


def test_a_one_character_alias_is_read_only_after_the_command_name(tmp_path: Path) -> None:
    names = vocabulary.vocabulary(bundled_spec(), vocabulary.TYPE)
    alias = next(n for n in sorted(names) if len(n) == 1)
    _plant(tmp_path, "_a.py", f'MODE = "{alias}"\nHELP = "Open it with `-{alias}`."\n')
    assert _found(tmp_path, vocabulary.TYPE) == []

    _plant(tmp_path, "_b.py", f'HELP = "Run `sq {alias} 7 show`."\n')
    assert _found(tmp_path, vocabulary.TYPE) == [alias]
