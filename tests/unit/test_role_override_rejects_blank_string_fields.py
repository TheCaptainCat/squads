"""A role override declaring a blank string is refused at validation, not rendered.

An empty (or whitespace-only) string is never a legitimate "inherit the base value" signal --
omitting the key already means that -- and a declared blank reaches four-plus independent
render sites (the human and ``--json`` role-show output, both backends' roster-line templates,
and the Claude Code pointer's identity sentence) with nothing there to catch it. The refusal is
an explicit check in ``_apply_override`` (``src/squads/_roles/_resolver.py``), alongside the
existing model-whitelist check rather than declared on ``RoleSpec`` itself -- so it raises a
hand-written ``SquadsError`` naming the file and the field(s), not a raw
``pydantic.ValidationError`` whose default rendering is framework noise (a "1 validation error
for RoleSpec" header, a truncated ``input_value`` dict dump, a link to pydantic's own error
docs). Every consumer that builds a role override -- ``sq dev add``, ``sq sync``'s catalog
refresh, ``sq role <slug> show``, and ``sq check``'s override reporter (which resolves through
the exact same seam, so it needs no reporter of its own) -- refuses the same clean way with no
separate check to keep in sync.

Table-driven over the whole string-bearing field set, not one example per symptom: the three
fields the original bug drove (``full_name``, ``title``, ``mission``) are not the whole gap --
``description``, the optional ``model``/``color``, and the list fields (``responsibilities``,
``agreements``) share the same unconstrained-``str`` shape.
"""

from pathlib import Path

import pytest

from squads._errors import SquadsError
from squads._roles._models import RoleSpec
from squads._roles._resolver import resolve_role


def _place(tmp_path: Path, slug: str, body: str) -> None:
    d = tmp_path / ".overrides" / "roles"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{slug}.toml").write_text(body, encoding="utf-8")


# --------------------------------------------------------------------- the whole field set

#: (field, TOML literal) for every ``RoleSpec`` string-bearing field, blank and whitespace-only
#: both -- whitespace-only is deliberately not a separate code path, so it is proven on the same
#: table rather than in its own corner.
_BLANK_SCALAR_FIELDS: list[tuple[str, str]] = [
    ("full_name", '""'),
    ("full_name", '"   "'),
    ("title", '""'),
    ("title", '"   "'),
    ("description", '""'),
    ("description", '"   "'),
    ("mission", '""'),
    ("mission", '"   "'),
    ("model", '""'),
    ("model", '"   "'),
    ("color", '""'),
    ("color", '"   "'),
]

#: List fields get the same treatment per element, alongside a real entry so the refusal is
#: proven to be about the blank element, not merely "the list is short".
_BLANK_LIST_FIELDS: list[tuple[str, str]] = [
    ("responsibilities", '["Real one", ""]'),
    ("responsibilities", '["Real one", "   "]'),
    ("agreements", '["Real one", ""]'),
    ("agreements", '["Real one", "   "]'),
]


@pytest.mark.parametrize(
    ("field", "value"),
    _BLANK_SCALAR_FIELDS,
    ids=[f"{f}={v}" for f, v in _BLANK_SCALAR_FIELDS],
)
def test_a_blank_scalar_field_is_refused_naming_the_field(tmp_path, field, value) -> None:
    _place(tmp_path, "architect", f"{field} = {value}\n")

    with pytest.raises(SquadsError) as excinfo:
        resolve_role("architect", tmp_path)
    assert field in str(excinfo.value)
    assert "blank" in str(excinfo.value) or "whitespace" in str(excinfo.value)


@pytest.mark.parametrize(
    ("field", "value"), _BLANK_LIST_FIELDS, ids=[f"{f}={v}" for f, v in _BLANK_LIST_FIELDS]
)
def test_a_blank_list_entry_is_refused_naming_the_field(tmp_path, field, value) -> None:
    _place(tmp_path, "architect", f"{field} = {value}\n")

    with pytest.raises(SquadsError) as excinfo:
        resolve_role("architect", tmp_path)
    assert field in str(excinfo.value)


def test_the_table_covers_every_string_bearing_field() -> None:
    """Keeps the table honest against the model: a string field added to ``RoleSpec`` later
    must gain a row here, or this reddens. ``slug`` (filename-derived, its own refusal) and the
    two booleans are out of scope -- they are covered by tests/unit/test_role_override_is_
    validated_field_by_field.py's wrong-type table instead."""
    covered = {field for field, _ in (*_BLANK_SCALAR_FIELDS, *_BLANK_LIST_FIELDS)}
    non_string_fields = {"slug", "is_default", "can_spawn"}
    missing = sorted(set(RoleSpec.model_fields) - covered - non_string_fields)
    assert not missing, f"RoleSpec string fields with no blank-value case: {missing}"


# --------------------------------------------------------------------- the regression this risks


def test_omitting_a_key_still_inherits_the_base_value(tmp_path) -> None:
    """The refusal must not turn a legal partial override into an error: a file that simply
    never mentions ``title`` keeps the bundled ``title``, exactly as before this change."""
    _place(tmp_path, "architect", 'full_name = "Ada Lovelace"\n')

    role = resolve_role("architect", tmp_path)

    bundled = resolve_role("architect", None)
    assert role.full_name == "Ada Lovelace"
    assert role.title == bundled.title


def test_a_valid_override_with_real_values_still_applies(tmp_path) -> None:
    _place(
        tmp_path,
        "architect",
        'full_name = "Chief Design Officer"\nmodel = "opus"\ncolor = "teal"\n'
        'responsibilities = ["Real responsibility"]\n',
    )

    role = resolve_role("architect", tmp_path)

    assert role.full_name == "Chief Design Officer"
    assert role.model == "opus"
    assert role.color == "teal"
    assert role.responsibilities == ("Real responsibility",)


def test_a_complete_new_slug_override_with_real_values_still_applies(tmp_path) -> None:
    _place(
        tmp_path,
        "security-expert",
        'full_name = "Sam Security"\ntitle = "security expert"\n'
        'description = "Keeps the system secure."\nmission = "Find and fix security issues."\n',
    )

    role = resolve_role("security-expert", tmp_path)

    assert role.full_name == "Sam Security"


def test_the_bundled_catalog_itself_still_loads() -> None:
    """The bundled catalog's own real values are unaffected by this change either way -- this
    pins that the check being an explicit post-validation step rather than a declared
    constraint changes nothing about what the shipped ``roles.toml`` produces."""
    from squads._roles._catalog import PREDEFINED

    assert len(PREDEFINED) == 8
    for role in PREDEFINED:
        assert role.full_name.strip()
        assert role.title.strip()


# --------------------------------------------------------------------- message quality

#: Markers of pydantic's own default rendering -- if any of these show up in what an adopter
#: reads, the refusal leaked framework internals instead of speaking plainly about their file.
_PYDANTIC_LEAK_MARKERS = ("validation error for", "input_value=", "errors.pydantic.dev")


def test_the_blank_field_refusal_names_only_the_file_and_the_fields(tmp_path) -> None:
    """The exact message an adopter sees for the bug's own three-field repro: the file, one
    clean sentence naming every blank field, and nothing pydantic wrote. A test asserting only
    the exit code (or only ``field in str(exc)``, satisfied by pydantic's own noisy rendering
    too) is what let the leak through in the first place."""
    _place(tmp_path, "architect", 'full_name = ""\ntitle = ""\nmission = ""\n')
    toml_path = tmp_path / ".overrides" / "roles" / "architect.toml"

    with pytest.raises(SquadsError) as excinfo:
        resolve_role("architect", tmp_path)
    message = str(excinfo.value)

    assert message == (
        f"invalid role override {toml_path}: field(s) blank or whitespace-only "
        "(omit the key instead to inherit): full_name, title, mission"
    )
    for marker in _PYDANTIC_LEAK_MARKERS:
        assert marker not in message.lower(), (marker, message)


def test_a_single_whitespace_only_field_refusal_is_equally_clean(tmp_path) -> None:
    _place(tmp_path, "architect", 'title = "   "\n')
    toml_path = tmp_path / ".overrides" / "roles" / "architect.toml"

    with pytest.raises(SquadsError) as excinfo:
        resolve_role("architect", tmp_path)
    message = str(excinfo.value)

    assert message == (
        f"invalid role override {toml_path}: field(s) blank or whitespace-only "
        "(omit the key instead to inherit): title"
    )
    for marker in _PYDANTIC_LEAK_MARKERS:
        assert marker not in message.lower(), (marker, message)


def test_the_sibling_model_whitelist_message_is_unchanged(tmp_path) -> None:
    """Regression pin for the constraint the coordinator set: fixing the blank-field message
    must not flatten (or otherwise touch) the existing whitelist refusal it was modelled on."""
    _place(tmp_path, "architect", 'model = "gpt-9"\n')
    toml_path = tmp_path / ".overrides" / "roles" / "architect.toml"

    with pytest.raises(SquadsError) as excinfo:
        resolve_role("architect", tmp_path)

    assert str(excinfo.value) == (
        f"invalid role override {toml_path}: model 'gpt-9' is not one of "
        "['haiku', 'inherit', 'opus', 'sonnet']"
    )


def test_a_wrong_type_refusal_still_leaks_pydantic_internals_not_fixed_here(tmp_path) -> None:
    """Documents a pre-existing, out-of-scope sibling defect rather than silently curing it: a
    wrong-*type* value (as opposed to a blank one) on this same seam still raises the raw
    ``pydantic.ValidationError`` text, because that refusal was never moved off ``RoleSpec``.
    Pinned here so the leak is visible and attributable, not fixed -- widening this change to
    cover it too was explicitly out of scope."""
    _place(tmp_path, "architect", "full_name = 7\n")

    with pytest.raises(SquadsError) as excinfo:
        resolve_role("architect", tmp_path)
    message = str(excinfo.value).lower()

    assert any(marker in message for marker in _PYDANTIC_LEAK_MARKERS), str(excinfo.value)
