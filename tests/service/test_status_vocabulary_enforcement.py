"""``set_status`` rejects any status outside the target type's declared vocabulary, and
``--force`` only ever bypasses a declared-illegal transition EDGE — never the vocabulary
itself. This distinction is load-bearing: force can skip a hop within a type's own statuses,
but can never set a status that type doesn't declare at all. One concrete type (bug) proves
the full happy-path lifecycle end to end through the service.

The roster types (role/skill/operator) share one lifecycle (``Active`` ⇄ ``Archived``) and
are covered here too, alongside the work-item vocabulary enforcement they share the mechanism
with: each is created ``Active``, can reach ``Archived`` and back, rejects a status outside
its own declared lifecycle and a disallowed edge with the same two error types, and the
enumeration in the error text is per-type (proving the target set is derived from the
addressed type's own lifecycle, not a single fixed list). ``Draft`` is no longer part of the
roster lifecycle — it stays declared globally (the work/guide lifecycles own it), so it is
now a vocabulary violation for a roster type, not merely an off-edge one.
"""

import pytest

from _helpers import create_item
from squads._errors import InvalidTransitionError, StatusNotInWorkflowError

pytestmark = pytest.mark.anyio


async def test_set_status_rejects_a_status_outside_the_declared_vocabulary(svc):
    bug = (await create_item(svc, "bug", "crash on login")).item
    assert bug.status == "Open"
    with pytest.raises(StatusNotInWorkflowError, match="'Done' is not a valid status for bug"):
        await svc.set_status(bug.id, "Done")


async def test_set_status_rejects_repeated_attempts_with_different_invalid_statuses(svc):
    bug = (await create_item(svc, "bug", "crash")).item
    for invalid in ("Draft", "Ready", "InReview", "Done"):
        with pytest.raises(StatusNotInWorkflowError):
            await svc.set_status(bug.id, invalid, force=True)


async def test_force_bypasses_the_transition_edge_but_never_the_vocabulary(svc):
    """force can skip a declared-illegal hop WITHIN the type's own vocabulary (Open ->
    Verified on a bug is not a legal edge, but Verified IS a bug status) — but force can
    never set a status the type doesn't declare at all (Done is not a bug status, period)."""
    bug = (await create_item(svc, "bug", "crash")).item

    # Vocabulary violation: force does NOT help.
    with pytest.raises(StatusNotInWorkflowError, match="not a valid status for bug"):
        await svc.set_status(bug.id, "Done", force=True)

    # Edge violation: without force it's rejected...
    with pytest.raises(InvalidTransitionError):
        await svc.set_status(bug.id, "Verified")
    # ...with force, the edge skip succeeds because Verified IS in bug's vocabulary.
    result = await svc.set_status(bug.id, "Verified", force=True)
    assert result.status == "Verified"


async def test_bugs_full_lifecycle_happy_path_and_wontfix_and_regression_reopen(svc):
    """One concrete type proves the mechanism end to end — not multiplied per type."""
    bug = (await create_item(svc, "bug", "null pointer")).item
    bug = await svc.set_status(bug.id, "InProgress")
    bug = await svc.set_status(bug.id, "Fixed")
    bug = await svc.set_status(bug.id, "Verified")
    assert bug.status == "Verified"

    wontfix = (await create_item(svc, "bug", "by design")).item
    wontfix = await svc.set_status(wontfix.id, "WontFix")
    wontfix = await svc.set_status(wontfix.id, "Open")  # reopen
    assert wontfix.status == "Open"

    regressed = (await create_item(svc, "bug", "flicker")).item
    await svc.set_status(regressed.id, "InProgress")
    await svc.set_status(regressed.id, "Fixed")
    await svc.set_status(regressed.id, "Verified")
    regressed = await svc.set_status(regressed.id, "InProgress")  # regression reopen
    assert regressed.status == "InProgress"


# --------------------------------------------------------------------------- roster types


async def test_role_moves_through_its_declared_lifecycle_and_back(svc):
    role = await svc.activate_role("qa")
    assert role.status == "Active"
    role = await svc.set_status(role.id, "Archived")
    assert role.status == "Archived"
    role = await svc.set_status(role.id, "Active")
    assert role.status == "Active"


async def test_skill_moves_through_its_declared_lifecycle_and_back(svc):
    skill = await svc.add_skill("Temp Skill")
    assert skill.status == "Active"
    skill = await svc.set_status(skill.id, "Archived")
    assert skill.status == "Archived"
    skill = await svc.set_status(skill.id, "Active")
    assert skill.status == "Active"


async def test_operator_moves_through_its_declared_lifecycle_and_back(svc):
    op = await svc.add_operator("Temp Operator")
    assert op.status == "Active"
    op = await svc.set_status(op.id, "Archived")
    assert op.status == "Archived"
    op = await svc.set_status(op.id, "Active")
    assert op.status == "Active"


async def test_roster_types_reject_a_status_outside_their_own_declared_lifecycle(svc):
    role = await svc.activate_role("qa")
    skill = await svc.add_skill("Temp Skill")
    op = await svc.add_operator("Temp Operator")

    with pytest.raises(StatusNotInWorkflowError, match="not a valid status for role"):
        await svc.set_status(role.id, "InProgress")
    with pytest.raises(StatusNotInWorkflowError, match="not a valid status for skill"):
        await svc.set_status(skill.id, "InProgress")
    with pytest.raises(StatusNotInWorkflowError, match="not a valid status for operator"):
        await svc.set_status(op.id, "InProgress")


async def test_roster_status_error_enumerates_only_that_type_s_own_states(svc):
    """The allowed-states enumeration in the error text is the addressed type's own lifecycle
    — proof (alongside the absence of any status literal in the CLI verb itself) that the
    target set is derived per type rather than a single hardcoded list. ``Draft`` is declared
    globally (work/guide own it) but is not part of role's own two-state lifecycle, so it is
    correctly absent from this enumeration."""
    role = await svc.activate_role("qa")
    with pytest.raises(
        StatusNotInWorkflowError,
        match=r"allowed: Active, Archived",
    ):
        await svc.set_status(role.id, "Bogus")


async def test_roster_status_draft_is_a_vocabulary_violation_not_an_edge_one(svc):
    """``Draft`` used to be part of the bundled role/skill/operator lifecycle and reachable via
    ``--force``; now that the lifecycle only declares Active/Archived, Draft is a vocabulary
    violation (rejected even with ``force``) rather than a merely-off-edge one."""
    role = await svc.activate_role("qa")
    with pytest.raises(StatusNotInWorkflowError, match="not a valid status for role"):
        await svc.set_status(role.id, "Draft")
    with pytest.raises(StatusNotInWorkflowError, match="not a valid status for role"):
        await svc.set_status(role.id, "Draft", force=True)


async def test_roster_status_force_bypasses_the_edge_but_never_the_vocabulary(svc):
    role = await svc.activate_role("qa")

    # Both Active<->Archived edges are declared on the bundled machine, so the edge-violation
    # half of this distinction is proven by the shared bug-type test above; here we confirm
    # force still cannot reach a status role doesn't declare at all.
    with pytest.raises(StatusNotInWorkflowError, match="not a valid status for role"):
        await svc.set_status(role.id, "Done", force=True)
