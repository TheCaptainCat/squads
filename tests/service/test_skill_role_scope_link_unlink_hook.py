"""``Service.link_role``/``unlink_role`` — the dedicated scoping verbs' service-layer
behaviour: they write (or remove) the skill's ``scopes`` edge to a role and then run the
partial-sync hook, which rewrites only that role's pointer + body ``## Skills`` region.

Contrast with a raw ``add_ref(..., kind="scopes")``: it writes the identical edge but is not
followed by the hook, so the role's pointer/body stay stale until the next full ``sync()`` —
proving the dedicated verb, not the edge itself, is what keeps things current.
"""

import pytest

from squads._itemfile import read_frontmatter
from squads._models._extras import ExtraKey as X

pytestmark = pytest.mark.anyio


def _pointer_path(svc, slug: str):
    return svc.paths.root / ".claude" / "agents" / f"{slug}.md"


async def test_link_role_resyncs_the_pointer_and_body_without_a_separate_sync_call(svc):
    role = await svc.activate_role("tech-writer")
    skill = await svc.add_skill("Release Runbook")

    await svc.link_role(skill.id, role.id)

    assert "release-runbook" in _pointer_path(svc, "tech-writer").read_text(encoding="utf-8")
    body = await svc.role_body("tech-writer")
    assert "release-runbook" in (body or "")
    fm = read_frontmatter(text=svc.paths.abspath(role.path).read_text(encoding="utf-8"))
    assert "release-runbook" in fm["extra"]["skills"]


async def test_a_raw_ref_add_writes_the_edge_but_leaves_the_pointer_stale_until_sync(svc):
    role = await svc.activate_role("tech-writer")
    skill = await svc.add_skill("Release Runbook")

    await svc.add_ref(skill.id, role.id, kind="scopes")
    # The edge exists (resolver already sees it)...
    assert "release-runbook" in await svc.resolved_skills_for_role("tech-writer")
    # ...but nothing has rewritten the pointer yet.
    assert "release-runbook" not in _pointer_path(svc, "tech-writer").read_text(encoding="utf-8")

    await svc.sync()
    assert "release-runbook" in _pointer_path(svc, "tech-writer").read_text(encoding="utf-8")


async def test_unlink_role_resyncs_the_pointer_and_body_immediately(svc):
    role = await svc.activate_role("tech-writer")
    skill = await svc.add_skill("Release Runbook")
    await svc.link_role(skill.id, role.id)

    await svc.unlink_role(skill.id, role.id)

    assert "release-runbook" not in _pointer_path(svc, "tech-writer").read_text(encoding="utf-8")
    body = await svc.role_body("tech-writer")
    assert "release-runbook" not in (body or "")
    fm = read_frontmatter(text=svc.paths.abspath(role.path).read_text(encoding="utf-8"))
    assert "release-runbook" not in fm["extra"]["skills"]


async def test_only_the_linked_roles_pointer_and_body_are_touched(svc):
    scoped_role = await svc.activate_role("tech-writer")
    other_role = await svc.activate_role("architect")
    other_pointer = _pointer_path(svc, "architect")
    other_body_before = await svc.role_body("architect")
    other_bytes_before = other_pointer.read_bytes()
    skill = await svc.add_skill("Release Runbook")

    await svc.link_role(skill.id, scoped_role.id)

    assert "release-runbook" in _pointer_path(svc, "tech-writer").read_text(encoding="utf-8")
    assert other_pointer.read_bytes() == other_bytes_before
    assert await svc.role_body("architect") == other_body_before
    assert other_role.extra.get(X.SLUG) == "architect"  # sanity


async def test_end_state_after_link_matches_a_full_sync(svc):
    """No drift between the incremental hook and the authoritative full sweep."""
    role = await svc.activate_role("tech-writer")
    skill = await svc.add_skill("Release Runbook")

    await svc.link_role(skill.id, role.id)
    hook_pointer = _pointer_path(svc, "tech-writer").read_text(encoding="utf-8")
    hook_body = await svc.role_body("tech-writer")

    await svc.sync()
    synced_pointer = _pointer_path(svc, "tech-writer").read_text(encoding="utf-8")
    synced_body = await svc.role_body("tech-writer")

    assert hook_pointer == synced_pointer
    assert hook_body == synced_body


async def test_relinking_an_already_scoped_role_is_idempotent(svc):
    role = await svc.activate_role("tech-writer")
    skill = await svc.add_skill("Release Runbook")

    await svc.link_role(skill.id, role.id)
    await svc.link_role(skill.id, role.id)

    refs = await svc.refs_out(skill.id)
    scope_refs = [r for r in refs if r[1] == "scopes"]
    assert scope_refs == [(role.id, "scopes")]


async def test_unlinking_a_role_that_was_never_scoped_is_a_clean_no_op(svc):
    role = await svc.activate_role("tech-writer")
    skill = await svc.add_skill("Release Runbook")

    updated = await svc.unlink_role(skill.id, role.id)

    assert updated.refs == []


async def test_removing_the_last_role_link_leaves_no_orphaned_reference(svc):
    role = await svc.activate_role("tech-writer")
    skill = await svc.add_skill("Release Runbook")
    await svc.link_role(skill.id, role.id)

    await svc.unlink_role(skill.id, role.id)

    refreshed = await svc.get(skill.id)
    assert refreshed.refs == []


async def test_linking_to_a_non_role_item_is_rejected(svc):
    role_like_task = (await svc.create("task", "Not a role")).item
    skill = await svc.add_skill("Release Runbook")

    with pytest.raises(Exception, match="targets a role"):
        await svc.link_role(skill.id, role_like_task.id)


async def test_one_skill_scoped_to_several_roles_at_once_preloads_all_and_only_those(svc):
    """The release-runbook case: one custom skill linked to manager, devops, AND
    tech-writer preloads it for all three (resolver + pointer + body), while a role never
    linked (python-dev) sees no trace of it in any of the three surfaces."""
    manager = await svc.activate_role("manager")
    devops = await svc.activate_role("devops")
    writer = await svc.activate_role("tech-writer")
    outsider = await svc.add_dev("python")
    skill = await svc.add_skill("Release Runbook")

    for role in (manager, devops, writer):
        await svc.link_role(skill.id, role.id)

    for slug in ("manager", "devops", "tech-writer"):
        assert "release-runbook" in await svc.resolved_skills_for_role(slug)
        assert "release-runbook" in _pointer_path(svc, slug).read_text(encoding="utf-8")
        body = await svc.role_body(slug)
        assert "release-runbook" in (body or "")

    assert "release-runbook" not in await svc.resolved_skills_for_role("python-dev")
    assert "release-runbook" not in _pointer_path(svc, "python-dev").read_text(encoding="utf-8")
    outsider_body = await svc.role_body("python-dev")
    assert "release-runbook" not in (outsider_body or "")
    assert outsider.extra.get(X.SLUG) == "python-dev"  # sanity


async def test_unlink_leaves_a_different_kind_edge_to_the_same_role_intact(svc):
    role = await svc.activate_role("tech-writer")
    skill = await svc.add_skill("Release Runbook")
    await svc.link_role(skill.id, role.id)
    await svc.add_ref(skill.id, role.id, kind="related")

    await svc.unlink_role(skill.id, role.id)

    refs = await svc.refs_out(skill.id)
    assert (role.id, "related") in refs
    assert (role.id, "scopes") not in refs


async def test_unlink_leaves_a_scopes_edge_to_a_different_role_intact(svc):
    kept_role = await svc.activate_role("architect")
    dropped_role = await svc.activate_role("tech-writer")
    skill = await svc.add_skill("Release Runbook")
    await svc.link_role(skill.id, kept_role.id)
    await svc.link_role(skill.id, dropped_role.id)

    await svc.unlink_role(skill.id, dropped_role.id)

    refs = await svc.refs_out(skill.id)
    assert (kept_role.id, "scopes") in refs
    assert (dropped_role.id, "scopes") not in refs
    assert "release-runbook" in await svc.resolved_skills_for_role("architect")
    assert "release-runbook" not in await svc.resolved_skills_for_role("tech-writer")
