"""The raw item/sub-entity Jinja templates (rendered directly, not through `sq show`): every
built-in item type's template renders the required `sq:body`/`sq:discussion` markers with a
leading '## Discussion' heading, the sub-entity block skeleton has no legacy `:meta` region and
nests its own discussion one heading level deeper, the review template's findings container
carries a severity legend that is spec-derived (a relabeled collection changes both the legend
and the CLI-hint text, not just the model), and a feature's scaffold hint tracks a renamed
sub-entity kind. This is the raw-template render path; `sq show`'s rendered CLI output is
proven independently in tests/cli/test_show_command_renders_body_and_subentities.py, and the
sub-entity head/summary *mechanism* (not the template skeleton) is proven in
tests/unit/test_subentity_head_and_summary_rendering.py.
"""

from datetime import UTC, datetime

import pytest

from _helpers import BUILTIN_TYPES
from squads import _discussion as discussion
from squads._models._item import Item
from squads._rendering._engine import render
from squads._workflow import bundled_spec

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _item(item_type: str, spec) -> Item:
    return Item(
        sequence_id=1,
        type=item_type,
        prefix=spec.items[item_type].prefix,
        title="Example",
        slug="example",
        status="Draft",
        path=f"{spec.items[item_type].folder}/x.md",
        created_at=_NOW,
        updated_at=_NOW,
        extra={"full_name": "Test Agent", "slug": "tester"},
    )


@pytest.mark.parametrize("item_type", list(BUILTIN_TYPES))
def test_every_builtin_type_template_renders_the_required_markers_and_heading(
    item_type: str,
) -> None:
    spec = bundled_spec()
    it = _item(item_type, spec)
    template_path = (
        f"agents/{item_type}.md.j2" if spec.item_is_meta(item_type) else f"items/{item_type}.md.j2"
    )
    out = render(template_path, item=it, description="", extra=it.extra, spec=spec)
    assert "<!-- sq:body -->" in out and "<!-- sq:body:end -->" in out
    assert "<!-- sq:discussion -->" in out and "<!-- sq:discussion:end -->" in out
    assert "## Discussion" in out
    assert out.index("## Discussion") < out.index("<!-- sq:discussion -->")


def test_subentity_block_skeleton_has_no_meta_region_and_nests_discussion_one_level_deeper() -> (
    None
):
    block = discussion.build_block("subtask", "ST1", "Validate")
    assert block == (
        "\n<!-- sq:subtask:ST1 -->\n### ST1 — Validate\n\n"
        "<!-- sq:subtask:ST1:head -->\n<!-- sq:subtask:ST1:head:end -->\n\n"
        "<!-- sq:subtask:ST1:body -->\n"
        "_Describe this subtask here — free-form paragraphs or bullet lists._\n"
        "<!-- sq:subtask:ST1:body:end -->\n\n"
        "#### Discussion\n\n"
        "<!-- sq:subtask:ST1:discussion -->\n<!-- sq:subtask:ST1:discussion:end -->\n"
        "<!-- sq:subtask:ST1:end -->\n"
    )
    assert ":meta" not in block
    assert "### ST1 —\n" in discussion.build_block("subtask", "ST1", "")  # blank title tolerated


def test_review_item_template_renders_a_findings_container_with_a_severity_legend() -> None:
    it = Item(
        sequence_id=1,
        type="review",
        title="Review",
        slug="review",
        status="Requested",
        path="reviews/x.md",
        created_at=_NOW,
        updated_at=_NOW,
    )
    out = render("items/review.md.j2", item=it, description="", extra={}, spec=bundled_spec())
    assert "<!-- sq:summary -->" in out and "<!-- sq:findings -->" in out
    assert "## Findings" in out
    for circle in ("🔴", "🟠", "🟡", "🟢", "🔵"):
        assert circle in out


def test_review_severity_legend_and_command_hint_are_spec_derived_not_hardcoded() -> None:
    """A project that relabels/re-values severity sees its own axis in the legend and the
    --severity hint, not the bundled critical/high/medium/low/info scale."""
    from squads._workflow._models import Badge, Collection, Field

    base = bundled_spec()
    impact_field = Field(code="severity", label="Impact", collection="impact", default="minor")
    finding = base.subentity_kinds["finding"].model_copy(update={"fields": [impact_field]})
    impact = Collection(
        label="Impact",
        ordered=True,
        default="minor",
        badges=[
            Badge(code="severe", label="Severe", emoji="🟣"),
            Badge(code="minor", label="Minor", emoji="⚪"),
        ],
    )
    spec = base.model_copy(
        update={
            "subentity_kinds": {**base.subentity_kinds, "finding": finding},
            "collections": {**base.collections, "impact": impact},
        }
    )
    it = Item(
        sequence_id=1,
        type="review",
        title="Review",
        slug="review",
        status="Requested",
        path="reviews/x.md",
        created_at=_NOW,
        updated_at=_NOW,
    )
    out = render("items/review.md.j2", item=it, description="", extra={}, spec=spec)
    assert "_Impact:_ 🟣 severe · ⚪ minor" in out
    assert "--severity minor" in out
    assert "critical" not in out


def test_feature_scaffold_hint_tracks_a_renamed_subentity_kind() -> None:
    """A project that renames its sub-entity kind (story->requirement) sees the real
    add-<kind>/<kind> command in the scaffold hint, not the bundled add-story/story."""
    base = bundled_spec()
    renamed_feature = base.items["feature"].model_copy(update={"subentity_kind": "requirement"})
    requirement_kind = base.subentity_kinds["story"]
    spec = base.model_copy(
        update={
            "items": {**base.items, "feature": renamed_feature},
            "subentity_kinds": {**base.subentity_kinds, "requirement": requirement_kind},
        }
    )
    it = Item(
        sequence_id=1,
        type="feature",
        title="Feature",
        slug="feature",
        status="Draft",
        path="features/x.md",
        created_at=_NOW,
        updated_at=_NOW,
    )
    out = render("items/feature.md.j2", item=it, description="", extra={}, spec=spec)
    assert "add-requirement" in out
    assert "requirement <n> update" in out
    assert "add-story" not in out
