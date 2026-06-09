from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from squads._models._config import SquadsConfig
from squads._models._enums import ItemType, Status
from squads._models._index import SquadsDB
from squads._models._item import Item

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _item(**over):
    base = dict(
        id="TASK-000001",
        type=ItemType.TASK,
        title="t",
        slug="t",
        status=Status.DRAFT,
        path="tasks/x.md",
        created_at=_NOW,
        updated_at=_NOW,
    )
    return Item(**{**base, **over})  # pyright: ignore[reportArgumentType]  # dynamic test factory


def test_item_requires_non_empty_id_title_slug_path():
    for field in ("id", "title", "slug", "path"):
        with pytest.raises(ValidationError):
            _item(**{field: ""})


def test_item_accepts_empty_description_and_collections():
    it = _item(description="")
    assert it.labels == [] and it.refs == [] and it.extra == {}


def test_db_counter_non_negative_and_schema_version_positive():
    with pytest.raises(ValidationError):
        SquadsDB(counter=-1)
    with pytest.raises(ValidationError):
        SquadsDB(schema_version=0)
    assert SquadsDB(counter=0).counter == 0


def test_config_rejects_empty_squad_dir():
    with pytest.raises(ValidationError):
        SquadsConfig(squad_dir="")
    assert SquadsConfig(squad_dir="squads").squad_dir == "squads"


def test_from_frontmatter_folds_legacy_ref_kinds():
    # pre-2 on-disk shape: refs as bare IDs + a parallel extra.ref_kinds map
    data = {
        "id": "TASK-000001",
        "type": "task",
        "title": "t",
        "status": "Draft",
        "refs": ["GUIDE-000002", "BUG-000003"],
        "extra": {"ref_kinds": {"BUG-000003": "fixes"}, "tech": "py"},
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    it = Item.from_frontmatter(data, path="tasks/t.md")
    assert it.refs == ["GUIDE-000002", "BUG-000003:fixes"]  # folded inline (default stays bare)
    assert "ref_kinds" not in it.extra  # legacy key dropped
    assert it.extra == {"tech": "py"}  # other extras preserved


def test_schema_version_constant_is_single_source():
    from squads._models._schema import SCHEMA_VERSION

    assert SquadsDB().schema_version == SCHEMA_VERSION
    assert SquadsConfig().schema_version == SCHEMA_VERSION


def test_inline_ref_helpers():
    from squads._models._item import make_ref, split_ref

    assert split_ref("ADR-000001") == ("ADR-000001", "related")
    assert split_ref("ADR-000001:implements") == ("ADR-000001", "implements")
    assert make_ref("ADR-000001") == "ADR-000001"  # default kind → bare
    assert make_ref("ADR-000001", "implements") == "ADR-000001:implements"
