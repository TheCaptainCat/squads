from datetime import UTC, datetime

import pytest

from squads._models._enums import ItemType, Status
from squads._models._item import Item
from squads._rendering._engine import render
from squads._services._base import (
    _template_for,  # pyright: ignore[reportPrivateUsage]  # tests probe internals
)


@pytest.mark.parametrize("item_type", list(ItemType))
def test_every_type_template_renders_with_markers(item_type):
    now = datetime(2026, 1, 1, tzinfo=UTC)
    it = Item(
        id=f"{item_type.prefix}-000001",
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

    for block in (d.build_story_block("US1", "Login"), d.build_subtask_block("ST1", "Validate")):
        assert "#### Discussion" in block  # one level below the ### story/subtask heading
        assert block.index("#### Discussion") < block.index(":discussion -->")


def test_review_has_findings_container_and_summary_region():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    it = Item(
        id="REV-000001",
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
