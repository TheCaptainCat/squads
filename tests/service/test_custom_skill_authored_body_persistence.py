"""A custom (author-defined) skill's authored body — set via ``Service.set_body`` — survives
``sq sync``, ``sq skill regen``, and ``sq repair`` unchanged, because none of the three ever
reads or rewrites an author-defined skill's ``:body`` region. A freshly added custom skill
with no authored body yet still renders coherently (no error, no crash) on
``show``/``read_body``.
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_a_freshly_added_custom_skill_with_no_authored_body_reads_back_cleanly(svc):
    skill = await svc.add_skill("Release Runbook", description="Ship a release safely.")

    body = await svc.read_body(skill.id)
    assert "## Instructions" in body  # the create-time stub, not empty/broken


async def test_authored_custom_skill_body_survives_sync_regen_and_repair(svc):
    skill = await svc.add_skill("Release Runbook", description="Ship a release safely.")
    authored = "## Instructions\n\nCut the branch, tag it, then publish."
    await svc.set_body(skill.id, authored)
    assert await svc.read_body(skill.id) == authored

    await svc.sync()
    assert await svc.read_body(skill.id) == authored

    await svc.regen(skill.id)
    assert await svc.read_body(skill.id) == authored

    await svc.repair()
    assert await svc.read_body(skill.id) == authored
