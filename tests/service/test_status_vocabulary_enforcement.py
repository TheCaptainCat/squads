"""``set_status`` rejects any status outside the target type's declared vocabulary, and
``--force`` only ever bypasses a declared-illegal transition EDGE — never the vocabulary
itself. This distinction is load-bearing: force can skip a hop within a type's own statuses,
but can never set a status that type doesn't declare at all. One concrete type (bug) proves
the full happy-path lifecycle end to end through the service.
"""

import pytest

from squads._errors import InvalidTransitionError, StatusNotInWorkflowError

pytestmark = pytest.mark.anyio


async def test_set_status_rejects_a_status_outside_the_declared_vocabulary(svc):
    bug = (await svc.create("bug", "crash on login")).item
    assert bug.status == "Open"
    with pytest.raises(StatusNotInWorkflowError, match="'Done' is not a valid status for bug"):
        await svc.set_status(bug.id, "Done")


async def test_set_status_rejects_repeated_attempts_with_different_invalid_statuses(svc):
    bug = (await svc.create("bug", "crash")).item
    for invalid in ("Draft", "Ready", "InReview", "Done"):
        with pytest.raises(StatusNotInWorkflowError):
            await svc.set_status(bug.id, invalid, force=True)


async def test_force_bypasses_the_transition_edge_but_never_the_vocabulary(svc):
    """force can skip a declared-illegal hop WITHIN the type's own vocabulary (Open ->
    Verified on a bug is not a legal edge, but Verified IS a bug status) — but force can
    never set a status the type doesn't declare at all (Done is not a bug status, period)."""
    bug = (await svc.create("bug", "crash")).item

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
    bug = (await svc.create("bug", "null pointer")).item
    bug = await svc.set_status(bug.id, "InProgress")
    bug = await svc.set_status(bug.id, "Fixed")
    bug = await svc.set_status(bug.id, "Verified")
    assert bug.status == "Verified"

    wontfix = (await svc.create("bug", "by design")).item
    wontfix = await svc.set_status(wontfix.id, "WontFix")
    wontfix = await svc.set_status(wontfix.id, "Open")  # reopen
    assert wontfix.status == "Open"

    regressed = (await svc.create("bug", "flicker")).item
    await svc.set_status(regressed.id, "InProgress")
    await svc.set_status(regressed.id, "Fixed")
    await svc.set_status(regressed.id, "Verified")
    regressed = await svc.set_status(regressed.id, "InProgress")  # regression reopen
    assert regressed.status == "InProgress"
