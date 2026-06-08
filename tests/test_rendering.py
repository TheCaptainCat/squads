from datetime import UTC, datetime

import pytest

from squads.models import Item, ItemType, Status
from squads.rendering import render
from squads.service import _template_for


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
