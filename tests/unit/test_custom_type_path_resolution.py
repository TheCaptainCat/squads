"""Folder/prefix/id resolution is spec-only: built-in and custom types resolve through
the exact same code path, there is no reserved-map fast path and no ``type.upper()`` guessing —
every resolver either succeeds off the spec or raises/degrades to a loud sentinel, never a
plausible-but-wrong value.
"""

import pytest

from _helpers import BUILTIN_FOLDER, BUILTIN_PREFIX, BUILTIN_TYPES
from squads._errors import InvalidIdError, SquadsError
from squads._models._vocab import prefix_for
from squads._paths import SquadPaths, type_for_id
from squads._workflow import bundled_spec
from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import ItemSpec, Lifecycle, WorkflowSpec

_INCIDENT_TYPE = "incident"
_INCIDENT_PREFIX = "INC"
_INCIDENT_FOLDER = "incidents"

# A prefix containing a hyphen (legal per the workflow spec's own TOML-bare-key grammar) —
# every prefix-parsing consumer must be hyphen-safe, splitting on the LAST hyphen only.
_RUNBOOK_TYPE = "runbook"
_RUNBOOK_PREFIX = "RUN-BOOK"
_RUNBOOK_FOLDER = "runbooks"


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
            "roles": base.roles,
            "ref_kinds": base.ref_kinds,
            "views": base.views,
        }
    )


def _spec_with_runbook() -> WorkflowSpec:
    base = load_workflow_spec()
    triage = Lifecycle(initial="Open", transitions={"Open": ["Done"], "Done": []})
    return WorkflowSpec.model_validate(
        {
            "items": {
                **base.items,
                _RUNBOOK_TYPE: ItemSpec(
                    prefix=_RUNBOOK_PREFIX, folder=_RUNBOOK_FOLDER, lifecycle="triage"
                ),
            },
            "statuses": base.statuses,
            "lifecycles": {**base.lifecycles, "triage": triage},
            "prefix_to_type": {**base.prefix_to_type, _RUNBOOK_PREFIX: _RUNBOOK_TYPE},
            "alias_to_type": base.alias_to_type,
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
            "roles": base.roles,
            "ref_kinds": base.ref_kinds,
            "views": base.views,
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


def test_folder_for_raises_when_the_spec_does_not_declare_the_type(tmp_path) -> None:
    sp = _paths(tmp_path)
    with pytest.raises(SquadsError, match="unknown item type"):
        sp.folder_for("incident", spec=bundled_spec())


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


def test_squad_relative_raises_when_the_spec_does_not_declare_the_type(tmp_path) -> None:
    sp = _paths(tmp_path)
    with pytest.raises(SquadsError, match="unknown item type"):
        sp.squad_relative("incident", "INC-000001-title.md", spec=bundled_spec())


# --------------------------------------------------------------------------- type_for_id


def test_type_for_id_resolves_every_builtin_prefix_via_a_spec() -> None:
    spec = bundled_spec()
    for item_type, prefix in BUILTIN_PREFIX.items():
        assert type_for_id(f"{prefix}-000001", spec=spec) == item_type


def test_type_for_id_resolves_a_custom_prefix_via_its_spec() -> None:
    assert type_for_id(f"{_INCIDENT_PREFIX}-000001", spec=_spec_with_incident()) == _INCIDENT_TYPE


def test_type_for_id_resolves_a_hyphenated_custom_prefix_via_its_spec() -> None:
    """A prefix containing a hyphen must resolve by its LAST hyphen, not its first — splitting
    on the first would treat "RUN" as the prefix and "BOOK-000001" as the number."""
    assert type_for_id(f"{_RUNBOOK_PREFIX}-000001", spec=_spec_with_runbook()) == _RUNBOOK_TYPE


def test_type_for_id_raises_when_the_spec_does_not_declare_the_prefix() -> None:
    with pytest.raises(InvalidIdError, match="unknown ID prefix"):
        type_for_id("INC-000001", spec=bundled_spec())


def test_prefix_for_raises_when_the_spec_does_not_declare_the_type() -> None:
    with pytest.raises(SquadsError, match="unknown item type"):
        prefix_for("incident", bundled_spec())
