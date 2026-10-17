"""The item model keeps every non-core frontmatter key in one flat attribute mapping and writes
it back flat: a table over key shapes crossing load, write, the index and the typed accessors."""

from datetime import UTC, datetime
from typing import Any

import pytest

from squads._models import _attributes as attrs
from squads._models._attributes import CORE_KEYS, AttributeKey
from squads._models._index import SquadsDB
from squads._models._item import Item

_NOW = datetime(2026, 1, 1, tzinfo=UTC)
_PATH = "guides/GUIDE-000001-a-guide.md"


def _frontmatter(**extra: Any) -> dict[str, Any]:
    return {
        "id": "GUIDE-1",
        "sequence_id": 1,
        "type": "guide",
        "title": "A guide",
        "status": "Draft",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        **extra,
    }


def _load(data: dict[str, Any]) -> Item:
    return Item.from_frontmatter(data, path=_PATH, default_kind="related")


#: (id, key, value): every shape a non-core key can take, declared or not.
KEY_SHAPES: list[tuple[str, str, Any]] = [
    ("declared-str", "tech", "python"),
    ("declared-list", "tags", ["a", "b"]),
    ("declared-with-a-wrong-kind", "tags", "a,b"),
    ("never-declared", "hand_key", "keep-me"),
    ("nested-mapping", "nested", {"a": {"b": 1}}),
    ("explicit-null", "nothing", None),
    ("bool", "flag", True),
    ("named-like-a-json-only-key", "badges", {"x": 1}),
    ("a-pasted-extra-block", "extra", {"slug": "x", "tech": "y"}),
]


@pytest.mark.parametrize(
    ("key", "value"), [(k, v) for _, k, v in KEY_SHAPES], ids=[i for i, _, _ in KEY_SHAPES]
)
def test_a_non_core_key_is_kept_flat_through_load_write_and_the_index(key: str, value: Any) -> None:
    item = _load(_frontmatter(**{key: value}))

    assert item.attributes == {key: value}
    written = item.to_frontmatter_dict()
    assert written[key] == value
    assert "attributes" not in written
    reloaded = _load(written)
    assert reloaded.attributes == {key: value}
    assert reloaded.to_frontmatter_dict() == written
    db = SquadsDB(counter=1)
    db.add(item)
    through_index = SquadsDB.model_validate_json(db.model_dump_json()).get(item.id)
    assert through_index is not None
    assert through_index.attributes == {key: value}
    assert through_index.to_frontmatter_dict() == written


def test_a_core_key_is_never_an_attribute_and_path_and_prefix_are_kept_as_unknown_keys() -> None:
    data = _frontmatter(labels=["x"], priority="high", path="stray/path.md", prefix="STRAY")
    item = _load(data)

    assert item.attributes == {"path": "stray/path.md", "prefix": "STRAY"}
    assert item.path == _PATH  # the model's own field is the file's location, not the key
    written = item.to_frontmatter_dict()
    assert written["path"] == "stray/path.md" and written["prefix"] == "STRAY"
    assert set(written) - {"path", "prefix"} <= set(CORE_KEYS)
    assert "path" not in item.to_row() or item.to_row()["path"] == _PATH


#: (id, frontmatter carries slug, roster item, expected slug, slug written back)
SLUG_ROWS = [
    ("stored", True, False, "stored-slug", True),
    ("absent-from-the-file", False, False, "a-guide", False),
    ("a-roster-item-writes-it", False, True, "a-guide", True),
]


@pytest.mark.parametrize(
    ("carries", "roster", "expected", "written"),
    [r[1:] for r in SLUG_ROWS],
    ids=[r[0] for r in SLUG_ROWS],
)
def test_slug_is_read_from_the_file_when_present_and_written_for_roster_items_or_when_it_was_there(
    carries: bool, roster: bool, expected: str, written: bool
) -> None:
    data = _frontmatter(**({"slug": "stored-slug"} if carries else {}))
    item = _load(data)
    if roster:
        item = item.model_copy(update={"slug_in_file": True})

    assert item.slug == expected
    assert ("slug" in item.to_frontmatter_dict()) is written


#: (id, key, stored value, accessor, expected): a value of the wrong kind reads as unset.
ACCESSORS = [
    ("flag-true", AttributeKey.IS_DEV, True, attrs.is_dev, True),
    ("flag-as-a-string", AttributeKey.IS_DEV, "true", attrs.is_dev, False),
    ("flag-as-a-number", AttributeKey.IS_DEV, 1, attrs.is_dev, False),
    ("default-unset", AttributeKey.IS_DEFAULT, None, attrs.is_default, None),
    ("default-false", AttributeKey.IS_DEFAULT, False, attrs.is_default, False),
    ("default-as-a-string", AttributeKey.IS_DEFAULT, "yes", attrs.is_default, None),
    ("tech-str", AttributeKey.TECH, "go", attrs.tech, "go"),
    ("tech-as-a-list", AttributeKey.TECH, ["go"], attrs.tech, None),
    ("model-empty", AttributeKey.MODEL, "", attrs.model, None),
]


@pytest.mark.parametrize(
    ("key", "stored", "accessor", "expected"),
    [r[1:] for r in ACCESSORS],
    ids=[r[0] for r in ACCESSORS],
)
def test_a_typed_accessor_reads_a_value_of_the_wrong_kind_as_unset(
    key: str, stored: Any, accessor: Any, expected: Any
) -> None:
    item = _load(_frontmatter(**({} if stored is None else {key: stored})))

    assert accessor(item) == expected
