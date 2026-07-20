"""``Service.resolved_skills_for_role`` — the union of pure system membership
(``interactions.skills_for_role``) with data-driven ``scopes`` ref edges.

A skill scopes to a role via a forward ``SKILL.refs += ROLE-n:scopes`` edge; the resolver
inverts that (kind-filtered backrefs), maps to slugs, and dedups system-first then scoped.
"""

import pytest

from squads import _interactions as interactions
from squads._itemfile import read_frontmatter

pytestmark = pytest.mark.anyio


async def test_with_no_scope_edges_the_resolved_set_matches_pure_system_membership(svc):
    role = await svc.activate_role("tech-writer")
    assert await svc.resolved_skills_for_role("tech-writer") == interactions.skills_for_role(
        "tech-writer"
    )
    # And an unregistered/unknown slug degrades to the pure function, not an error.
    assert await svc.resolved_skills_for_role("nonexistent-role") == interactions.skills_for_role(
        "nonexistent-role"
    )
    assert role.extra.get("full_name")  # sanity: activation actually happened


async def test_a_skill_scoped_to_a_role_is_appended_after_the_system_skills(svc):
    role = await svc.activate_role("tech-writer")
    skill = await svc.add_skill("Release Runbook")
    await svc.add_ref(skill.id, role.id, kind="scopes")

    resolved = await svc.resolved_skills_for_role("tech-writer")
    system = interactions.skills_for_role("tech-writer")
    assert resolved[: len(system)] == system
    assert resolved[len(system) :] == ["release-runbook"]


async def test_scoping_two_skills_dedups_and_orders_the_scoped_tail_lexically(svc):
    role = await svc.activate_role("tech-writer")
    zeta = await svc.add_skill("Zeta Runbook")
    alpha = await svc.add_skill("Alpha Runbook")
    await svc.add_ref(zeta.id, role.id, kind="scopes")
    await svc.add_ref(alpha.id, role.id, kind="scopes")
    # Re-adding the same edge (idempotent) must not duplicate the slug in the resolved set.
    await svc.add_ref(zeta.id, role.id, kind="scopes")

    resolved = await svc.resolved_skills_for_role("tech-writer")
    system = interactions.skills_for_role("tech-writer")
    assert resolved == [*system, "alpha-runbook", "zeta-runbook"]


async def test_scoping_a_skill_to_one_role_does_not_affect_an_unrelated_roles_resolved_set(svc):
    scoped_role = await svc.activate_role("tech-writer")
    other_role = await svc.activate_role("architect")
    skill = await svc.add_skill("Release Runbook")
    await svc.add_ref(skill.id, scoped_role.id, kind="scopes")

    assert "release-runbook" in await svc.resolved_skills_for_role("tech-writer")
    assert await svc.resolved_skills_for_role("architect") == interactions.skills_for_role(
        "architect"
    )
    assert other_role.extra.get("slug") == "architect"  # sanity


async def test_a_ref_of_a_different_kind_pointing_at_the_role_is_not_treated_as_scoping(svc):
    role = await svc.activate_role("tech-writer")
    skill = await svc.add_skill("Release Runbook")
    await svc.add_ref(skill.id, role.id, kind="related")

    assert await svc.resolved_skills_for_role("tech-writer") == interactions.skills_for_role(
        "tech-writer"
    )


async def test_a_full_sync_persists_the_resolved_list_into_the_roles_extra_skills_cache(svc):
    """The resolved list lands in the role's frontmatter ``extra.skills`` (invariant #1: the
    ``.md`` file, not the rebuildable ``.squads.json`` index, is the source of truth a full
    sync writes to) and the role body's rendered ``## Skills`` section."""
    role = await svc.activate_role("tech-writer")
    skill = await svc.add_skill("Release Runbook")
    await svc.add_ref(skill.id, role.id, kind="scopes")

    await svc.sync()

    path = svc.paths.abspath(role.path)
    fm = read_frontmatter(text=path.read_text(encoding="utf-8"))
    resolved = await svc.resolved_skills_for_role("tech-writer")
    assert fm["extra"]["skills"] == resolved
    assert "release-runbook" in resolved  # sanity: the scoped skill is actually in there

    body = await svc.role_body("tech-writer")
    assert "`release-runbook`" in (body or "")
