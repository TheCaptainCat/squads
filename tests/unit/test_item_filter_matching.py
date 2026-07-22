"""``ItemFilter`` is the one match predicate shared by both `list_items` and `tree_view` — proven
directly against `Item` values with no filesystem: each dimension alone, ANDed together, and the
empty-filter-matches-everything case. Priority stands in as the one worked badge-dimension
example; the underlying badge-value comparison itself is proven generically elsewhere.
"""

from datetime import UTC, datetime

from squads._models._item import Item
from squads._services._base import ItemFilter
from squads._workflow import bundled_spec

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _item(item_type: str = "task", **overrides: object) -> Item:
    fields: dict[str, object] = {
        "sequence_id": 1,
        "type": item_type,
        "prefix": "TASK",
        "title": "t",
        "slug": "t",
        "status": "Draft",
        "path": f"{item_type}s/x.md",
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    fields.update(overrides)
    return Item(**fields)  # type: ignore[arg-type]


def test_is_empty_true_with_no_fields_set_false_with_any_one_set():
    assert ItemFilter().is_empty() is True
    assert ItemFilter(item_type="task").is_empty() is False
    assert ItemFilter(status="Ready").is_empty() is False
    assert ItemFilter(assignee="qa").is_empty() is False
    assert ItemFilter(badges=(("priority", "high"),)).is_empty() is False
    assert ItemFilter(parent="FEAT-000001").is_empty() is False
    assert ItemFilter(label="urgent").is_empty() is False


def test_matches_type():
    task, feat = _item("task"), _item("feature")
    f = ItemFilter(item_type="task")
    assert f.matches(task) is True and f.matches(feat) is False


def test_matches_status():
    item = _item(status="Draft")
    assert ItemFilter(status="Draft").matches(item) is True
    assert ItemFilter(status="Ready").matches(item) is False


def test_matches_assignee():
    item = _item(assignee="manager")
    assert ItemFilter(assignee="manager").matches(item) is True
    assert ItemFilter(assignee="product-owner").matches(item) is False


def test_matches_badge_value_exactly():
    item = _item(priority="high")
    assert ItemFilter(badges=(("priority", "high"),)).matches(item) is True
    assert ItemFilter(badges=(("priority", "low"),)).matches(item) is False


def test_matches_is_the_and_of_every_set_dimension():
    item = _item("task", priority="high")
    assert ItemFilter(item_type="task", badges=(("priority", "high"),)).matches(item) is True
    assert ItemFilter(item_type="task", badges=(("priority", "low"),)).matches(item) is False
    assert ItemFilter(item_type="feature", badges=(("priority", "high"),)).matches(item) is False


def test_is_empty_false_with_category_set():
    assert ItemFilter(category="work").is_empty() is False


def test_matches_category_resolves_via_the_spec():
    spec = bundled_spec()
    task, decision, role = _item("task"), _item("decision"), _item("role")
    assert ItemFilter(category="work", spec=spec).matches(task) is True
    assert ItemFilter(category="work", spec=spec).matches(decision) is False
    assert ItemFilter(category="records", spec=spec).matches(decision) is True
    assert ItemFilter(category="roster", spec=spec).matches(role) is True
    assert ItemFilter(category="roster", spec=spec).matches(task) is False


def test_matches_category_without_a_spec_is_a_graceful_non_match():
    """No spec to resolve the type's category from — never a crash, just no match."""
    item = _item("task")
    assert ItemFilter(category="work").matches(item) is False


def test_matches_category_composes_with_other_dimensions():
    spec = bundled_spec()
    item = _item("task", priority="high")
    assert (
        ItemFilter(category="work", badges=(("priority", "high"),), spec=spec).matches(item) is True
    )
    assert (
        ItemFilter(category="records", badges=(("priority", "high"),), spec=spec).matches(item)
        is False
    )
