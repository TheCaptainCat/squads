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
    return Item(**{**base, **over})


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
