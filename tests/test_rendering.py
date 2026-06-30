from datetime import UTC, datetime

import pytest

from squads._models._enums import ItemType, Status
from squads._models._item import Item
from squads._rendering._engine import render
from squads._workflow import bundled_spec


def _template_for(item_type: str) -> str:
    """Probe helper: mirror ServiceCore._template_for using the bundled spec."""
    spec = bundled_spec()
    if spec.item_is_meta(str(item_type)):
        return f"agents/{item_type}.md.j2"
    return f"items/{item_type}.md.j2"


@pytest.mark.parametrize("item_type", list(ItemType))
def test_every_type_template_renders_with_markers(item_type):
    now = datetime(2026, 1, 1, tzinfo=UTC)
    it = Item(
        sequence_id=1,
        type=item_type,
        title="Example",
        slug="example",
        status=Status.DRAFT,
        path=f"{item_type.folder}/x.md",
        created_at=now,
        updated_at=now,
        extra={"full_name": "Test Agent", "slug": "tester"},
    )
    out = render(_template_for(item_type), item=it, description="", extra=it.extra)
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
    from squads import _discussion as d

    assert d._status_badge("InProgress") == "🟡 In Progress"  # pyright: ignore[reportPrivateUsage]
    assert d._status_badge("WontFix") == "⚫ Wont Fix"  # pyright: ignore[reportPrivateUsage]
    assert d._severity_badge("high") == "🟠 High"  # pyright: ignore[reportPrivateUsage]


def test_subentity_summary_template_layout():
    from squads import _discussion as d
    from squads._models._enums import Severity
    from squads._models._subentity import SubEntity

    subs = [
        SubEntity(
            local_id="F1",
            title="Null deref",
            status=Status.OPEN,
            severity=Severity.HIGH,
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
        type=ItemType.REVIEW,
        title="Review",
        slug="review",
        status=Status.REQUESTED,
        path="reviews/x.md",
        created_at=now,
        updated_at=now,
    )
    out = render("items/review.md.j2", item=it, description="", extra={})
    # sq-managed summary region + the findings container (filled by `sq finding add`)
    assert "<!-- sq:summary -->" in out and "<!-- sq:findings -->" in out
    assert "## Findings" in out
    for circle in ("🔴", "🟠", "🟡", "🟢", "🔵"):
        assert circle in out  # severity legend
