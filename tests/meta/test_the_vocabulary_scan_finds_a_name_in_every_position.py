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


def _a_prefix() -> str:
    names = vocabulary.vocabulary(bundled_spec(), vocabulary.TYPE)
    return next(n for n in sorted(names) if len(n) > 1 and n.isupper())


def test_an_id_prefix_is_found_written_with_its_dash(tmp_path: Path) -> None:
    prefix = _a_prefix()
    shapes = {
        "a bare prefix with its dash": f'PREFIX = "{prefix}-"\n',
        "a startswith test": f'ok = item_id.startswith("{prefix}-")\n',
        "an f-string id": f'ID = f"{prefix}-{{n}}"\n',
        "a percent-format id": f'ID = "{prefix}-%d" % n\n',
    }
    for where, text in shapes.items():
        planted = tmp_path / where.replace(" ", "-")
        _plant(planted, "_a.py", text)
        assert prefix in _found(planted, vocabulary.TYPE), f"{prefix!r} not found as {where}"


def test_only_the_defining_assignment_of_an_engine_constant_may_spell_its_word(
    tmp_path: Path,
) -> None:
    name, word = next(iter(vocabulary.ENGINE_CONSTANTS.items()))
    defined = tmp_path / "defined"
    _plant(defined, "_a.py", f'{name} = "{word}"\n')
    spelled = tmp_path / "spelled"
    _plant(spelled, "_a.py", f'def f(t):\n    return t == "{word}"\n')

    found = {
        where: [hit.name for hit in vocabulary.tree_hits(root, bundled_spec(), *_CATEGORIES)]
        for where, root in (("defined", defined), ("spelled", spelled))
    }

    assert (word in found["defined"], word in found["spelled"]) == (False, True)


def test_a_command_docstring_is_help_text_and_any_other_docstring_is_prose(tmp_path: Path) -> None:
    prefix = _a_prefix()
    help_text = f'"""Show it.\n\n    Pass `{prefix}-<n>`.\n    """'
    _plant(
        tmp_path / "command",
        "_a.py",
        f"@app.command()\ndef show() -> None:\n    {help_text}\n",
    )
    _plant(
        tmp_path / "plain",
        "_a.py",
        f"def show() -> None:\n    {help_text}\n",
    )

    assert prefix in _found(tmp_path / "command", vocabulary.TYPE)
    assert _found(tmp_path / "plain", vocabulary.TYPE) == []


def test_a_function_registered_by_calling_command_on_it_is_a_command(tmp_path: Path) -> None:
    prefix = _a_prefix()
    help_text = f'"""Show it.\n\n    Pass `{prefix}-<n>`.\n    """'
    forms = {
        "bare": 'app.command("x")(show)',
        "wrapped": 'app.command("x")(handle_errors(show))',
        "hidden": 'app.command("x", hidden=True)(show)',
    }
    for where, registration in forms.items():
        _plant(
            tmp_path / where,
            "_a.py",
            f"def show() -> None:\n    {help_text}\n\n\n{registration}\n",
        )
        assert prefix in _found(tmp_path / where, vocabulary.TYPE), f"{where} not read as help"
