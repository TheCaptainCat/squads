"""The bundled ``squads`` meta-skill's own generated content: priority guidance derives from
whichever collection is actually active (never falling back to a hardcoded priority list);
the ``create`` example lists only active work types; the direct-operator rule and the
full-comments/handle-vs-body briefings are present; and the sub-entity comment-scoping
convention is taught with a concrete example per sub-entity kind.
"""

import pytest

pytestmark = pytest.mark.anyio


def _squads_skill_body(project) -> str:
    return (project.squad_dir / "agents" / "skills" / "squads.md").read_text(encoding="utf-8")


async def test_priority_guidance_derives_from_the_active_collection_not_a_hardcoded_list(
    project,
):
    """A custom priority collection (renamed codes) must show up in the guidance verbatim —
    the skill must never fall back to the bundled urgent|high|medium|low literal."""
    from squads._services import _service as service
    from squads._workflow import bundled_spec
    from squads._workflow._models import Badge, Collection

    base = bundled_spec()
    custom = Collection(label="Priority", ordered=True, badges=[Badge(code="p0", label="P0")])
    spec = base.model_copy(update={"collections": {**base.collections, "priority": custom}})
    await service.Service(project, spec=spec).refresh_managed()
    body = _squads_skill_body(project)
    assert "p0" in body
    assert "urgent|high|medium|low" not in body


async def test_create_example_lists_only_active_work_types(project):
    from squads._services import _service as service
    from squads._workflow import bundled_spec

    base = bundled_spec()
    dropped = {k: v for k, v in base.items.items() if k != "guide"}
    spec = base.model_copy(update={"items": dropped})
    await service.Service(project, spec=spec).refresh_managed()
    body = _squads_skill_body(project)
    assert "guide" not in body.split("# also:")[1].splitlines()[0]


async def test_direct_operator_rule_is_present(project):
    body = _squads_skill_body(project)
    assert "Working directly with the operator" in body
    assert "never your chat" in body


async def test_teaches_full_comments_briefing_as_the_standard_dossier_move(project):
    body = _squads_skill_body(project)
    assert "--full --comments" in body
    assert "show --full --comments" in body


async def test_teaches_the_comment_scoping_convention_with_one_example_per_subentity_kind(
    project,
):
    body = _squads_skill_body(project)
    assert "Scope your comment to the right discussion" in body
    assert "story <k> comment" in body
    assert "subtask <k> comment" in body
    assert "finding <k> comment" in body
    assert "sq inbox" in body  # the no-gap-when-using-sub-entity-discussions rule


async def test_skill_drops_per_type_lifecycle_diagrams_but_keeps_hierarchy_and_table(project):
    """Agents read the skill as raw text — the ~200-line triplicated per-type
    ``stateDiagram-v2`` blocks are noise there (mermaid never renders). The small hierarchy
    ``flowchart TD`` and the one-line lifecycle table stay; ``sq workflow`` keeps the full
    per-type diagrams (covered separately)."""
    body = _squads_skill_body(project)
    assert "stateDiagram-v2" not in body
    assert "flowchart TD" in body
    assert "| Prefix | Type | Lifecycle |" in body
