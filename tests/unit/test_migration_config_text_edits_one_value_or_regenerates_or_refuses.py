"""The ``.squads.toml`` text a migration writes: one verified ``schema_version`` value edit with
every other byte kept, a regeneration when the file carries retired keys, or a refusal that names
the file and a line, before anything is written."""

import tomllib

import pytest

from squads._errors import SquadsError
from squads._migrations._config_text import plan_config_rewrite
from squads._models._config import SquadsConfig

NAME = ".squads.toml"
BODY = 'squad_dir = "squads"\nactive_backends = ["claude_code"]\n'


def _edit(line: str, tail: str = "") -> tuple[str, str]:
    """A file whose schema line is *line* and what it reads as after the edit to ``0.2``."""
    return f"# mine\n{line}\n{BODY}{tail}", f"# mine\n{line.replace('0.1', '0.2')}\n{BODY}{tail}"


EDITS = {
    "plain": _edit('schema_version = "0.1"'),
    "trailing-comment": _edit('schema_version = "0.1"  # stamp'),
    "spacing": _edit('  schema_version   =   "0.1"'),
    "quoted-key": _edit('"schema_version" = "0.1"'),
    "single-quoted-value": _edit("schema_version = '0.1'"),
    "stale-version-kept": _edit('schema_version = "0.1"', 'squads_version = "0.0.1"\n'),
    "multi-line-value-kept": _edit(
        'schema_version = "0.1"', 'working_language = """\nfr"""\nnote = [\n  "a", # b\n]\n'
    ),
    "table-line-in-a-string-after": _edit(
        'schema_version = "0.1"', 'note = """\n[x]\nschema_version = "0.1"\n"""\n'
    ),
    "no-final-newline": (
        f'schema_version = "0.1"\n{BODY}'.rstrip("\n"),
        f'schema_version = "0.2"\n{BODY}'.rstrip("\n"),
    ),
    "line-after-a-nested-array": (
        f'note = [\n  [1, 2]\n]\nschema_version = "0.1"\n{BODY}',
        f'note = [\n  [1, 2]\n]\nschema_version = "0.2"\n{BODY}',
    ),
    "nan-elsewhere": _edit('schema_version = "0.1"', "x = nan\n"),
    "table-like-string-line-before": (
        f'note = """\n[x]\n"""\nschema_version = "0.1"\n{BODY}',
        f'note = """\n[x]\n"""\nschema_version = "0.2"\n{BODY}',
    ),
    "a-second-candidate-in-a-string": (
        f'note = """\nschema_version = "0.1"\n"""\nschema_version = "0.1"\n{BODY}',
        f'note = """\nschema_version = "0.1"\n"""\nschema_version = "0.2"\n{BODY}',
    ),
    "tables-kept": _edit('schema_version = "0.1"', "\n[display]\npronouns = false\n# c\n"),
}


@pytest.mark.parametrize(("original", "expected"), EDITS.values(), ids=EDITS.keys())
def test_the_schema_line_is_the_only_change(original: str, expected: str) -> None:
    rewrite = plan_config_rewrite(original, "0.2", NAME)

    assert rewrite.text == expected
    assert rewrite.dropped == ()


REFUSED = {
    "multi-line-string": 'schema_version = """0.1"""\n' + BODY,
    "escaped-string": 'schema_version = "0.\\u0031"\n' + BODY,
    "only-inside-a-table": BODY + '[t]\nschema_version = "0.1"\n',
    "unparseable": 'schema_version = "0.1\n' + BODY,
}


@pytest.mark.parametrize("original", REFUSED.values(), ids=REFUSED.keys())
def test_a_file_the_edit_cannot_verify_is_refused_with_the_file_named(original: str) -> None:
    with pytest.raises(SquadsError, match=r"\.squads\.toml"):
        plan_config_rewrite(original, "0.2", NAME)


def test_a_refusal_names_the_line_to_fix() -> None:
    with pytest.raises(SquadsError, match=r"candidate lines: 2"):
        plan_config_rewrite('# c\nschema_version = """0.1"""\n' + BODY, "0.2", NAME)


LEGACY = {
    "trailing-comment": 'schema_version = "0.1"\ndefault_backend = "agents_md"  # legacy\n',
    "multi-line-role": (
        'schema_version = "0.1"\ndefault_role = """\nmanager"""\ndefault_backend = "agents_md"\n'
    ),
    "quoted-key": 'schema_version = "0.1"\n"default_backend" = "agents_md"\n',
    "dotted-slug": (
        'schema_version = "0.1"\ndefault_backend = "agents_md"\n[init.names]\n"a.b" = "X"\n'
    ),
    "slug-with-a-space": (
        'schema_version = "0.1"\ndefault_backend = "agents_md"\n[init.names]\n"my role" = "X"\n'
    ),
    "both-keys-and-comments": '# mine\nschema_version = "0.1"\ndefault_role = "m"\n'
    'default_backend = "agents_md"\nsquads_version = "0.0.1"\n',
}


@pytest.mark.parametrize("original", LEGACY.values(), ids=LEGACY.keys())
def test_retired_keys_regenerate_a_file_that_reads_back_the_same(original: str) -> None:
    expected = SquadsConfig.from_toml_dict(tomllib.loads(original))

    rewrite = plan_config_rewrite(original, "0.2", NAME)

    table = tomllib.loads(rewrite.text)
    assert table["schema_version"] == "0.2"
    assert table["active_backends"] == ["agents_md"]
    assert "default_backend" not in table
    assert SquadsConfig.from_toml_dict(table).model_dump() == {
        **expected.model_dump(),
        "schema_version": "0.2",
    }


def test_a_regeneration_keeps_names_display_and_working_language() -> None:
    original = (
        'schema_version = "0.1"\ndefault_backend = "agents_md"\nworking_language = "fr"\n'
        '[display]\npronouns = false\n[init.names]\nmanager = "Cat"\n'
    )

    table = tomllib.loads(plan_config_rewrite(original, "0.2", NAME).text)

    assert table["working_language"] == "fr"
    assert table["display"] == {"pronouns": False}
    assert table["init"] == {"names": {"manager": "Cat"}}


def test_a_regeneration_reports_the_keys_it_leaves_out() -> None:
    original = (
        'schema_version = "0.1"\ndefault_role = "m"\nextra = 1\nlocale = "it"\n'
        '[init]\nother = 2\n[init.names]\nmanager = "Cat"\n[tbl]\nx = 1\n'
    )

    rewrite = plan_config_rewrite(original, "0.2", NAME)

    assert rewrite.dropped == ("extra", "locale", "tbl", "init.other")


UNREPORTED = {
    "unusable-display-entries": (
        '[display]\npronouns = "false"\nfoo = 1\n',
        ("display.pronouns", "display.foo"),
    ),
    "display-not-a-table": ("display = 3\n", ("display",)),
    "init-names-not-a-table": ("[init]\nnames = 5\n", ("init.names",)),
}


@pytest.mark.parametrize(("tail", "dropped"), UNREPORTED.values(), ids=UNREPORTED.keys())
def test_a_regeneration_reports_the_unusable_display_and_init_entries_it_drops(
    tail: str, dropped: tuple[str, ...]
) -> None:
    original = 'default_backend = "agents_md"\nschema_version = "0.1"\n' + tail

    assert plan_config_rewrite(original, "0.2", NAME).dropped == dropped


UNHOLDABLE = {
    "non-string-working-language": 'default_role = "m"\nworking_language = 5\n',
    "non-string-init-name": 'default_role = "m"\n[init.names]\na = 5\n',
}


@pytest.mark.parametrize("original", UNHOLDABLE.values(), ids=UNHOLDABLE.keys())
def test_a_regeneration_that_cannot_hold_a_setting_is_refused(original: str) -> None:
    with pytest.raises(SquadsError, match="legacy keys"):
        plan_config_rewrite(original, "0.2", NAME)
