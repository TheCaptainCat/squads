from datetime import UTC, datetime

import pytest

from _helpers import BUILTIN_TYPES
from squads._models._item import Item
from squads._rendering._engine import render
from squads._workflow import bundled_spec


@pytest.mark.parametrize("item_type", list(BUILTIN_TYPES))
def test_every_type_template_renders_with_markers(item_type):
    now = datetime(2026, 1, 1, tzinfo=UTC)
    spec = bundled_spec()
    it = Item(
        sequence_id=1,
        type=item_type,
        prefix=spec.items[item_type].prefix,
        title="Example",
        slug="example",
        status="Draft",
        path=f"{spec.items[item_type].folder}/x.md",
        created_at=now,
        updated_at=now,
        extra={"full_name": "Test Agent", "slug": "tester"},
    )
    # Delegate to the real WorkflowSpec.item_is_meta — same call ServiceCore._template_for
    # makes — so any new template branch in the production method will break this test.
    type_str = str(item_type)
    is_meta = spec.item_is_meta(type_str)
    template_path = f"agents/{type_str}.md.j2" if is_meta else f"items/{type_str}.md.j2"
    out = render(template_path, item=it, description="", extra=it.extra, spec=spec)
    assert "<!-- sq:body -->" in out and "<!-- sq:body:end -->" in out
    assert "<!-- sq:discussion -->" in out and "<!-- sq:discussion:end -->" in out
    # a top-level (h2) Discussion heading leads the discussion region
    assert "## Discussion" in out
    assert out.index("## Discussion") < out.index("<!-- sq:discussion -->")


def test_nested_discussions_get_h4_heading():
    from squads import _discussion as d

    for block in (d.build_block("story", "US1", "Login"), d.build_block("subtask", "ST1", "Go")):
        assert "#### Discussion" in block  # one level below the ### story/subtask heading
        assert block.index("#### Discussion") < block.index(":discussion -->")


def test_subentity_block_template_is_byte_exact():
    # the block skeleton comes from subentities/block.md.j2 — pin its exact output (markers, blank
    # lines, leading/trailing newline) so the parser/round-trips keep working. State is no longer in
    # the body (no :meta); the block ships an empty :head that set_head fills.
    from squads import _discussion as d

    assert d.build_block("subtask", "ST1", "Validate") == (
        "\n<!-- sq:subtask:ST1 -->\n### ST1 — Validate\n\n"
        "<!-- sq:subtask:ST1:head -->\n<!-- sq:subtask:ST1:head:end -->\n\n"
        "<!-- sq:subtask:ST1:body -->\n"
        "_Describe this subtask here — free-form paragraphs or bullet lists._\n"
        "<!-- sq:subtask:ST1:body:end -->\n\n"
        "#### Discussion\n\n"
        "<!-- sq:subtask:ST1:discussion -->\n<!-- sq:subtask:ST1:discussion:end -->\n"
        "<!-- sq:subtask:ST1:end -->\n"
    )
    # empty title keeps the bare "### ST1 —" heading
    assert "### ST1 —\n" in d.build_block("subtask", "ST1", "")
    # no machine state lives in the block body anymore
    assert ":meta" not in d.build_block("finding", "F1", "Null deref")


def test_head_partial_renders_attributes():
    # the extensible header partial: one bold line per set attribute, in order, blank when all unset
    out = render(
        "subentities/head.md.j2",
        status="🟡 In Progress",
        severity=None,
        story=None,
        assignee="Grace Hopper",
    )
    assert out == "**Status:** 🟡 In Progress\n**Assignee:** Grace Hopper\n"
    blank = render("subentities/head.md.j2", status=None, severity=None, story=None, assignee=None)
    assert blank.strip() == ""


def test_status_and_severity_badges():
    from squads import _badges as b

    assert b.status_badge("InProgress") == "🟡 In Progress"
    assert b.status_badge("WontFix") == "⚫ Wont Fix"
    assert b.badge_render("severity", "high", as_label=True) == "🟠 High"


def test_subentity_summary_template_layout():
    from squads import _discussion as d
    from squads._models._subentity import SubEntity

    subs = [
        SubEntity(
            local_id="F1",
            title="Null deref",
            status="Open",
            severity="high",
            assignee="qa",
        )
    ]
    out = d.render_summary("finding", subs)
    assert out.startswith("| Finding | Severity | Status | Assignee | Title |\n| --- | ")
    assert "| F1 | 🟠 high | Open | qa | Null deref |" in out
    assert d.render_summary("finding", []) == ""  # empty until there are rows


def test_review_has_findings_container_and_summary_region():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    it = Item(
        sequence_id=1,
        type="review",
        title="Review",
        slug="review",
        status="Requested",
        path="reviews/x.md",
        created_at=now,
        updated_at=now,
    )
    out = render("items/review.md.j2", item=it, description="", extra={}, spec=bundled_spec())
    # sq-managed summary region + the findings container (filled by `sq finding add`)
    assert "<!-- sq:summary -->" in out and "<!-- sq:findings -->" in out
    assert "## Findings" in out
    for circle in ("🔴", "🟠", "🟡", "🟢", "🔵"):
        assert circle in out  # severity legend


def test_review_legend_and_head_label_follow_a_relabeled_severity_collection():
    """A project that relabels/re-values severity sees its own axis in the review legend and
    the finding head badge, not the bundled critical/high/medium/low/info scale."""
    from squads import _discussion as d
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

    now = datetime(2026, 1, 1, tzinfo=UTC)
    it = Item(
        sequence_id=1,
        type="review",
        title="Review",
        slug="review",
        status="Requested",
        path="reviews/x.md",
        created_at=now,
        updated_at=now,
    )
    out = render("items/review.md.j2", item=it, description="", extra={}, spec=spec)
    assert "_Impact:_ 🟣 severe · ⚪ minor" in out
    assert "--severity minor" in out
    assert "critical" not in out  # bundled legend gone

    head = d.set_head(
        "<!-- sq:finding:F1:head -->\n<!-- sq:finding:F1:head:end -->",
        "finding",
        "F1",
        severity="minor",
        spec=spec,
    )
    assert "**Impact:** ⚪ Minor" in head


def test_feature_and_task_scaffold_hints_name_a_renamed_subentity_kind():
    """A project that renames its sub-entity kind (story->requirement) sees the real
    add-<kind>/<kind> command in the scaffold hint, not the bundled add-story/story."""
    base = bundled_spec()
    renamed_feature = base.items["feature"].model_copy(update={"subentity_kind": "requirement"})
    subentity_kinds = {**base.subentity_kinds, "requirement": base.subentity_kinds["story"]}
    items = {**base.items, "feature": renamed_feature}
    spec = base.model_copy(update={"items": items, "subentity_kinds": subentity_kinds})

    now = datetime(2026, 1, 1, tzinfo=UTC)
    it = Item(
        sequence_id=1,
        type="feature",
        title="Feature",
        slug="feature",
        status="Draft",
        path="features/x.md",
        created_at=now,
        updated_at=now,
    )
    out = render("items/feature.md.j2", item=it, description="", extra={}, spec=spec)
    assert "add-requirement" in out
    assert "requirement <n> update" in out
    assert "add-story" not in out
