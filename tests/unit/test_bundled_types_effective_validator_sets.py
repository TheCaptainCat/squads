"""The effective per-item validator set of every bundled type under the bundled spec, written
out as literal tuples so a check that moves in or out of a floor or a bundle shows as a diff to
this table and not as a silent change in what every squad runs.
"""

import pytest

from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import effective_validator_names

_WORK = (
    "item_status_valid",
    "dangling_ref",
    "ref_kind_valid",
    "agent_registered",
    "parent_acyclic",
    "parent_in",
    "subentity_status_valid",
    "subentity_container_marker",
    "subentity_body_written",
    "subtask_story_mapping",
)
_RECORDS = (
    "item_status_valid",
    "dangling_ref",
    "ref_kind_valid",
    "agent_registered",
    "parent_acyclic",
    "no_parent",
    "supersedes_incoming",
)
_ROSTER = (
    "item_status_valid",
    "dangling_ref",
    "ref_kind_valid",
    "agent_registered",
    "parent_acyclic",
)

EXPECTED: dict[str, tuple[str, ...]] = {
    "epic": (*_WORK, "no_parent"),
    "feature": _WORK,
    "task": _WORK,
    "bug": _WORK,
    "review": _WORK,
    "decision": _RECORDS,
    "contract": _RECORDS,
    "milestone": _RECORDS,
    "guide": _RECORDS,
    "role": _ROSTER,
    "skill": (*_ROSTER, "item_skill_shadowed"),
    "operator": _ROSTER,
}


def test_every_bundled_type_has_a_row() -> None:
    assert set(load_workflow_spec().items) == set(EXPECTED)


@pytest.mark.parametrize("item_type", sorted(EXPECTED))
def test_the_effective_set_of_a_bundled_type_is_what_its_category_and_own_list_give(
    item_type: str,
) -> None:
    ts = load_workflow_spec().items[item_type]
    assert effective_validator_names(ts.category, extra=tuple(ts.validators)) == EXPECTED[item_type]
