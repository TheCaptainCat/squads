"""``Service.resolved_skills_for_role`` — the union of pure system membership
(``role_guidance.skills_for_role``) with data-driven ``scopes`` ref edges.

A skill scopes to a role via a forward ``SKILL.refs += ROLE-n:scopes`` edge; the resolver
inverts that (kind-filtered backrefs), maps to slugs, and dedups system-first then scoped.
"""

import pytest

from squads._interactions import _role_guidance as role_guidance
from squads._interactions import get_playbook_spec
from squads._itemfile import read_frontmatter
from squads._workflow import bundled_spec

_SPEC = bundled_spec()
_PB = get_playbook_spec()

pytestmark = pytest.mark.anyio


async def test_with_no_scope_edges_the_resolved_set_matches_pure_system_membership(svc):
    role = await svc.activate_role("tech-writer")
    assert await svc.resolved_skills_for_role("tech-writer") == role_guidance.skills_for_role(
        "tech-writer", _SPEC, _PB
    )
    # And an unregistered/unknown slug degrades to the pure function, not an error.
    assert await svc.resolved_skills_for_role("nonexistent-role") == role_guidance.skills_for_role(
        "nonexistent-role", _SPEC, _PB
    )
    assert role.title  # sanity: activation actually happened


async def test_a_skill_scoped_to_a_role_is_appended_after_the_system_skills(svc):
    role = await svc.activate_role("tech-writer")
    skill = await svc.add_skill("Release Runbook")
    await svc.add_ref(skill.id, role.id, kind="scopes")

    resolved = await svc.resolved_skills_for_role("tech-writer")
    system = role_guidance.skills_for_role("tech-writer", _SPEC, _PB)
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
    system = role_guidance.skills_for_role("tech-writer", _SPEC, _PB)
    assert resolved == [*system, "alpha-runbook", "zeta-runbook"]


async def test_scoping_a_skill_to_one_role_does_not_affect_an_unrelated_roles_resolved_set(svc):
    scoped_role = await svc.activate_role("tech-writer")
    other_role = await svc.activate_role("architect")
    skill = await svc.add_skill("Release Runbook")
    await svc.add_ref(skill.id, scoped_role.id, kind="scopes")

    assert "release-runbook" in await svc.resolved_skills_for_role("tech-writer")
    assert await svc.resolved_skills_for_role("architect") == role_guidance.skills_for_role(
        "architect", _SPEC, _PB
    )
    assert other_role.slug == "architect"  # sanity


async def test_a_ref_of_a_different_kind_pointing_at_the_role_is_not_treated_as_scoping(svc):
    role = await svc.activate_role("tech-writer")
    skill = await svc.add_skill("Release Runbook")
    await svc.add_ref(skill.id, role.id, kind="related")

    assert await svc.resolved_skills_for_role("tech-writer") == role_guidance.skills_for_role(
        "tech-writer", _SPEC, _PB
    )


async def test_a_full_sync_never_materialises_the_resolved_list_into_the_role(svc):
    """The resolved list is a computed projection, not a cache: a full sync persists neither
    a ``skills`` key in the role's frontmatter nor a rendered ``## Skills`` section in its
    resolved definition — ``resolved_skills_for_role`` answers the same list, recomputed from
    the index on every call, with no I/O beyond what the caller already loaded."""
    role = await svc.activate_role("tech-writer")
    skill = await svc.add_skill("Release Runbook")
    await svc.add_ref(skill.id, role.id, kind="scopes")

    await svc.sync()

    path = svc.paths.abspath(role.path)
    fm = read_frontmatter(text=path.read_text(encoding="utf-8"))
    assert "skills" not in fm

    definition = await svc.read_body(role.id)
    assert "## Skills" not in definition

    resolved = await svc.resolved_skills_for_role("tech-writer")
    assert "release-runbook" in resolved  # sanity: the scoped skill is still resolved live
