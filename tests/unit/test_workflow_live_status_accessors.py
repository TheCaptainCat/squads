"""``WorkflowSpec.live_statuses``/``live_initial`` — the two derived, flag-keyed status
accessors that replace binding engine behaviour to a literal status name OR a role name:
``live_statuses`` is the read predicate ("is this entry on offer"), ``live_initial`` is
the create-at target for a call site that must *create* an entry already live. Both are
computed from ``machine_for(item_type).states`` and the existing per-status role resolution
(``role_for``) — no stored field, nothing declared twice.
"""

import pytest

from squads._errors import SquadsError
from squads._workflow import bundled_spec


def test_live_statuses_returns_the_sole_live_status_for_every_roster_type() -> None:
    spec = bundled_spec()
    for roster_type in ("role", "skill", "operator"):
        assert spec.live_statuses(roster_type) == {"Active"}


def test_live_statuses_returns_every_state_sharing_the_live_role_not_just_one() -> None:
    """A role can be carried by more than one status of a type's lifecycle (the read
    predicate's whole point) — the bundled work lifecycle's live 'active' role is carried by
    both InProgress and InReview."""
    spec = bundled_spec()
    assert spec.live_statuses("task") == {"InProgress", "InReview"}


def test_live_statuses_is_empty_for_a_type_whose_lifecycle_has_no_live_role() -> None:
    """The adr lifecycle (item type 'decision') never resolves any status to the live
    'active' role — the predicate degrades to empty rather than raising."""
    spec = bundled_spec()
    assert spec.live_statuses("decision") == frozenset()


def test_live_initial_returns_the_lifecycle_initial_for_every_bundled_roster_type() -> None:
    """The bundled agent lifecycle's initial ('Active') is itself live, so R1' vacates and
    live_initial simply returns it."""
    spec = bundled_spec()
    for roster_type in ("role", "skill", "operator"):
        assert spec.live_initial(roster_type) == "Active"
        assert spec.live_initial(roster_type) == spec.initial_status(roster_type)


def test_live_initial_falls_back_to_the_sole_live_status_when_initial_is_nonlive() -> None:
    """R1' guarantees exactly one live status whenever the lifecycle's own initial isn't
    live — that sole status is what a parked-then-activated roster entry is later
    transitioned into, and what live_initial resolves to when a caller creates one at
    initial instead."""
    from squads._workflow._models import Lifecycle, StatusSpec, WorkflowSpec

    base = bundled_spec()
    custom_statuses = {
        **base.statuses,
        "Provisioning": StatusSpec(role="pending"),  # not live
        "Online": StatusSpec(role="active"),  # the bundled live role
        "Decommissioned": StatusSpec(role="retired"),
    }
    custom_lifecycles = {
        **base.lifecycles,
        "parked_agent": Lifecycle(
            initial="Provisioning",
            transitions={
                "Provisioning": ["Online"],
                "Online": ["Decommissioned"],
                "Decommissioned": [],
            },
        ),
    }
    custom_items = {
        **base.items,
        "role": base.items["role"].model_copy(update={"lifecycle": "parked_agent"}),
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
    assert spec.initial_status("role") == "Provisioning"
    assert spec.live_statuses("role") == {"Online"}
    assert spec.live_initial("role") == "Online"


def test_live_initial_prefers_the_lifecycle_initial_over_a_second_live_status() -> None:
    """R1 permits more than one live status once the initial is itself one of them (R1'
    only bites when it isn't) — live_initial must still resolve to the lifecycle's own
    initial rather than picking arbitrarily from the live set, so scaffolding a fresh entry
    always lands on the state the lifecycle actually declares as its start."""
    from squads._workflow._models import Lifecycle, StatusSpec, WorkflowSpec

    base = bundled_spec()
    custom_statuses = {
        **base.statuses,
        "Online": StatusSpec(role="active"),  # the bundled live role — also the initial
        "AlsoOnline": StatusSpec(role="active"),  # a second live status
        "Retired2": StatusSpec(role="retired"),
    }
    custom_lifecycles = {
        **base.lifecycles,
        "dual_live_agent": Lifecycle(
            initial="Online",
            transitions={
                "Online": ["AlsoOnline", "Retired2"],
                "AlsoOnline": ["Retired2"],
                "Retired2": [],
            },
        ),
    }
    custom_items = {
        **base.items,
        "role": base.items["role"].model_copy(update={"lifecycle": "dual_live_agent"}),
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
    assert spec.live_statuses("role") == {"Online", "AlsoOnline"}
    assert spec.live_initial("role") == "Online"


def test_live_initial_never_raises_indexerror_or_stopiteration_on_a_bad_type() -> None:
    spec = bundled_spec()
    try:
        spec.live_initial("decision")  # no live status at all on this lifecycle
    except SquadsError:
        pass
    except (IndexError, StopIteration):  # fmt: skip
        pytest.fail("live_initial must raise SquadsError, never IndexError/StopIteration")
