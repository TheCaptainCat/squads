"""Every field of a role override is typed, and every wrong shape is refused by name.

A role is not an ``sq`` view — it is materialised into the agent hosts' own files, so a value
nothing validates writes a broken agent definition. The resolver used to assign raw TOML values
straight into a plain dataclass, and the consequences were not subtle: ``can_spawn = "false"``
is a non-empty string and therefore truthy, so a *quoting mistake granted spawn authority*;
``model = "opuss"`` was stored despite the catalog's own model whitelist; a non-string colour
reached the generated pointer verbatim; an unknown key vanished; and ``$(*self)`` was written
out as a literal token, in frontmatter and in the rendered body — the very idiom the scaffold
teaches.

So this is a table over the whole field set rather than one example per symptom. Every field of
``RoleSpec`` appears with a wrong type, because the defect was never one bad field — it was the
absence of validation, which is invisible field by field.
"""

from pathlib import Path

import pytest

from squads._errors import SquadsError
from squads._roles._models import RoleSpec
from squads._roles._resolver import resolve_dev_role, resolve_role


def _place(tmp_path: Path, slug: str, body: str) -> None:
    d = tmp_path / ".overrides" / "roles"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{slug}.toml").write_text(body, encoding="utf-8")


# --------------------------------------------------------------------- the truthiness trap


@pytest.mark.parametrize("written", ['"false"', '"no"', '"off"', '"0"'])
def test_a_quoted_false_never_grants_a_boolean_capability(tmp_path, written: str) -> None:
    """The headline case, stated as the capability rather than the type: a quoted false is the
    adopter saying no, and it must not read as yes. Untyped, every one of these was a non-empty
    string — truthy — so ``sq role architect show`` reported "can spawn: yes"."""
    _place(tmp_path, "architect", f"can_spawn = {written}\nis_default = {written}\n")

    role = resolve_role("architect", tmp_path)

    assert role.can_spawn is False
    assert role.is_default is False


@pytest.mark.parametrize("written", ['"true"', '"yes"', '"on"', '"1"'])
def test_a_quoted_true_still_means_yes(tmp_path, written: str) -> None:
    """The other half — the point is that quoting stops changing the answer, not that quoted
    values are refused."""
    _place(tmp_path, "architect", f"can_spawn = {written}\n")

    assert resolve_role("architect", tmp_path).can_spawn is True


def test_a_boolean_field_with_no_boolean_reading_is_refused(tmp_path) -> None:
    _place(tmp_path, "architect", 'can_spawn = "maybe"\n')

    with pytest.raises(SquadsError) as excinfo:
        resolve_role("architect", tmp_path)
    assert "can_spawn" in str(excinfo.value)


# --------------------------------------------------------------------- the whole field set

#: (field, wrong TOML value) for every field ``RoleSpec`` declares — string fields given a
#: non-string, list fields given a non-list and a wrong element type, booleans a non-boolean.
_WRONG_TYPES: list[tuple[str, str]] = [
    ("full_name", "7"),
    ("full_name", "true"),
    ("title", '["a"]'),
    ("description", "3.5"),
    ("mission", "true"),
    ("model", "12"),
    ("color", "12345"),
    ("color", "[1, 2]"),
    ("is_default", '"maybe"'),
    ("can_spawn", "[]"),
    ("responsibilities", '"not a list"'),
    ("responsibilities", "[1, 2]"),
    ("responsibilities", "{ a = 1 }"),
    ("agreements", "42"),
    ("agreements", "[true]"),
]


@pytest.mark.parametrize(
    ("field", "value"), _WRONG_TYPES, ids=[f"{f}={v}" for f, v in _WRONG_TYPES]
)
def test_a_wrong_type_on_any_field_is_refused_naming_the_field(tmp_path, field, value) -> None:
    _place(tmp_path, "architect", f"{field} = {value}\n")

    with pytest.raises(SquadsError) as excinfo:
        resolve_role("architect", tmp_path)
    assert field in str(excinfo.value)


def test_the_table_covers_every_declared_field(tmp_path) -> None:
    """Keeps the table honest against the model rather than against whoever wrote it: a field
    added to ``RoleSpec`` later must gain a row, or this reddens. ``slug`` is excluded — it is
    filename-derived and has its own refusal."""
    covered = {field for field, _ in _WRONG_TYPES}
    missing = sorted(set(RoleSpec.model_fields) - covered - {"slug"})
    assert not missing, f"RoleSpec fields with no wrong-type case: {missing}"


def test_a_model_outside_the_catalogs_whitelist_is_refused(tmp_path) -> None:
    """Type-correct and still wrong: ``model`` is a plain string, so only the whitelist the
    bundled catalog already enforces on itself catches a typo'd model name."""
    _place(tmp_path, "architect", 'model = "opuss"\n')

    with pytest.raises(SquadsError) as excinfo:
        resolve_role("architect", tmp_path)
    assert "opuss" in str(excinfo.value)
    assert "opus" in str(excinfo.value)  # the accepted set is named, so it is fixable in place


@pytest.mark.parametrize("model", ["sonnet", "opus", "haiku", "inherit"])
def test_every_whitelisted_model_is_accepted(tmp_path, model: str) -> None:
    _place(tmp_path, "architect", f'model = "{model}"\n')

    assert resolve_role("architect", tmp_path).model == model


# --------------------------------------------------------------------- splat-refs


def test_the_append_idiom_spreads_the_bundled_list_instead_of_writing_the_token(
    tmp_path,
) -> None:
    """``["$(*self)", …]`` is what the override scaffold teaches. Unresolved, the literal string
    reached both the ROLE frontmatter and the rendered body."""
    bundled = resolve_role("architect", None).responsibilities
    _place(tmp_path, "architect", 'responsibilities = ["$(*self)", "Extra thing"]\n')

    role = resolve_role("architect", tmp_path)

    assert role.responsibilities == (*bundled, "Extra thing")
    assert not any("$(" in r for r in role.responsibilities)


def test_the_append_idiom_also_works_for_a_generated_dev_role(tmp_path) -> None:
    """A dev role's base is generated rather than catalogued, so its bundled list is only a
    splat target if the resolver composes against the generated definition."""
    base = resolve_dev_role("python", squad_dir=None).responsibilities
    _place(tmp_path, "python-dev", 'responsibilities = ["$(*self)", "Own the migrations"]\n')

    role = resolve_dev_role("python", squad_dir=tmp_path)

    assert role.responsibilities == (*base, "Own the migrations")


def test_a_splat_ref_on_a_brand_new_slug_dangles_rather_than_appending_nothing(
    tmp_path,
) -> None:
    """A wholly-new role has no bundled list to append to, so the token is a mistake — refused
    rather than quietly resolving to just the new entries."""
    _place(
        tmp_path,
        "security-expert",
        'full_name = "Sam"\ntitle = "t"\ndescription = "d"\nmission = "m"\n'
        'responsibilities = ["$(*self)", "Audit"]\n',
    )

    with pytest.raises(SquadsError) as excinfo:
        resolve_role("security-expert", tmp_path)
    assert "self" in str(excinfo.value)


def test_a_dotted_splat_path_addresses_a_bundled_field(tmp_path) -> None:
    _place(tmp_path, "architect", 'title = "$(mission)"\n')

    role = resolve_role("architect", tmp_path)

    assert role.title == resolve_role("architect", None).mission


# --------------------------------------------------------------------- the untouched path


def test_an_override_that_sets_nothing_leaves_the_bundled_role_intact(tmp_path) -> None:
    """The control for the whole file: validation must not change what a correct override
    produces. An empty override is the strictest form of that — every field falls through."""
    _place(tmp_path, "architect", "# only a comment\n")

    assert resolve_role("architect", tmp_path) == resolve_role("architect", None)
