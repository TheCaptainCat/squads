"""The type/status floor is exactly the three roster types plus Draft/Active/Archived — everything
else (the 7 work types, the sub-entity/finding statuses) is ordinary, droppable spec vocabulary.
A custom type also cannot shadow a reserved prefix or folder.
"""

import pytest

from _helpers import FLOOR_STATUSES, FORMER_FLOOR_STATUSES, ROSTER_TYPES, WORK_TYPES
from squads._errors import SquadsError
from squads._workflow import bundled_spec
from squads._workflow._models import ItemSpec, WorkflowSpec


def _spec_without_type(drop_type: str) -> dict[str, object]:
    """A raw payload for ``WorkflowSpec.model_validate`` missing *drop_type* — also strips it
    from every remaining type's ``parents`` so the floor check is isolated from the separate
    parent-reference integrity check."""
    base = bundled_spec()
    items_without = {
        k: (
            v.model_copy(update={"parents": [p for p in v.parents if p != drop_type]})
            if drop_type in v.parents
            else v
        )
        for k, v in base.items.items()
        if k != drop_type
    }
    prefix_without = {p: t for p, t in base.prefix_to_type.items() if t != drop_type}
    return {
        "items": items_without,
        "statuses": base.statuses,
        "lifecycles": base.lifecycles,
        "prefix_to_type": prefix_without,
        "alias_to_type": base.alias_to_type,
        "collections": base.collections,
        "subentity_kinds": base.subentity_kinds,
        "roles": base.roles,
    }


def _spec_without_status(drop_status: str) -> dict[str, object]:
    base = bundled_spec()
    return {
        "items": base.items,
        "statuses": {k: v for k, v in base.statuses.items() if k != drop_status},
        "lifecycles": base.lifecycles,
        "prefix_to_type": base.prefix_to_type,
        "alias_to_type": base.alias_to_type,
        "collections": base.collections,
        "subentity_kinds": base.subentity_kinds,
        "roles": base.roles,
    }


# --------------------------------------------------------------------------- type floor


@pytest.mark.parametrize("roster_type", sorted(ROSTER_TYPES))
def test_spec_missing_a_roster_type_fails_closed(roster_type: str) -> None:
    with pytest.raises(SquadsError, match="spec missing required roster types"):
        WorkflowSpec.model_validate(_spec_without_type(roster_type))


@pytest.mark.parametrize("work_type", sorted(WORK_TYPES))
def test_spec_missing_a_work_type_loads_successfully(work_type: str) -> None:
    """Only the three roster types are floor-enforced; every work type is droppable."""
    WorkflowSpec.model_validate(_spec_without_type(work_type))  # must not raise


# --------------------------------------------------------------------------- status floor


@pytest.mark.parametrize("floor_status", sorted(FLOOR_STATUSES))
def test_spec_missing_a_floor_status_fails_closed(floor_status: str) -> None:
    with pytest.raises(SquadsError, match="spec missing reserved Status members"):
        WorkflowSpec.model_validate(_spec_without_status(floor_status))


@pytest.mark.parametrize("former_floor_status", sorted(FORMER_FLOOR_STATUSES))
def test_former_floor_subentity_statuses_no_longer_hit_the_floor(
    former_floor_status: str,
) -> None:
    """Dropping a sub-entity/finding status still fails (a lifecycle still names it in its
    transitions) but via lifecycle integrity, never via the reserved-floor check — proving these
    left the reserved floor and became ordinary spec vocabulary."""
    with pytest.raises(SquadsError) as exc_info:
        WorkflowSpec.model_validate(_spec_without_status(former_floor_status))
    assert "spec missing reserved Status members" not in str(exc_info.value)


# --------------------------------------------------------------------------- prefix/folder shadow


def test_custom_type_cannot_shadow_a_reserved_prefix() -> None:
    base = bundled_spec()
    new_items = {
        **base.items,
        "shadow-task": ItemSpec(prefix="TASK", folder="shadow-tasks", lifecycle="work"),
    }
    with pytest.raises(SquadsError, match="duplicate prefix"):
        WorkflowSpec.model_validate(
            {
                "items": new_items,
                "statuses": base.statuses,
                "lifecycles": base.lifecycles,
                "prefix_to_type": base.prefix_to_type,
                "alias_to_type": base.alias_to_type,
                "roles": base.roles,
            }
        )


def test_custom_type_cannot_shadow_a_reserved_folder() -> None:
    base = bundled_spec()
    new_items = {**base.items, "shadow": ItemSpec(prefix="SHAD", folder="tasks", lifecycle="work")}
    new_prefix_to_type = {**base.prefix_to_type, "SHAD": "shadow"}
    with pytest.raises(SquadsError, match="duplicate folder"):
        WorkflowSpec.model_validate(
            {
                "items": new_items,
                "statuses": base.statuses,
                "lifecycles": base.lifecycles,
                "prefix_to_type": new_prefix_to_type,
                "alias_to_type": base.alias_to_type,
                "roles": base.roles,
            }
        )


# --------------------------------------------------------------------------- non_roster_types()


def test_non_roster_types_excludes_roster_types_and_includes_every_builtin_work_type() -> None:
    spec = bundled_spec()
    nrt = spec.non_roster_types()
    assert nrt == {t for t in spec.items if not spec.item_is_roster(t)}
    for rt in ROSTER_TYPES:
        assert rt not in nrt


def test_non_roster_types_matches_category_derived_expectation() -> None:
    """Independent of ``item_is_roster``: ``non_roster_types()`` is exactly the
    non-``roster``-category set (work + records)."""
    spec = bundled_spec()
    assert spec.non_roster_types() == {t for t, ts in spec.items.items() if ts.category != "roster"}


def test_non_roster_types_includes_a_custom_work_type_but_not_a_custom_roster_type() -> None:
    base = bundled_spec()
    incident = ItemSpec(prefix="INC", folder="incidents", lifecycle="work", category="work")
    agent = ItemSpec(prefix="AGENT", folder="agents/custom", lifecycle="work", category="roster")
    new_items = {**base.items, "incident": incident, "custom-agent": agent}
    new_prefix_to_type = {**base.prefix_to_type, "INC": "incident", "AGENT": "custom-agent"}
    spec = WorkflowSpec.model_validate(
        {
            "items": new_items,
            "statuses": base.statuses,
            "lifecycles": base.lifecycles,
            "prefix_to_type": new_prefix_to_type,
            "alias_to_type": base.alias_to_type,
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
            "roles": base.roles,
        }
    )
    nrt = spec.non_roster_types()
    assert "incident" in nrt
    assert "custom-agent" not in nrt


def test_module_level_non_roster_types_matches_the_bundled_specs_own_method() -> None:
    """``squads._workflow.non_roster_types()`` — a package-level convenience wrapper over the
    bundled singleton's own ``non_roster_types()`` method, proven above."""
    from squads._workflow import non_roster_types

    spec = bundled_spec()
    assert non_roster_types() == spec.non_roster_types()
    for rt in ROSTER_TYPES:
        assert rt not in non_roster_types()


# --------------------------------------------------------------------------- graceful degradation
# A custom work type has no PLAYBOOK/interactions entry — every playbook accessor degrades to
# empty rather than KeyError (the playbook stays PLAYBOOK-keyed / built-in-only).


def test_managed_item_types_is_playbook_keyed_and_excludes_a_hypothetical_custom_type() -> None:
    from _helpers import BUILTIN_TYPES
    from squads._interactions import managed_item_types

    managed = managed_item_types()
    for item_type in managed:
        assert item_type in BUILTIN_TYPES
    assert "incident" not in [str(t) for t in managed]


def test_skills_for_role_degrades_gracefully_when_custom_types_exist() -> None:
    from squads._interactions import skills_for_role

    result = skills_for_role("manager")
    assert isinstance(result, list) and result


def test_in_lane_owner_degrades_to_empty_for_a_type_with_no_lane_owner() -> None:
    from squads._interactions import in_lane_owner

    assert in_lane_owner("incident") == set()
