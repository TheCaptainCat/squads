"""Folder/prefix/id resolution is spec-only: built-in and custom types resolve through
the exact same code path, there is no reserved-map fast path and no ``type.upper()`` guessing —
every resolver either succeeds off the spec or raises/degrades to a loud sentinel, never a
plausible-but-wrong value.
"""

from datetime import UTC, datetime

import pytest

from _helpers import BUILTIN_FOLDER, BUILTIN_PREFIX, BUILTIN_TYPES
from squads._errors import InvalidIdError, SquadsError
from squads._models._item import UNRESOLVED_PREFIX, Item, effective_prefix
from squads._models._vocab import prefix_for
from squads._paths import SquadPaths, type_for_id
from squads._workflow import bundled_spec
from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import ItemSpec, Lifecycle, WorkflowSpec

_INCIDENT_TYPE = "incident"
_INCIDENT_PREFIX = "INC"
_INCIDENT_FOLDER = "incidents"


def _spec_with_incident() -> WorkflowSpec:
    base = load_workflow_spec()
    triage = Lifecycle(initial="Open", transitions={"Open": ["Done"], "Done": []})
    return WorkflowSpec.model_validate(
        {
            "items": {
                **base.items,
                _INCIDENT_TYPE: ItemSpec(
                    prefix=_INCIDENT_PREFIX, folder=_INCIDENT_FOLDER, lifecycle="triage"
                ),
            },
            "statuses": base.statuses,
            "lifecycles": {**base.lifecycles, "triage": triage},
            "prefix_to_type": {**base.prefix_to_type, _INCIDENT_PREFIX: _INCIDENT_TYPE},
            "alias_to_type": base.alias_to_type,
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
        }
    )


def _paths(tmp_path) -> SquadPaths:
    return SquadPaths(root=tmp_path, squad_dir=tmp_path / "squads", config=None)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- folder_for


def test_folder_for_every_builtin_type_with_a_spec(tmp_path) -> None:
    spec = _spec_with_incident()
    sp = _paths(tmp_path)
    for item_type in BUILTIN_TYPES:
        expected = tmp_path / "squads" / BUILTIN_FOLDER[item_type]
        assert sp.folder_for(item_type, spec=spec) == expected


def test_folder_for_a_custom_type_with_a_spec(tmp_path) -> None:
    sp = _paths(tmp_path)
    result = sp.folder_for(_INCIDENT_TYPE, spec=_spec_with_incident())
    assert result == tmp_path / "squads" / _INCIDENT_FOLDER


@pytest.mark.parametrize(
    ("item_type", "spec"),
    [
        ("task", None),  # builtin, no spec at all
        ("incident", None),  # unknown, no spec at all
        ("incident", bundled_spec()),  # unknown, a real spec that just doesn't declare it
    ],
    ids=["builtin-no-spec", "unknown-no-spec", "unknown-wrong-spec"],
)
def test_folder_for_raises_when_the_type_has_no_resolvable_spec_entry(
    tmp_path, item_type: str, spec: WorkflowSpec | None
) -> None:
    sp = _paths(tmp_path)
    with pytest.raises(SquadsError, match="unknown item type"):
        sp.folder_for(item_type, spec=spec) if spec is not None else sp.folder_for(item_type)


# --------------------------------------------------------------------------- squad_relative


def test_squad_relative_resolves_builtin_and_custom_types_identically(tmp_path) -> None:
    spec = _spec_with_incident()
    sp = _paths(tmp_path)
    assert sp.squad_relative("task", "TASK-000001-title.md", spec=spec) == (
        f"{BUILTIN_FOLDER['task']}/TASK-000001-title.md"
    )
    assert sp.squad_relative(_INCIDENT_TYPE, "INC-000001-db-timeout.md", spec=spec) == (
        f"{_INCIDENT_FOLDER}/INC-000001-db-timeout.md"
    )


def test_squad_relative_raises_for_an_unknown_type_with_no_spec(tmp_path) -> None:
    sp = _paths(tmp_path)
    with pytest.raises(SquadsError, match="unknown item type"):
        sp.squad_relative("incident", "INC-000001-title.md")


# --------------------------------------------------------------------------- type_for_id


def test_type_for_id_resolves_every_builtin_prefix_via_a_spec() -> None:
    spec = bundled_spec()
    for item_type, prefix in BUILTIN_PREFIX.items():
        assert type_for_id(f"{prefix}-000001", spec=spec) == item_type


def test_type_for_id_resolves_a_custom_prefix_via_its_spec() -> None:
    assert type_for_id(f"{_INCIDENT_PREFIX}-000001", spec=_spec_with_incident()) == _INCIDENT_TYPE


@pytest.mark.parametrize(
    ("item_id", "spec"),
    [
        ("TASK-000001", None),  # builtin prefix, no spec at all
        ("INC-000001", None),  # unknown prefix, no spec at all
        ("INC-000001", bundled_spec()),  # unknown prefix, a real spec that doesn't declare it
    ],
    ids=["builtin-no-spec", "unknown-no-spec", "unknown-wrong-spec"],
)
def test_type_for_id_raises_when_the_prefix_has_no_resolvable_spec_entry(
    item_id: str, spec: WorkflowSpec | None
) -> None:
    with pytest.raises(InvalidIdError, match="unknown ID prefix"):
        type_for_id(item_id, spec=spec) if spec is not None else type_for_id(item_id)


# --------------------------------------------------------------------------- prefix_for (the
# reverse direction: type -> prefix, used at create/retype time)


def test_prefix_for_resolves_every_builtin_type_via_a_spec() -> None:
    spec = _spec_with_incident()
    for item_type, prefix in BUILTIN_PREFIX.items():
        assert prefix_for(item_type, spec) == prefix


def test_prefix_for_resolves_a_custom_type_via_its_spec() -> None:
    assert prefix_for(_INCIDENT_TYPE, _spec_with_incident()) == _INCIDENT_PREFIX


@pytest.mark.parametrize(
    ("item_type", "spec"),
    [
        ("task", None),
        ("incident", None),
        ("blork", _spec_with_incident()),
    ],
    ids=["builtin-no-spec", "unknown-no-spec", "unknown-wrong-spec"],
)
def test_prefix_for_raises_when_the_type_has_no_resolvable_spec_entry(
    item_type: str, spec: WorkflowSpec | None
) -> None:
    with pytest.raises(SquadsError, match="unknown item type"):
        prefix_for(item_type, spec) if spec is not None else prefix_for(item_type)


# --------------------------------------------------------------------------- effective_prefix —
# the shared stand-in used by every acyclic formatter (Item.id, format_id, ref matching) that
# has no spec in hand and cannot raise; never a type.upper() guess.


def test_effective_prefix_returns_the_prefix_when_set() -> None:
    assert effective_prefix("INC") == "INC"


def test_effective_prefix_degrades_to_the_unresolved_sentinel_when_unset() -> None:
    assert effective_prefix("") == UNRESOLVED_PREFIX


# --------------------------------------------------------------------------- Item.prefix is
# derived from the id string, for builtin AND custom types alike — never a persisted
# frontmatter key, and a stray legacy one is ignored, not trusted.


def _item(item_type: str, prefix: str, path: str) -> Item:
    now = datetime.now(UTC)
    return Item(
        sequence_id=7,
        type=item_type,
        prefix=prefix,
        title="t",
        slug="t",
        status="Draft",
        path=path,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.parametrize(
    ("item_type", "prefix", "path"),
    [("task", "TASK", "tasks/TASK-000007-t.md"), ("incident", "INC", "incidents/INC-000007-t.md")],
    ids=["builtin", "custom"],
)
def test_item_prefix_round_trips_through_frontmatter_via_id_never_persisted_directly(
    item_type: str, prefix: str, path: str
) -> None:
    original = _item(item_type, prefix, path)
    assert original.id == f"{prefix}-7"

    fm = original.to_frontmatter_dict()
    assert "prefix" not in fm  # nothing redundant left to persist

    reloaded = Item.from_frontmatter(fm, path=path)
    assert reloaded.prefix == prefix
    assert reloaded.id == original.id


def test_item_id_degrades_to_the_unresolved_sentinel_when_no_prefix_is_resolvable() -> None:
    """Never a type.upper() guess (which used to coincidentally look right for 'task' but
    silently mis-renders e.g. 'decision' as DECISION-N instead of ADR-N)."""
    item = Item(
        sequence_id=7,
        type="task",
        title="t",
        slug="t",
        status="Draft",
        path="tasks/TASK-000007-t.md",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    assert item.prefix == ""
    assert item.id == f"{UNRESOLVED_PREFIX}-7"


def test_a_stray_legacy_prefix_key_in_frontmatter_is_tolerated_but_never_trusted() -> None:
    """A file carrying a stray, disagreeing ``prefix:`` line (from an earlier, since-reverted
    build) still loads — the id: line, never the stray key, is the source of truth."""
    now = datetime.now(UTC).isoformat()
    data = {
        "id": "TASK-000007",
        "sequence_id": 7,
        "type": "task",
        "prefix": "WRONGPREFIX",
        "title": "t",
        "slug": "t",
        "status": "Draft",
        "created_at": now,
        "updated_at": now,
    }
    item = Item.from_frontmatter(data, path="tasks/TASK-000007-t.md")
    assert item.prefix == "TASK"
    assert item.id == "TASK-7"
