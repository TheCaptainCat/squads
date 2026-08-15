"""``sq check`` reports a roster entry already sitting in a config-invalid state (the
config-integrity clauses C1-C3), exercised end to end through the CLI: the right exit code, and
the dependants named in the output.

The interactive retirement gate now refuses each of these transitions, so the invalid state is
reached by a direct index write (bypassing the service layer), mirroring
``tests/integration/test_check_detects_structural_corruption.py``'s pattern for other
otherwise-service-refused corruption — never through ``svc.set_status``.
"""

import json

import pytest

from squads._services import _service as service

pytestmark = pytest.mark.anyio


async def test_check_exits_3_and_names_the_role_still_preloading_an_archived_skill(project, invoke):
    svc = service.Service(project)
    await svc.seed_bundled_skills()
    squads_skill = await svc.roster_item("skill", "squads")
    assert squads_skill is not None
    async with svc.store.transaction() as db:
        db.items[squads_skill.sequence_id].status = "Archived"

    result = await invoke(["check"])
    assert result.exit_code == 3, result.output
    assert squads_skill.id in result.output
    assert "config integrity" in result.output


async def test_check_json_names_the_scoped_role_for_an_archived_custom_skill(project, invoke):
    svc = service.Service(project)
    role = await svc.roster_item("role", "manager")
    assert role is not None
    skill = await svc.add_skill("Custom Helper")
    await svc.link_role(skill.id, role.id)
    async with svc.store.transaction() as db:
        db.items[skill.sequence_id].status = "Archived"

    result = await invoke(["check", "--json"])
    assert result.exit_code == 3, result.output
    issues = json.loads(result.output)
    hit = next(i for i in issues if i["item"] == skill.id)
    assert "manager" in hit["message"]


async def test_check_stays_clean_on_a_freshly_seeded_squad(project, invoke):
    svc = service.Service(project)
    await svc.seed_bundled_skills()

    result = await invoke(["check"])
    assert result.exit_code == 0, result.output
