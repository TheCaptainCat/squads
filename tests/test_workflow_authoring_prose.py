"""TASK-000279 — Spec-derive the role-to-type authoring prose in workflow.md.j2.

Covers:
- The `authoring_owner()` / `parent_chain()` helpers in `_interactions` (the spec-driven
  replacement for the hardcoded "Product owner -> features" / "Tech lead -> tasks" prose).
- The rendered authoring narrative changes when the underlying spec (parent chain, lane
  ownership) changes — proving the text is genuinely spec-derived, not a string coincidence.
- Graceful degradation: a type with no single in-lane owner (e.g. a custom type with no
  CREATE_LANES entry) is simply omitted from the authoring narrative rather than crashing
  or fabricating a guess.
- CLAUDE.md's own (separately-worded) Team workflow block picks up the same spec-derived
  role/type substitution.

Byte-identical bundled output is covered by tests/test_golden_rendered_output.py and
tests/test_workflow_renderer_261.py; this module focuses on genuine spec-derivation.
"""

from squads._interactions import authoring_owner, parent_chain
from squads._rendering._engine import render
from squads._workflow import bundled_spec
from squads._workflow._models import ItemSpec, WorkflowSpec

# ---------------------------------------------------------------------------
# authoring_owner() / parent_chain() unit behaviour
# ---------------------------------------------------------------------------


class TestAuthoringOwner:
    def test_feature_owner_is_product_owner(self) -> None:
        assert authoring_owner("feature") == ("product-owner", "product owner")

    def test_task_owner_is_tech_lead(self) -> None:
        assert authoring_owner("task") == ("tech-lead", "tech lead")

    def test_unknown_type_returns_none(self) -> None:
        assert authoring_owner("no-such-type") is None

    def test_type_with_no_lane_owner_returns_none(self) -> None:
        # role/skill/operator (meta types) and any custom type absent from CREATE_LANES
        # have no in-lane owner.
        assert authoring_owner("role") is None
        assert authoring_owner("incident") is None


class TestParentChain:
    def test_task_chain_is_epic_feature_task(self) -> None:
        assert parent_chain(bundled_spec(), "task") == ["epic", "feature", "task"]

    def test_feature_chain_is_epic_feature(self) -> None:
        assert parent_chain(bundled_spec(), "feature") == ["epic", "feature"]

    def test_epic_chain_is_just_epic(self) -> None:
        assert parent_chain(bundled_spec(), "epic") == ["epic"]

    def test_multi_parent_type_falls_back_to_itself(self) -> None:
        spec = bundled_spec()
        new_items = dict(spec.items)
        new_items["task"] = new_items["task"].model_copy(update={"parents": ["epic", "feature"]})
        multi_parent_spec = spec.model_copy(update={"items": new_items})
        assert parent_chain(multi_parent_spec, "task") == ["task"]


# ---------------------------------------------------------------------------
# The rendered narrative genuinely tracks the spec (not hardcoded strings)
# ---------------------------------------------------------------------------


def _spec_with_renamed_task_parent() -> WorkflowSpec:
    """Bundled spec plus a new 'initiative' type, with 'task' reparented onto it.

    All reserved built-in types (including 'feature') stay present — the spec forbids
    dropping them — but 'task's declared parent now points at the new type instead.
    Proves the authoring prose's parent name / prefix / hierarchy line come from the
    spec: if they were still hardcoded to "feature"/"FEAT", this substitution would go
    unnoticed.
    """
    base = bundled_spec()
    new_items = dict(base.items)
    new_items["initiative"] = base.items["feature"].model_copy(
        update={"prefix": "INIT", "folder": "initiatives", "aliases": [], "parents": ["epic"]}
    )
    new_items["task"] = new_items["task"].model_copy(
        update={"parents": ["initiative"], "parent_required": "initiative"}
    )
    new_prefix_to_type = dict(base.prefix_to_type)
    new_prefix_to_type["INIT"] = "initiative"
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


class TestAuthoringProseTracksSpec:
    def test_task_parent_name_and_prefix_follow_spec_rename(self) -> None:
        spec = _spec_with_renamed_task_parent()
        rendered = render("workflow.md.j2", spec=spec)
        assert "tasks under a initiative" in rendered or "tasks under a initiative," in rendered
        assert "--parent INIT-…" in rendered
        assert "the parent initiative" in rendered
        assert "no initiative parent" in rendered
        # The old hardcoded wording must be gone.
        assert "tasks under a feature" not in rendered
        assert "--parent FEAT-…" not in rendered

    def test_hierarchy_line_follows_spec_rename(self) -> None:
        spec = _spec_with_renamed_task_parent()
        rendered = render("workflow.md.j2", spec=spec)
        assert "Hierarchy: epic → initiative → task" in rendered

    def test_claude_section_task_parent_follows_spec_rename(self) -> None:
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


# ---------------------------------------------------------------------------
# Graceful omission when a type has no single in-lane owner
# ---------------------------------------------------------------------------


class TestGracefulOmission:
    def test_feature_bullet_omitted_when_subentity_kind_changes(self) -> None:
        """If 'feature' stops hosting 'story' sub-entities, the story-specific bullet
        is skipped rather than rendering a stale 'user stories' reference."""
        base = bundled_spec()
        new_items = dict(base.items)
        new_items["feature"] = new_items["feature"].model_copy(update={"subentity_kind": None})
        spec = base.model_copy(update={"items": new_items})
        rendered = render("workflow.md.j2", spec=spec)
        assert "Product owner** → features + their user stories" not in rendered

    def test_task_bullet_omitted_when_no_parent_required(self) -> None:
        base = bundled_spec()
        new_items = dict(base.items)
        new_items["task"] = new_items["task"].model_copy(update={"parent_required": None})
        spec = base.model_copy(update={"items": new_items})
        rendered = render("workflow.md.j2", spec=spec)
        assert "Tech lead** → tasks under a feature" not in rendered

    def test_custom_type_with_no_lane_owner_is_silently_skipped(self) -> None:
        """A custom type appears in the retype-target list (Part A) but does not force
        (or crash) an authoring bullet it has no declared owner for."""
        base = bundled_spec()
        new_items = dict(base.items)
        new_items["incident"] = ItemSpec(
            prefix="INC", folder="incidents", lifecycle=base.items["bug"].lifecycle
        )
        new_prefix_to_type = dict(base.prefix_to_type)
        new_prefix_to_type["INC"] = "incident"
        spec = WorkflowSpec.model_validate(
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
        rendered = render("workflow.md.j2", spec=spec)
        # Part A: the retype target list includes the custom type.
        assert "`incident`" in rendered.split("Valid targets:")[1].splitlines()[0]
        # Part B: no fabricated authoring bullet for a type with no lane owner.
        assert (
            "incident" not in rendered.split("## Type-command aliases")[0].split("Valid targets")[0]
        )
