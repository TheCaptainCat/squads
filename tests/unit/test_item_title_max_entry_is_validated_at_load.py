"""The `item_title_max:<n>` entry at spec load: the threshold is required and must be a positive
integer written in ASCII digits; a second entry is a repeat; the check is refused on a roster
type. The same parser governs `subentity_title_max`, so a digit that `int()` rejects is refused
there too instead of raising.
"""

import pytest

from squads._errors import SquadsError
from squads._workflow import bundled_spec
from squads._workflow._models import ItemSpec, WorkflowSpec
from squads._workflow._validator_names import parse_positive_int


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


_MISSING = "missing its required parameter"
_NOT_POSITIVE = "non-positive-integer item_title_max threshold"

_REFUSED = [
    (["item_title_max"], _MISSING),
    (["item_title_max:"], _MISSING),
    (["item_title_max@error"], _MISSING),
    (["item_title_max:0"], _NOT_POSITIVE),
    (["item_title_max:-5"], _NOT_POSITIVE),
    (["item_title_max:1.5"], _NOT_POSITIVE),
    (["item_title_max:abc"], _NOT_POSITIVE),
    (["item_title_max: 80"], _NOT_POSITIVE),
    (["item_title_max:80 "], _NOT_POSITIVE),
    (["item_title_max:²"], _NOT_POSITIVE),
    (["item_title_max:٨٠"], _NOT_POSITIVE),
    (["item_title_max:80@fatal"], "unknown level"),
    (["item_title_max:80", "item_title_max:90"], "selected more than once"),
    (["item_title_max:80", "item_title_max:80@error"], "selected more than once"),
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
    assert entries[-1] in text


@pytest.mark.parametrize("entry", ["item_title_max:1", "item_title_max:80", "item_title_max:080"])
@pytest.mark.parametrize("suffix", ["", "@warn", "@error"])
def test_a_positive_integer_threshold_loads_at_either_level(entry: str, suffix: str) -> None:
    spec = _load("task", [entry + suffix])
    assert spec.item_title_max("task") == int(entry.split(":")[1])
    assert spec.item_title_max("bug") is None


@pytest.mark.parametrize("roster_type", ["role", "skill", "operator"])
@pytest.mark.parametrize("entry", ["item_title_max:80", "item_title_max:80@error"])
def test_the_check_is_refused_on_a_roster_type(roster_type: str, entry: str) -> None:
    with pytest.raises(SquadsError) as raised:
        _load(roster_type, [entry])
    text = str(raised.value)
    assert f"item {roster_type!r}" in text
    assert entry in text
    assert "cannot apply to a roster type" in text


@pytest.mark.parametrize("roster_type", ["role", "skill", "operator"])
def test_a_roster_type_may_still_select_a_check_outside_the_policy_set(roster_type: str) -> None:
    _load(roster_type, ["no_status_banner"])


@pytest.mark.parametrize(
    ("text", "value"),
    [("1", 1), ("80", 80), ("080", 80), ("0", None), ("-1", None), ("", None), ("²", None)],
)
def test_the_positive_integer_parser_reads_ascii_digits_only(text: str, value: int | None) -> None:
    assert parse_positive_int(text) == value


def test_a_superscript_digit_in_a_sub_entity_threshold_is_refused_not_raised() -> None:
    with pytest.raises(SquadsError, match="non-positive-integer subentity_title_max threshold"):
        _load("task", ["subentity_title_max:²"])
