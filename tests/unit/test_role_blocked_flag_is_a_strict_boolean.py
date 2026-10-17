"""A role declares that its statuses mean "blocked" with a boolean `blocked` key: omitted is
false, a TOML boolean is read as written, and any other shape is refused naming the role and the
key. Exactly one bundled role declares it, and the spec accessor reads the flag of the role a
status resolves to.
"""

import pytest

from squads._errors import SquadsError
from squads._workflow import bundled_spec
from squads._workflow._loader import _parse_role  # pyright: ignore[reportPrivateUsage]
from squads._workflow._models import RoleSpec

_BASE: dict[str, object] = {"settled": False, "color": "neutral"}


@pytest.mark.parametrize(
    ("declared", "expected"),
    [({}, False), ({"blocked": True}, True), ({"blocked": False}, False)],
    ids=["omitted", "true", "false"],
)
def test_a_boolean_or_an_omitted_key_is_read_as_written(
    declared: dict[str, object], expected: bool
) -> None:
    assert _parse_role("waiting", {**_BASE, **declared}).blocked is expected


@pytest.mark.parametrize(
    "written",
    ["yes", "true", "", 1, 0, 1.5, [True], {"a": 1}],
    ids=["yes", "true-string", "empty-string", "one", "zero", "float", "list", "table"],
)
def test_any_non_boolean_is_refused_naming_the_role_and_the_key(written: object) -> None:
    with pytest.raises(SquadsError) as raised:
        _parse_role("waiting", {**_BASE, "blocked": written})
    text = str(raised.value)
    assert "'waiting'" in text
    assert "blocked must be true or false" in text
    assert "pydantic" not in text


def test_the_model_refuses_a_non_boolean_too() -> None:
    with pytest.raises(ValueError, match="blocked"):
        RoleSpec.model_validate({**_BASE, "blocked": "yes"})


def test_exactly_the_bundled_blocked_role_declares_the_flag() -> None:
    spec = bundled_spec()
    assert sorted(name for name, role in spec.roles.items() if role.blocked) == ["blocked"]
