"""`Service.remove_item`: a roster item is removed only with `purge=True`; without it the call
raises before writing anything."""

import pytest

from squads._errors import SquadsError

pytestmark = pytest.mark.anyio


async def test_remove_item_without_purge_raises_and_leaves_the_index_and_file(svc):
    skill = await svc.add_skill("Temp skill")
    path = svc.paths.abspath(skill.path)
    before = (svc.paths.squad_dir / ".squads.json").read_bytes()

    with pytest.raises(SquadsError, match="--purge") as exc:
        await svc.remove_item(skill.id, purge=False)

    assert f"sq skill {skill.id} status Archived" in str(exc.value)
    assert path.exists()
    assert (svc.paths.squad_dir / ".squads.json").read_bytes() == before


async def test_remove_item_names_only_purge_for_an_archived_entry(svc):
    skill = await svc.add_skill("Temp skill")
    await svc.set_roster_status(skill.id, "Archived")

    with pytest.raises(SquadsError) as exc:
        await svc.remove_item(skill.id, purge=False)

    assert "remove --purge" in str(exc.value)
    assert "status" not in str(exc.value)


async def test_remove_item_names_the_gate_when_the_archive_gate_would_refuse(svc):
    await svc.activate_role("tech-lead")  # its playbook interacts with task
    skill = await svc.add_skill("Sq Task")  # implied by the task type: archiving is refused

    with pytest.raises(SquadsError) as exc:
        await svc.remove_item(skill.id, purge=False)

    assert f"cannot remove {skill.id}" in str(exc.value)
    assert "remove --purge" not in str(exc.value)
