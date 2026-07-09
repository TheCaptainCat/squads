from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from squads._models._config import SquadsConfig
from squads._models._enums import Severity
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._models._subentity import SubEntity

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _item(**over):
    base = dict(
        sequence_id=1,
        type="task",
        title="t",
        slug="t",
        status="Draft",
        path="tasks/x.md",
        created_at=_NOW,
        updated_at=_NOW,
    )
    return Item(**{**base, **over})  # pyright: ignore[reportArgumentType]  # dynamic test factory


def test_item_requires_non_empty_title_slug_path():
    for field in ("title", "slug", "path"):
        with pytest.raises(ValidationError):
            _item(**{field: ""})


def test_item_id_is_derived_from_sequence_and_type():
    # An explicit prefix is always required for a real id; Item.id itself never derives real
    # vocabulary (that would need a spec/_workflow import, breaking the acyclic invariant).
    assert _item(sequence_id=7, type="task", prefix="TASK").id == "TASK-7"
    assert _item(sequence_id=42, type="review", prefix="REV").id == "REV-42"


def test_item_id_without_prefix_degrades_to_unresolved_sentinel():
    """With no prefix set, Item.id degrades to the loud UNRESOLVED_PREFIX sentinel — never a
    type.upper() guess, even for a type like 'task' where that would coincidentally look
    right."""
    from squads._models._item import UNRESOLVED_PREFIX

    assert _item(sequence_id=7, type="task").id == f"{UNRESOLVED_PREFIX}-7"


def test_subentity_roundtrips_through_frontmatter():
    sub = SubEntity(
        local_id="F1",
        title="Null deref",
        status="Open",
        assignee="qa",
        severity=Severity.HIGH,
    )
    data = sub.to_frontmatter_dict()
    # enums serialize to their string values; None fields (here: story) are omitted
    assert data == {
        "local_id": "F1",
        "title": "Null deref",
        "status": "Open",
        "assignee": "qa",
        "severity": "high",
    }
    back = SubEntity.from_frontmatter(data)
    assert back == sub
    assert back.status == "Open" and back.severity is Severity.HIGH


def test_item_subentities_roundtrip_through_frontmatter():
    it = _item(
        type="task",
        subentities=[SubEntity(local_id="ST1", title="Wire", status="Todo", story="US1")],
    )
    fm = it.to_frontmatter_dict()
    assert fm["subentities"] == [
        {"local_id": "ST1", "title": "Wire", "status": "Todo", "story": "US1"}
    ]
    rebuilt = Item.from_frontmatter(fm, path=it.path)
    assert rebuilt.subentities == it.subentities
    # an item with no sub-entities omits the key entirely
    assert "subentities" not in _item().to_frontmatter_dict()


def test_item_accepts_empty_description_and_collections():
    it = _item(description="")
    assert it.labels == [] and it.refs == [] and it.extra == {}


def test_db_counter_non_negative():
    with pytest.raises(ValidationError):
        SquadsDB(counter=-1)
    assert SquadsDB(counter=0).counter == 0


def test_config_rejects_empty_squad_dir():
    with pytest.raises(ValidationError):
        SquadsConfig(squad_dir="")
    assert SquadsConfig(squad_dir="squads").squad_dir == "squads"


def test_from_frontmatter_folds_legacy_ref_kinds():
    # pre-2 on-disk shape: refs as bare IDs + a parallel extra.ref_kinds map
    data = {
        "id": "TASK-000001",
        "sequence_id": 1,
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
