"""A skill implied by a declared type is refused on every surface with the mechanism stated
(the implicating type, and that it stays implied while declared), never a recommendation to
drop the type; the retirement gate and the `sq check` reporter print the same condition."""

import pytest

from squads._errors import ConfigIntegrityError

pytestmark = pytest.mark.anyio

_CONDITION = "not live but implied by declared type(s): task"


async def _gate(svc) -> str:
    await svc.activate_role("tech-lead")  # its playbook interacts with task
    skill = await svc.add_skill("Sq Task")
    with pytest.raises(ConfigIntegrityError) as excinfo:
        await svc.set_roster_status(skill.id, "Archived")
    return str(excinfo.value)


async def _reporter(svc) -> str:
    await svc.seed_bundled_skills()
    await svc.activate_role("tech-lead")
    sq_task = await svc.roster_item("skill", "sq-task")
    async with svc.store.transaction() as db:
        db.items[sq_task.sequence_id].status = "Archived"
    issues = await svc.check()
    return next(i.message for i in issues if "config integrity" in i.message)


async def _removal(svc) -> str:
    await svc.seed_bundled_skills()
    await svc.activate_role("tech-lead")
    sq_task = await svc.roster_item("skill", "sq-task")
    with pytest.raises(ConfigIntegrityError) as excinfo:
        await svc.remove_item(sq_task.id, purge=True)
    return str(excinfo.value)


_SURFACES = {"retirement refusal": _gate, "check reporter": _reporter, "removal refusal": _removal}


@pytest.mark.parametrize("surface", list(_SURFACES))
async def test_each_surface_states_the_implicating_type_and_never_advises_a_drop(
    svc, surface: str
) -> None:
    message = await _SURFACES[surface](svc)

    assert "task" in message
    assert "implied by declared type(s)" in message
    assert "for as long as those types are declared" in message
    assert "[selected]" not in message
    assert "drop" not in message


@pytest.mark.parametrize("surface", ["retirement refusal", "check reporter"])
async def test_the_gate_and_the_reporter_share_one_condition_text(svc, surface: str) -> None:
    message = await _SURFACES[surface](svc)

    assert _CONDITION in message


async def test_the_retirement_refusal_states_the_target_status_once(svc) -> None:
    assert (await _gate(svc)).count("'Archived'") == 1
