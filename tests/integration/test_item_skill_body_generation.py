"""Per-item generated skill body (``sq-<type>``) through the REAL backend
(``svc.refresh_managed()`` writing real files under the squad folder) — not the render-mirror
that tests/unit/test_item_skill_dev_gate.py uses to pin the golden: active-role sections
reflect only actually-active roles; actor guidance is structured, not free prose; the dev
section is gated on an active ``*-dev`` role; the trailer names only the type's actual
sub-entity kind; the lifecycle description reflects an overridden status machine — and, the
sibling of the dropped-type no-crash family (tests/unit/test_dropped_type_authoring_prose_no_
crash.py), falls back to the frozen playbook lifecycle line rather than crashing when the
type itself has been dropped from the active spec.

Also covers two per-item-skill content facts not explicitly numbered by the coverage ledger
but with no other home found (flagged in the chunk close-out): each active role's per-type
comment-scoping guidance names the right sub-entity command shape, and a sub-entity's title
guidance teaches "handle, not full description" consistently across story/subtask/finding.
"""

import pytest

from squads import _interactions as interactions

pytestmark = pytest.mark.anyio


def _item_skill_body(project, item_type: str) -> str:
    return (
        project.squad_dir / "agents" / "skills" / f"{interactions.item_skill_name(item_type)}.md"
    ).read_text(encoding="utf-8")


async def test_item_skills_are_generated_with_a_thin_claude_pointer_and_a_real_squad_body(
    project,
):
    skills_dir = project.root / ".claude" / "skills"
    for it in interactions.managed_item_types():
        pointer = (skills_dir / interactions.item_skill_name(it) / "SKILL.md").read_text(
            encoding="utf-8"
        )
        assert interactions.item_skill_name(it) in pointer
        assert (
            project.squad_dir / "agents" / "skills" / f"{interactions.item_skill_name(it)}.md"
        ).is_file()
    feature = _item_skill_body(project, "feature")
    # 'minimal' roster (manager only) has no active role sections for feature.
    assert "## For " not in feature
    assert "add-story" in feature  # the generic command block is always present


async def test_active_role_sections_reflect_only_actually_active_roles(svc, project):
    await svc.activate_role("product-owner")
    await svc.activate_role("qa")
    await svc.refresh_managed()
    feature = _item_skill_body(project, "feature")
    assert "Nina Product" in feature
    assert "Olivia Lead" not in feature  # tech-lead never activated


async def test_actor_guidance_is_structured_not_free_prose(svc, project):
    await svc.add_dev("python")
    await svc.refresh_managed()
    task = _item_skill_body(project, "task")
    assert "## For developers" in task
    for label in ("**Enter**", "**Do:**", "**Hand off:**", "**Watch for:**"):
        assert label in task
    assert "acceptance criteria" in task
    assert "@reviewer" in task
    assert "don't author features/tasks" in task


async def test_the_dev_section_is_gated_on_an_active_dev_role(svc, project):
    assert "## For developers" not in _item_skill_body(project, "task")
    await svc.add_dev("rust")
    await svc.refresh_managed()
    assert "## For developers" in _item_skill_body(project, "task")


async def test_the_reviewers_section_carries_its_own_scope_discipline(svc, project):
    await svc.activate_role("reviewer")
    await svc.refresh_managed()
    task = _item_skill_body(project, "task")
    assert "Paul Reviewer" in task
    assert "don't fix the code yourself" in task


async def test_the_trailer_names_only_the_types_own_actual_subentity_kind(project):
    feature = _item_skill_body(project, "feature")
    assert "Its stories\nget their bodies from `sq feature <n> story <k> body" in feature
    task = _item_skill_body(project, "task")
    assert "Its subtasks\nget their bodies from `sq task <n> subtask <k> body" in task
    review = _item_skill_body(project, "review")
    assert "Its findings\nget their bodies from `sq review <n> finding <k> body" in review
    for hostless in ("epic", "decision", "guide", "bug"):
        assert "get their bodies from" not in _item_skill_body(project, hostless)


async def test_lifecycle_line_reflects_an_overridden_status_machine(project):
    from squads._services import _service as service
    from squads._workflow import bundled_spec

    base = bundled_spec()
    overridden_task = base.items["task"].model_copy(update={"lifecycle": "guide"})
    spec = base.model_copy(update={"items": {**base.items, "task": overridden_task}})
    await service.Service(project, spec=spec).refresh_managed()
    task = _item_skill_body(project, "task")
    lifecycle_line = next(ln for ln in task.splitlines() if ln.startswith("**Lifecycle:**"))
    assert lifecycle_line == "**Lifecycle:** Draft → Published → Deprecated"


async def test_a_dropped_type_falls_back_to_the_frozen_lifecycle_line_rather_than_crashing(
    project,
):
    """ "bug" (not task/feature/epic, which sit on workflow.md.j2's hardcoded parent-chain walk)
    is dropped here — its item skill must still render via the frozen playbook fallback."""
    from squads._services import _service as service
    from squads._workflow import bundled_spec

    base = bundled_spec()
    dropped_items = {k: v for k, v in base.items.items() if k != "bug"}
    spec = base.model_copy(update={"items": dropped_items})
    await service.Service(project, spec=spec).refresh_managed()
    bug = _item_skill_body(project, "bug")
    lifecycle_line = next(ln for ln in bug.splitlines() if ln.startswith("**Lifecycle:**"))
    assert lifecycle_line == (
        "**Lifecycle:** Open → InProgress → Fixed → Verified (+ WontFix, Blocked, Cancelled)"
    )
    assert "get their bodies from" not in bug


async def test_item_skills_teach_the_full_comments_briefing_in_their_enter_section(svc, project):
    await svc.add_dev("python")
    await svc.refresh_managed()
    for it in interactions.managed_item_types():
        body = _item_skill_body(project, it)
        assert "--full --comments" in body, f"sq-{it} skill missing --full --comments briefing"
        assert "show --full --comments" in body


async def test_per_type_skills_carry_role_specific_scoped_comment_guidance(svc, project):
    await svc.activate_role("reviewer")
    await svc.activate_role("product-owner")
    await svc.activate_role("tech-lead")
    await svc.add_dev("python")
    await svc.refresh_managed()

    review = _item_skill_body(project, "review")
    assert "finding <k> comment" in review
    assert "comment-scoping convention" in review

    feature = _item_skill_body(project, "feature")
    assert "story <k> comment" in feature
    assert "comment-scoping convention" in feature

    task = _item_skill_body(project, "task")
    assert "subtask <k> comment" in task
    assert "comment-scoping convention" in task


async def test_subentity_title_guidance_teaches_handle_not_full_description_per_kind(svc, project):
    await svc.activate_role("reviewer")
    await svc.activate_role("product-owner")
    await svc.activate_role("tech-lead")
    await svc.refresh_managed()

    review = _item_skill_body(project, "review")
    assert "short handle" in review
    assert "full description goes in the finding body" in review
    assert "finding <k> body" in review

    feature = _item_skill_body(project, "feature")
    assert "user-story phrase" in feature
    assert "the acceptance criteria live there, not in the title" in feature
    assert "story <k> body" in feature

    task = _item_skill_body(project, "task")
    assert "short handle" in task
    assert "implementation detail goes in the subtask body" in task
    assert "subtask <k> body" in task


async def test_pointer_frontmatter_lists_the_roles_own_skills_list(svc, project):
    from squads import _sections as sections

    def _fm(path):
        return sections.split_frontmatter(path.read_text(encoding="utf-8"))

    await svc.activate_role("product-owner")
    await svc.refresh_managed()
    fm, _ = _fm(project.root / ".claude" / "agents" / "product-owner.md")
    assert fm["skills"] == ["squads", "greeting", "sq-memory", "sq-epic", "sq-feature"]
    mfm, _ = _fm(project.root / ".claude" / "agents" / "manager.md")
    assert mfm["skills"] == ["squads", "greeting", "sq-memory"]
