"""``Service.seed_bundled_skills()`` is idempotent: calling it a second time allocates no new
ids or sequence numbers, returning an empty list once every bundled skill is already stamped
with a convention-named file.
"""

import pytest

from squads._services._service import Service
from squads._workflow import ROSTER_SKILL, bundled_spec
from squads._workflow._models import Lifecycle, StatusSpec, WorkflowSpec

pytestmark = pytest.mark.anyio


async def test_seeding_a_second_time_allocates_nothing_new(svc):
    first = await svc.seed_bundled_skills()
    assert first  # sanity: something was actually seeded

    skills_before = await svc.list_items(item_type="skill")
    ids_before = {sk.id for sk in skills_before}
    seqs_before = {sk.sequence_id for sk in skills_before}

    second = await svc.seed_bundled_skills()
    assert second == []

    skills_after = await svc.list_items(item_type="skill")
    assert {sk.id for sk in skills_after} == ids_before
    assert {sk.sequence_id for sk in skills_after} == seqs_before


async def test_seed_bundled_skills_creates_at_the_live_status_when_initial_is_nonlive(
    svc,
):
    """squads scaffolding its own system skills must create LIVE, not merely at whatever the
    lifecycle declares as `initial` — a generated role entry preloads a skill by slug regardless
    of that skill item's status, so seeding at a non-live initial would leave every role entry
    preloading a skill that was never materialised. Here the skill type's lifecycle is rebound to
    a parked-then-activated machine (initial 'Provisioning', non-live) with 'Active' (live)
    one hop away; the seeded items must land on 'Active', not 'Provisioning'."""
    base = bundled_spec()
    agent = base.lifecycles["agent"]
    custom_lifecycles = {
        **base.lifecycles,
        "parked_skill_agent": Lifecycle(
            initial="Provisioning",
            transitions={"Provisioning": ["Active"], **agent.transitions},
        ),
    }
    custom_items = {
        **base.items,
        ROSTER_SKILL: base.items[ROSTER_SKILL].model_copy(
            update={"lifecycle": "parked_skill_agent"}
        ),
    }
    custom_statuses = {**base.statuses, "Provisioning": StatusSpec(role="pending")}
    custom_spec = WorkflowSpec.model_validate(
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
        }
    )
    assert custom_spec.initial_status(ROSTER_SKILL) == "Provisioning"
    assert custom_spec.live_initial(ROSTER_SKILL) == "Active"

    custom_svc = Service(svc.paths, spec=custom_spec)
    seeded = await custom_svc.seed_bundled_skills()
    assert seeded  # sanity: something was actually seeded
    assert all(sk.status == "Active" for sk in seeded)
