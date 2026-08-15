"""``activate`` is a create verb, and it guarantees the role it reports on is live.

Activating a slug whose roster entry exists but has been retired used to return that entry
untouched, so the CLI printed ``activated <Name> (ROLE-n)`` at exit 0 while the status stayed
retired — a success line for a command that did nothing, with `sq check` silent either side.

Refusing (rather than performing the transition) is what keeps ``activate`` consistent with
every sibling roster create verb — ``add_dev``, ``add_skill``, ``add_operator`` all raise on an
existing slug — and keeps "create" and "transition" as separate verbs. The refusal names the
transition verb that does work, resolved from the roster type's own live-initial status rather
than a hard-coded one, so a project that renamed its roster lifecycle is told its own vocabulary.
"""

import pytest

from squads._errors import SquadsError
from squads._workflow import ROSTER_ROLE

pytestmark = pytest.mark.anyio


async def _activated_then_retired(svc, slug: str):
    """A role that has been through the whole legitimate cycle — activated, then retired — which
    is the only way to reach the shape this guards: a roster entry that exists but is not live."""
    role = await svc.activate_role(slug)
    await svc.set_status(role.id, "Archived")
    return role


async def test_activating_a_retired_role_refuses_instead_of_reporting_a_no_op(svc):
    role = await _activated_then_retired(svc, "tech-writer")

    with pytest.raises(SquadsError) as excinfo:
        await svc.activate_role("tech-writer")

    message = str(excinfo.value)
    assert "Archived" in message  # says which status it is actually in
    assert role.id in message
    # and names the verb that does the job, in the roster type's own vocabulary
    assert f"sq role tech-writer status {svc.spec.live_initial(ROSTER_ROLE)}" in message


async def test_the_refusal_leaves_the_role_exactly_as_it_was(svc):
    await _activated_then_retired(svc, "tech-writer")

    with pytest.raises(SquadsError):
        await svc.activate_role("tech-writer")

    still = await svc.roster_item(ROSTER_ROLE, "tech-writer")
    assert still is not None and still.status == "Archived"


async def test_the_named_remedy_actually_makes_the_role_live_again(svc):
    """The point of naming a remedy is that following it works — otherwise the refusal has
    just moved the dead end one command further along."""
    role = await _activated_then_retired(svc, "tech-writer")

    await svc.set_status(role.id, svc.spec.live_initial(ROSTER_ROLE))

    revived = await svc.activate_role("tech-writer")
    assert revived.status in svc.spec.live_statuses(ROSTER_ROLE)


async def test_activating_an_already_live_role_stays_an_idempotent_no_op(svc):
    """The postcondition already holds, so the success line is true — and `init`/`adopt` both
    lean on re-activation being harmless."""
    before = await svc.roster_item(ROSTER_ROLE, "manager")
    assert before is not None

    again = await svc.activate_role("manager")
    assert again.id == before.id
    assert again.status == before.status


async def test_a_slug_with_no_roster_entry_is_still_created_live(svc):
    role = await svc.activate_role("devops")
    assert role.status in svc.spec.live_statuses(ROSTER_ROLE)


async def test_activate_matches_its_sibling_create_verbs_on_a_retired_slug(svc):
    """The behaviour this aligns to: every other roster create verb already refuses an existing
    slug whatever its status. Pinned here so a future 'make it idempotent' change has to face
    all four at once rather than quietly re-splitting activate off from the family."""
    dev = await svc.add_dev("python")
    skill = await svc.add_skill("Some Skill")
    operator = await svc.add_operator("Some Person")
    for item in (dev, skill, operator):
        await svc.set_status(item.id, "Archived")
    await _activated_then_retired(svc, "tech-writer")

    with pytest.raises(SquadsError, match="already exists"):
        await svc.add_dev("python")
    with pytest.raises(SquadsError, match="already exists"):
        await svc.add_skill("Some Skill")
    with pytest.raises(SquadsError, match="already exists"):
        await svc.add_operator("Some Person")
    with pytest.raises(SquadsError, match="already exists"):
        await svc.activate_role("tech-writer")
