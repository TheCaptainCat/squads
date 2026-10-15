"""The `external_id_not_in_title:<regex>` entry at spec load: the pattern is required and must
compile, `@` is reserved for the level so a pattern cannot hold one, a second entry is a repeat,
and the check is refused on a roster type. A pattern keeps every colon after the first.
"""

import pytest

from squads._errors import SquadsError
from squads._workflow import bundled_spec
from squads._workflow._models import ItemSpec, WorkflowSpec

_NAME = "external_id_not_in_title"
_AT = "'@' separates the pattern from the level"
_GENERIC_LEVEL = "names an unknown level"


def _load(item_type: str, entries: list[str]) -> WorkflowSpec:
    base = bundled_spec()
    items: dict[str, ItemSpec] = {
        **base.items,
        item_type: base.items[item_type].model_copy(update={"validators": entries}),
    }
    return WorkflowSpec.model_validate(
        {
            "items": items,
            "statuses": dict(base.statuses),
            "lifecycles": dict(base.lifecycles),
            "prefix_to_type": dict(base.prefix_to_type),
            "alias_to_type": dict(base.alias_to_type),
            "collections": dict(base.collections),
            "subentity_kinds": dict(base.subentity_kinds),
            "roles": dict(base.roles),
            "ref_kinds": dict(base.ref_kinds),
            "views": dict(base.views),
        }
    )


_REFUSED = [
    ([_NAME], "missing its required parameter"),
    ([f"{_NAME}:"], "missing its required parameter"),
    ([f"{_NAME}@error"], "missing its required parameter"),
    ([f"{_NAME}:[abc"], "unterminated character set"),
    ([f"{_NAME}:(ab"], "missing )"),
    ([f"{_NAME}:user@host"], _AT),
    ([f"{_NAME}:a@b@error"], _AT),
    ([f"{_NAME}:[A-Z]+-[0-9]+@fatal"], _AT),
    ([f"{_NAME}:[A-Z]+-[0-9]+", f"{_NAME}:GH-[0-9]+"], "selected more than once"),
    ([f"{_NAME}:[A-Z]+-[0-9]+", f"{_NAME}:[A-Z]+-[0-9]+@error"], "selected more than once"),
]


@pytest.mark.parametrize(("entries", "message"), _REFUSED, ids=lambda v: str(v))
def test_a_malformed_entry_is_refused_naming_the_type_and_the_entry(
    entries: list[str], message: str
) -> None:
    with pytest.raises(SquadsError) as raised:
        _load("task", entries)
    text = str(raised.value)
    assert message in text
    assert "item 'task'" in text
    assert repr(entries[-1]) in text


@pytest.mark.parametrize("entry", [f"{_NAME}:user@host", f"{_NAME}:a@b@error"])
def test_a_pattern_holding_an_at_sign_earns_one_message_not_the_generic_level_message(
    entry: str,
) -> None:
    with pytest.raises(SquadsError) as raised:
        _load("task", [entry])
    assert _GENERIC_LEVEL not in str(raised.value)
    assert str(raised.value).count(_AT) == 1


def test_the_missing_parameter_message_shows_the_entry_form() -> None:
    with pytest.raises(SquadsError, match=r"name it as 'external_id_not_in_title:<regex>'"):
        _load("task", [_NAME])


def test_a_compile_error_carries_the_compilers_own_text() -> None:
    with pytest.raises(SquadsError, match=r"invalid regular expression '\[abc': .*unterminated"):
        _load("task", [f"{_NAME}:[abc"])


@pytest.mark.parametrize("suffix", ["", "@warn", "@error"])
@pytest.mark.parametrize("pattern", [r"[A-Z]+-\d+", "foo", "a:b", r"\x40", "(?i)abc-[0-9]+"])
def test_a_valid_pattern_loads_at_either_level_and_is_kept_whole(pattern: str, suffix: str) -> None:
    spec = _load("task", [f"{_NAME}:{pattern}{suffix}"])
    assert spec.item_external_id_pattern("task") == pattern
    assert spec.item_external_id_pattern("bug") is None


@pytest.mark.parametrize("roster_type", ["role", "skill", "operator"])
@pytest.mark.parametrize("entry", [f"{_NAME}:[A-Z]+-[0-9]+", f"{_NAME}:[A-Z]+-[0-9]+@error"])
def test_the_check_is_refused_on_a_roster_type(roster_type: str, entry: str) -> None:
    with pytest.raises(SquadsError) as raised:
        _load(roster_type, [entry])
    text = str(raised.value)
    assert f"item {roster_type!r}" in text
    assert "cannot apply to a roster type" in text
