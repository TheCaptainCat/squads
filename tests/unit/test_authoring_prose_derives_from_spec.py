"""``authoring_owner``/``parent_chain`` (the spec-driven replacement for hardcoded "product
owner -> features" prose), and proof the rendered authoring narrative genuinely tracks the
spec rather than a string coincidence: renaming a type's parent changes its parent name,
prefix, and hierarchy line everywhere (including CLAUDE.md's own wording); a bullet is
gracefully omitted (not fabricated) when a type has no single in-lane owner or its
sub-entity/parent requirement changes.
"""

from squads._interactions import authoring_owner, parent_chain
from squads._rendering._engine import render
from squads._workflow import bundled_spec
from squads._workflow._models import ItemSpec, WorkflowSpec


def test_authoring_owner_resolves_the_lane_owning_role_per_type() -> None:
    assert authoring_owner("feature") == ("product-owner", "product owner")
    assert authoring_owner("task") == ("tech-lead", "tech lead")


def test_authoring_owner_returns_none_for_an_unknown_or_ownerless_type() -> None:
    assert authoring_owner("no-such-type") is None
    assert authoring_owner("role") is None  # meta type
    assert authoring_owner("incident") is None  # a hypothetical custom type, absent from lanes


def test_parent_chain_derives_the_authoring_hierarchy() -> None:
    spec = bundled_spec()
    assert parent_chain(spec, "task") == ["epic", "feature", "task"]
    assert parent_chain(spec, "feature") == ["epic", "feature"]
    assert parent_chain(spec, "epic") == ["epic"]


def test_parent_chain_falls_back_to_itself_when_more_than_one_parent_is_possible() -> None:
    spec = bundled_spec()
    new_items = dict(spec.items)
    new_items["task"] = new_items["task"].model_copy(update={"parents": ["epic", "feature"]})
    multi_parent_spec = spec.model_copy(update={"items": new_items})
    assert parent_chain(multi_parent_spec, "task") == ["task"]


def _spec_with_renamed_task_parent() -> WorkflowSpec:
    """The bundled spec plus a new 'initiative' type, with 'task' reparented onto it (all
    reserved built-ins, including 'feature', stay present — only task's declared parent
    changes)."""
    base = bundled_spec()
    new_items = dict(base.items)
    new_items["initiative"] = base.items["feature"].model_copy(
        update={"prefix": "INIT", "folder": "initiatives", "aliases": [], "parents": ["epic"]}
    )
    new_items["task"] = new_items["task"].model_copy(
        update={"parents": ["initiative"], "parent_required": "initiative"}
    )
    new_prefix_to_type = {**base.prefix_to_type, "INIT": "initiative"}
    return WorkflowSpec.model_validate(
        {
            "items": new_items,
            "statuses": base.statuses,
            "lifecycles": base.lifecycles,
            "prefix_to_type": new_prefix_to_type,
            "alias_to_type": base.alias_to_type,
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
        }
    )


def test_the_rendered_hierarchy_line_and_parent_flag_track_a_spec_level_parent_rename() -> None:
    spec = _spec_with_renamed_task_parent()
    rendered = render("workflow.md.j2", spec=spec)
    assert "--parent INIT-…" in rendered
    assert "Hierarchy: epic → initiative → task" in rendered
    assert "--parent FEAT-…" not in rendered
    assert "epic → feature → task" not in rendered


def test_the_claude_md_section_also_tracks_the_same_parent_rename() -> None:
    spec = _spec_with_renamed_task_parent()
    rendered = render(
        "claude/claude_section.md.j2",
        squad_dir="squads",
        roles=[],
        operators=[],
        default_role_full_name="Catherine Manager",
        default_role_slug="manager",
        spec=spec,
    )
    assert "parent is the initiative" in rendered
    assert "--parent INIT-…" in rendered
    assert "parent is the feature" not in rendered


def test_a_bullet_is_omitted_not_fabricated_when_its_subentity_or_parent_requirement_drops() -> (
    None
):
    base = bundled_spec()
    no_story = base.model_copy(
        update={
            "items": {
                **base.items,
                "feature": base.items["feature"].model_copy(update={"subentity_kind": None}),
            }
        }
    )
    rendered = render("workflow.md.j2", spec=no_story)
    assert "add-story" not in rendered
    assert "**Product owner** → `sq create feature" in rendered  # bullet itself stays

    no_parent = base.model_copy(
        update={
            "items": {
                **base.items,
                "task": base.items["task"].model_copy(update={"parent_required": None}),
            }
        }
    )
    rendered2 = render("workflow.md.j2", spec=no_parent)
    assert "--parent FEAT-…" not in rendered2
    assert "**Tech lead** → `sq create task" in rendered2


def test_a_custom_type_with_no_lane_owner_is_silently_skipped_not_crashed() -> None:
    base = bundled_spec()
    new_items = dict(base.items)
    new_items["incident"] = ItemSpec(
        prefix="INC", folder="incidents", lifecycle=base.items["bug"].lifecycle
    )
    spec = WorkflowSpec.model_validate(
        {
            "items": new_items,
            "statuses": base.statuses,
            "lifecycles": base.lifecycles,
            "prefix_to_type": {**base.prefix_to_type, "INC": "incident"},
            "alias_to_type": base.alias_to_type,
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
        }
    )
    rendered = render("workflow.md.j2", spec=spec)
    # Part A (retype target list) includes the custom type...
    assert "`incident`" in rendered.split("Valid targets:")[1].splitlines()[0]
    # ...but no fabricated authoring bullet is generated for a type with no lane owner.
    authoring_section = rendered.split("## Type-command aliases")[0].split("Valid targets")[0]
    assert "incident" not in authoring_section
