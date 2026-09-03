"""Per-item skill definition (``sq-<type>``) through the REAL service resolver
(``svc.skill_definition_text``, reading this squad's own live roster and active spec) — not the
render-mirror that tests/unit/test_item_skill_dev_gate.py uses to pin the golden: active-role
sections
reflect only actually-active roles; actor guidance is structured, not free prose; the dev
section is gated on an active ``*-dev`` role; the trailer names only the type's actual
sub-entity kind; the lifecycle description reflects an overridden status machine — and, the
sibling of the dropped-type no-crash family (tests/unit/test_dropped_type_authoring_prose_no_
crash.py), resolves to no definition at all, rather than crashing or naming a stale one, when
the type itself has been dropped from the active spec.

Also covers two per-item-skill content facts not explicitly numbered by the coverage ledger
but with no other home found (flagged in the chunk close-out): each active role's per-type
comment-scoping guidance names the right sub-entity command shape, and a sub-entity's title
guidance teaches "handle, not full description" consistently across story/subtask/finding.
"""

import pytest

from squads import _interactions as interactions

pytestmark = pytest.mark.anyio


async def _item_skill_body(svc, item_type: str) -> str:
    """The type's skill definition as this squad resolves it — the text ``sq skill sq-<type>
    show`` prints. Rendered on read, so *svc* must carry the spec/playbook under test."""
    return await svc.skill_definition_text(interactions.item_skill_name(item_type))


async def test_item_skills_are_generated_with_a_thin_claude_pointer_and_a_resolved_definition(
    svc, project
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
    feature = await _item_skill_body(svc, "feature")
    # 'minimal' roster (manager only) has no active role sections for feature.
    assert "## For " not in feature
    assert "add-story" in feature  # the generic command block is always present


async def test_active_role_sections_reflect_only_actually_active_roles(svc, project):
    await svc.activate_role("product-owner")
    await svc.activate_role("qa")
    await svc.refresh_managed()
    feature = await _item_skill_body(svc, "feature")
    assert "Nina Product" in feature
    assert "Olivia Lead" not in feature  # tech-lead never activated


async def test_actor_guidance_is_structured_not_free_prose(svc, project):
    await svc.add_dev("python")
    await svc.refresh_managed()
    task = await _item_skill_body(svc, "task")
    assert "## For developers" in task
    for label in ("**Enter**", "**Do:**", "**Hand off:**", "**Watch for:**"):
        assert label in task
    assert "acceptance criteria" in task
    assert "@reviewer" in task
    assert "don't author features/tasks" in task


async def test_the_dev_section_is_gated_on_an_active_dev_role(svc, project):
    assert "## For developers" not in await _item_skill_body(svc, "task")
    await svc.add_dev("rust")
    await svc.refresh_managed()
    assert "## For developers" in await _item_skill_body(svc, "task")


async def test_the_reviewers_section_carries_its_own_scope_discipline(svc, project):
    await svc.activate_role("reviewer")
    await svc.refresh_managed()
    task = await _item_skill_body(svc, "task")
    assert "Paul Reviewer" in task
    assert "don't fix the code yourself" in task


async def test_the_trailer_names_only_the_types_own_actual_subentity_kind(svc):
    feature = await _item_skill_body(svc, "feature")
    assert "Its stories\nget their bodies from `sq feature <n> story <k> body" in feature
    task = await _item_skill_body(svc, "task")
    assert "Its subtasks\nget their bodies from `sq task <n> subtask <k> body" in task
    review = await _item_skill_body(svc, "review")
    assert "Its findings\nget their bodies from `sq review <n> finding <k> body" in review
    for hostless in ("epic", "decision", "guide", "bug"):
        assert "get their bodies from" not in await _item_skill_body(svc, hostless)


async def test_lifecycle_line_reflects_an_overridden_status_machine(project):
    from squads._services import _service as service
    from squads._workflow import bundled_spec

    base = bundled_spec()
    overridden_task = base.items["task"].model_copy(update={"lifecycle": "guide"})
    spec = base.model_copy(update={"items": {**base.items, "task": overridden_task}})
    overridden = service.Service(project, spec=spec)
    task = await _item_skill_body(overridden, "task")
    lifecycle_line = next(ln for ln in task.splitlines() if ln.startswith("**Lifecycle:**"))
    assert lifecycle_line == "**Lifecycle:** Draft → Published → Deprecated"


async def test_a_dropped_type_resolves_to_no_definition_rather_than_crashing(project):
    """ "bug" (not task/feature/epic, which sit on workflow.md.j2's hardcoded parent-chain walk)
    is dropped here — its skill must resolve to nothing at all rather than crash on a lifecycle
    the active spec can no longer describe, and rather than name the type under its old entry.

    The playbook still carries a frozen ``bug`` entry, so this is exactly the case where a
    fallback onto playbook prose would produce a plausible-looking, permanently stale
    definition for a type this squad no longer has."""
    from squads._services import _service as service
    from squads._workflow import bundled_spec

    base = bundled_spec()
    dropped_items = {k: v for k, v in base.items.items() if k != "bug"}
    spec = base.model_copy(update={"items": dropped_items})
    dropped = service.Service(project, spec=spec)
    assert await _item_skill_body(dropped, "bug") == ""
    # The types the spec still declares are unaffected.
    assert "**Lifecycle:**" in await _item_skill_body(dropped, "task")


async def test_item_skills_teach_the_full_comments_briefing_in_their_enter_section(svc):
    await svc.add_dev("python")
    for it in interactions.managed_item_types():
        body = await _item_skill_body(svc, it)
        assert "--full --comments" in body, f"sq-{it} skill missing --full --comments briefing"
        assert "show --full --comments" in body


async def test_per_type_skills_carry_role_specific_scoped_comment_guidance(svc, project):
    await svc.activate_role("reviewer")
    await svc.activate_role("product-owner")
    await svc.activate_role("tech-lead")
    await svc.add_dev("python")
    await svc.refresh_managed()

    review = await _item_skill_body(svc, "review")
    assert "finding <k> comment" in review
    assert "comment-scoping convention" in review

    feature = await _item_skill_body(svc, "feature")
    assert "story <k> comment" in feature
    assert "comment-scoping convention" in feature

    task = await _item_skill_body(svc, "task")
    assert "subtask <k> comment" in task
    assert "comment-scoping convention" in task


async def test_subentity_title_guidance_teaches_handle_not_full_description_per_kind(svc, project):
    await svc.activate_role("reviewer")
    await svc.activate_role("product-owner")
    await svc.activate_role("tech-lead")
    await svc.refresh_managed()

    review = await _item_skill_body(svc, "review")
    assert "short handle" in review
    assert "full description goes in the finding body" in review
    assert "finding <k> body" in review

    feature = await _item_skill_body(svc, "feature")
    assert "user-story phrase" in feature
    assert "the acceptance criteria live there, not in the title" in feature
    assert "story <k> body" in feature

    task = await _item_skill_body(svc, "task")
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
    assert fm["skills"] == [
        "squads",
        "greeting",
        "sq-memory",
        "sq-epic",
        "sq-feature",
        "sq-contract",
        "sq-milestone",
    ]
    mfm, _ = _fm(project.root / ".claude" / "agents" / "manager.md")
    assert mfm["skills"] == ["squads", "greeting", "sq-memory"]
