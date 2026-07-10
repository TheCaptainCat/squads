"""The sub-entity head/summary-render mechanism (`_discussion.py`'s pure functions), proven
once against the spec-driven engine rather than per built-in kind: `build_block` scaffolds a
block with no legacy `:meta` region but a `:head` placeholder, `set_head` renders badges into
that region, and `render_summary` builds the roll-up table generically from declared fields —
degrading gracefully (never crashing) when a collection is dropped or a stored code is unknown.
"""

from squads import _badges as badges
from squads import _discussion as discussion
from squads import _sections as sections
from squads._models._subentity import SubEntity
from squads._workflow import bundled_spec
from squads._workflow._models import Field, SubentityKindSpec


def test_build_block_scaffolds_body_and_head_with_no_legacy_meta_region() -> None:
    block = discussion.build_block("finding", "F1", "Null deref")
    assert ":meta" not in block
    assert "<!-- sq:finding:F1:head -->" in block
    assert "<!-- sq:finding:F1:body -->" in block
    assert "### F1 — Null deref" in block


def test_build_block_uses_a_given_body_or_falls_back_to_the_kind_placeholder() -> None:
    block = discussion.build_block("subtask", "ST1", "Validate", body="custom body text")
    assert "custom body text" in block
    assert discussion.body_placeholder("subtask") not in block
    default = discussion.build_block("subtask", "ST1", "Validate")
    assert discussion.body_placeholder("subtask") in default


def test_set_head_renders_status_assignee_and_story_badges_into_the_empty_region() -> None:
    block = discussion.build_block("subtask", "ST1", "Validate")
    out = discussion.set_head(
        block,
        "subtask",
        "ST1",
        status="InProgress",
        assignee_name="Grace Hopper",
        story="US1 — Login",
    )
    head = sections.get_section(out, "subtask:ST1:head")
    assert head is not None
    assert "**Status:** 🟡 In Progress" in head
    assert "**Assignee:** Grace Hopper" in head
    assert "**Implements:** US1 — Login" in head


def test_render_summary_builds_the_roll_up_table_and_is_empty_for_no_sub_entities() -> None:
    subs = [
        SubEntity(local_id="F1", title="Null deref", status="Open", severity="high", assignee="qa")
    ]
    out = discussion.render_summary("finding", subs)
    assert "| Finding | Severity | Status | Assignee | Title |" in out
    assert "🟠 high" in out and "Open" in out and "qa" in out
    assert discussion.render_summary("finding", []) == ""


def test_severity_badge_and_summary_degrade_gracefully_when_the_collection_is_dropped() -> None:
    """A spec that dropped/renamed the severity collection never crashes — the raw code plus
    the neutral fallback badge, mirroring status_badge's graceful degradation."""
    spec = bundled_spec().model_copy(update={"collections": {}})
    coll = badges.resolve_collection("finding", "severity", spec)
    assert badges.badge_render(coll, "high", spec, as_label=True) == "⚪ High"

    subs = [SubEntity(local_id="F1", title="Null deref", status="Open", severity="high")]
    out = discussion.render_summary("finding", subs, spec)
    assert "⚪ high" in out  # emoji degrades; the raw code still renders, never crashes


def test_severity_badge_falls_back_for_a_code_no_longer_in_the_collection() -> None:
    """A stored code that isn't (or is no longer) a badge in the collection also degrades
    gracefully rather than raising a KeyError."""
    assert badges.badge_render("severity", "nonexistent", as_label=True) == "⚪ Nonexistent"


def test_custom_kind_summary_table_derives_one_column_per_declared_field() -> None:
    """A custom sub-entity kind's summary table gets one column per declared field, headed
    by its label, with no per-kind special-casing anywhere — severity is just the generic case."""
    base = bundled_spec()
    action = SubentityKindSpec(
        lifecycle="subentity",
        completion="Done",
        plural="actions",
        local_prefix="AC",
        fields=[Field(code="impact", label="Impact", collection="severity")],
    )
    spec = base.model_copy(update={"subentity_kinds": {**base.subentity_kinds, "action": action}})

    sub = SubEntity(local_id="AC1", title="Patch the leak", status="Todo")
    out = discussion.render_summary("action", [sub], spec)
    assert "| Action | Impact | Status | Assignee | Title |" in out
    assert "AC1" in out and "Patch the leak" in out
