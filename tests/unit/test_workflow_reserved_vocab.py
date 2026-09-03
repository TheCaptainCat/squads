"""The reserved surface, after the reserved-status floor's retirement, is exactly the three
roster types (each declaring ``category = "roster"``) — no status name is reserved any more.
A lifecycle bound to a ``category = "roster"`` type instead carries its own floor restated
against the ``live`` flag (R1 — at least one live status; R1' — exactly one when the
``initial`` itself isn't live; R2 — a settled, non-live status reachable from a live
one), asserted here via direct construction; the collect/lint/load-boundary surfacing of that
floor lives in ``test_workflow_lint_merge_errors.py`` and ``test_load_boundary_vocab.py``. A
custom type also cannot shadow a reserved prefix or folder.
"""

import pytest

from _helpers import FLOOR_STATUSES, ROSTER_TYPES, WORK_TYPES
from squads._errors import SquadsError
from squads._workflow import bundled_spec
from squads._workflow._models import ItemSpec, Lifecycle, StatusSpec, WorkflowSpec


def _spec_without_type(drop_type: str) -> dict[str, object]:
    """A raw payload for ``WorkflowSpec.model_validate`` missing *drop_type* — also strips it
    from every remaining type's ``parents``, and from any ``ref_rules``/``validators`` entry
    that targets it (``feature``'s ``implements`` rule targets ``contract``; no bundled type
    selects a ``ref_rule_target_present:<T>`` validator, but the strip covers that shape too so
    this helper keeps working for a spec that does), so the floor check is isolated from the
    separate parent-/ref-rule-target-reference integrity checks."""
    base = bundled_spec()
    items_without = {
        k: v.model_copy(
            update={
                "parents": [p for p in v.parents if p != drop_type],
                "ref_rules": [rr for rr in v.ref_rules if rr.target != drop_type],
                "validators": [
                    entry
                    for entry in v.validators
                    if entry.partition(":")[2] != drop_type or not entry.partition(":")[1]
                ],
            }
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
        "ref_kinds": base.ref_kinds,
        "views": base.views,
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
        "ref_kinds": base.ref_kinds,
        "views": base.views,
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
def test_dropping_an_agent_lifecycle_status_still_fails_closed_but_never_via_the_retired_message(
    floor_status: str,
) -> None:
    """Draft/Active/Archived are no longer a reserved-status floor — dropping one still fails
    to load, because the ``agent``/``work``/``guide`` lifecycles still reference it by name
    (lifecycle integrity), but never via the retired 'spec missing reserved Status members'
    message; that check no longer exists."""
    with pytest.raises(SquadsError) as exc_info:
        WorkflowSpec.model_validate(_spec_without_status(floor_status))
    assert "spec missing reserved Status members" not in str(exc_info.value)


def test_a_roster_lifecycle_may_use_entirely_custom_status_and_role_names() -> None:
    """No status name is reserved any more: a roster type's lifecycle may name its states
    anything, in any language, as long as at least one resolves to a live role (with the
    initial itself live here, vacating R1') and a settled, non-live one is reachable from
    it — the flag-keyed floor, not a literal Draft/Active/Archived requirement. The custom
    status name below is deliberately NOT "Live" — that word now names the flag itself, and
    picking it as a status literal would read as if the assertions below were circular."""
    base = bundled_spec()
    custom_statuses = {
        **base.statuses,
        "Provisioning": StatusSpec(role="pending"),
        "Online": StatusSpec(role="active"),
        "Decommissioned": StatusSpec(role="retired"),
    }
    custom_lifecycles = {
        **base.lifecycles,
        "custom_agent": Lifecycle(
            initial="Online",
            transitions={"Online": ["Decommissioned"], "Decommissioned": ["Online"]},
        ),
    }
    custom_items = {
        **base.items,
        "role": base.items["role"].model_copy(update={"lifecycle": "custom_agent"}),
    }
    spec = WorkflowSpec.model_validate(
        {
            "items": custom_items,
            "statuses": custom_statuses,
            "lifecycles": custom_lifecycles,
            "prefix_to_type": dict(base.prefix_to_type),
            "alias_to_type": dict(base.alias_to_type),
            "collections": dict(base.collections),
            "subentity_kinds": dict(base.subentity_kinds),
            "roles": dict(base.roles),
            "ref_kinds": dict(base.ref_kinds),
            "views": dict(base.views),
        }
    )
    assert spec.live_statuses("role") == {"Online"}
    assert spec.live_initial("role") == "Online"


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
    # lifecycle="agent" (not "work"): a category="roster" type's lifecycle must satisfy the
    # roster floor (exactly one 'active'-role status), which "work" does not.
    agent = ItemSpec(prefix="AGENT", folder="agents/custom", lifecycle="agent", category="roster")
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
            "ref_kinds": base.ref_kinds,
            "views": base.views,
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
