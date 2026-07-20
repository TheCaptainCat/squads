"""``sq skill <n> link-role``/``unlink-role`` — the sanctioned CLI surface for scoping a
custom skill to a role. Each verb writes the ``scopes`` edge and immediately resyncs the
affected role's Claude pointer and body ``## Skills`` section (no separate ``sq sync`` needed).
"""

import pytest

from squads._services import _service as service

pytestmark = pytest.mark.anyio


@pytest.fixture
async def seeded_paths(tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal")
    return result.paths


def _pointer_text(paths, slug: str) -> str:
    return (paths.root / ".claude" / "agents" / f"{slug}.md").read_text(encoding="utf-8")


async def test_link_role_makes_the_role_pointer_preload_the_skill_immediately(
    seeded_paths, invoke
) -> None:
    svc = service.Service(seeded_paths)
    role = await svc.activate_role("tech-writer")
    skill = await svc.add_skill("Release Runbook")

    r = await invoke(["skill", str(skill.sequence_id), "link-role", role.extra["slug"]])
    assert r.exit_code == 0, r.output

    assert "release-runbook" in _pointer_text(seeded_paths, "tech-writer")
    body = await svc.role_body("tech-writer")
    assert "release-runbook" in (body or "")


async def test_link_role_accepts_a_role_addressed_by_full_id(seeded_paths, invoke) -> None:
    svc = service.Service(seeded_paths)
    role = await svc.activate_role("tech-writer")
    skill = await svc.add_skill("Release Runbook")

    r = await invoke(["skill", str(skill.sequence_id), "link-role", role.id])
    assert r.exit_code == 0, r.output
    assert "release-runbook" in _pointer_text(seeded_paths, "tech-writer")


async def test_unlink_role_drops_the_skill_from_the_role_pointer_immediately(
    seeded_paths, invoke
) -> None:
    svc = service.Service(seeded_paths)
    role = await svc.activate_role("tech-writer")
    skill = await svc.add_skill("Release Runbook")
    r = await invoke(["skill", str(skill.sequence_id), "link-role", "tech-writer"])
    assert r.exit_code == 0, r.output

    r = await invoke(["skill", str(skill.sequence_id), "unlink-role", "tech-writer"])
    assert r.exit_code == 0, r.output

    assert "release-runbook" not in _pointer_text(seeded_paths, "tech-writer")
    body = await svc.role_body("tech-writer")
    assert "release-runbook" not in (body or "")
    assert role.extra.get("slug") == "tech-writer"  # sanity


async def test_linking_a_nonexistent_role_gives_a_clear_error(seeded_paths, invoke) -> None:
    svc = service.Service(seeded_paths)
    skill = await svc.add_skill("Release Runbook")

    r = await invoke(["skill", str(skill.sequence_id), "link-role", "no-such-role"])
    assert r.exit_code != 0
    assert "no-such-role" in r.output


async def test_relinking_an_already_linked_role_is_a_clean_no_op(seeded_paths, invoke) -> None:
    svc = service.Service(seeded_paths)
    await svc.activate_role("tech-writer")
    skill = await svc.add_skill("Release Runbook")

    r1 = await invoke(["skill", str(skill.sequence_id), "link-role", "tech-writer"])
    assert r1.exit_code == 0, r1.output
    r2 = await invoke(["skill", str(skill.sequence_id), "link-role", "tech-writer"])
    assert r2.exit_code == 0, r2.output

    refs = await svc.refs_out(skill.id)
    scope_refs = [r for r in refs if r[1] == "scopes"]
    assert len(scope_refs) == 1


async def test_unlinking_a_role_never_linked_is_a_clean_no_op(seeded_paths, invoke) -> None:
    svc = service.Service(seeded_paths)
    await svc.activate_role("tech-writer")
    skill = await svc.add_skill("Release Runbook")

    r = await invoke(["skill", str(skill.sequence_id), "unlink-role", "tech-writer"])
    assert r.exit_code == 0, r.output
    assert await svc.refs_out(skill.id) == []


async def test_link_role_run_for_several_roles_preloads_all_and_only_those(
    seeded_paths, invoke
) -> None:
    """The release-runbook scenario: one skill linked via the verb to manager, devops, AND
    tech-writer in turn preloads it for each; a role never linked (python-dev) does not."""
    svc = service.Service(seeded_paths)
    await svc.activate_role("manager")
    await svc.activate_role("devops")
    await svc.activate_role("tech-writer")
    await svc.add_dev("python")
    skill = await svc.add_skill("Release Runbook")

    for slug in ("manager", "devops", "tech-writer"):
        r = await invoke(["skill", str(skill.sequence_id), "link-role", slug])
        assert r.exit_code == 0, r.output

    for slug in ("manager", "devops", "tech-writer"):
        assert "release-runbook" in _pointer_text(seeded_paths, slug)
    assert "release-runbook" not in _pointer_text(seeded_paths, "python-dev")
