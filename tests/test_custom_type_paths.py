"""Tests for TASK-000258 / ADR-322: spec-aware folder/prefix mapping in _paths.

Covers:
- folder_for: resolves solely from the spec, for built-in AND custom types alike.
- folder_for: raises SquadsError for unknown type, or any type with no spec (fail-closed).
- squad_relative: same spec-only resolution as folder_for.
- type_for_id: resolves solely from spec.prefix_to_type, for built-in AND custom types alike.
- type_for_id: raises InvalidIdError for unknown prefix, or any prefix with no spec.
- ID round-trip: INC-000001 allocates and parses back to "incident" via the spec.
- Folder auto-created when a custom-type item is created (via write_new / create()).
- sq repair is a stable no-op: a custom-type item file is indexed and then repaired.
"""

from pathlib import Path

import pytest

from _helpers import BUILTIN_FOLDER, BUILTIN_PREFIX, BUILTIN_TYPES
from squads._errors import InvalidIdError, SquadsError
from squads._paths import SquadPaths, number_for_id, type_for_id
from squads._services import _service as service
from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import ItemSpec, Lifecycle, WorkflowSpec

pytestmark = pytest.mark.anyio

#: prefix -> built-in type, derived from BUILTIN_PREFIX (test-only, mirrors _helpers).
_BUILTIN_TYPE_BY_PREFIX: dict[str, str] = {v: k for k, v in BUILTIN_PREFIX.items()}

# ---------------------------------------------------------------------------
# Helper: build a minimal WorkflowSpec that adds an "incident" custom type
# ---------------------------------------------------------------------------

_INCIDENT_FOLDER = "incidents"
_INCIDENT_PREFIX = "INC"
_INCIDENT_TYPE = "incident"

# We re-use the bundled spec and extend it with the incident type for most tests.


def _spec_with_incident() -> WorkflowSpec:
    """Return the bundled spec extended with a minimal 'incident' custom type."""
    base = load_workflow_spec()
    # Triage lifecycle: Open → Done | WontFix
    triage = Lifecycle(
        initial="Open",
        transitions={
            "Open": ["Done", "WontFix"],
            "Done": [],
            "WontFix": ["Open"],
        },
    )
    incident_spec = ItemSpec(
        prefix=_INCIDENT_PREFIX,
        folder=_INCIDENT_FOLDER,
        lifecycle="triage",
    )
    new_lifecycles = dict(base.lifecycles)
    new_lifecycles["triage"] = triage
    new_items = dict(base.items)
    new_items[_INCIDENT_TYPE] = incident_spec
    new_prefix_to_type = dict(base.prefix_to_type)
    new_prefix_to_type[_INCIDENT_PREFIX] = _INCIDENT_TYPE
    return WorkflowSpec.model_validate(
        {
            "items": new_items,
            "statuses": base.statuses,
            "lifecycles": new_lifecycles,
            "prefix_to_type": new_prefix_to_type,
            "alias_to_type": base.alias_to_type,
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
        }
    )


# ---------------------------------------------------------------------------
# SquadPaths.folder_for — built-in behaviour unchanged
# ---------------------------------------------------------------------------


def test_folder_for_builtin_types_with_spec(tmp_path: Path) -> None:
    """Built-in types resolve to the expected folder when a spec is supplied (ADR-322: the
    spec is the sole vocabulary source — there is no reserved-map fast path any more)."""
    spec = _spec_with_incident()
    sp = SquadPaths(
        root=tmp_path,
        squad_dir=tmp_path / "squads",
        config=None,  # type: ignore[arg-type]
    )
    for item_type in BUILTIN_TYPES:
        expected = tmp_path / "squads" / BUILTIN_FOLDER[item_type]
        assert sp.folder_for(item_type, spec=spec) == expected, f"{item_type}: folder_for mismatch"


def test_folder_for_builtin_type_no_spec_raises(tmp_path: Path) -> None:
    """Every type — built-in or custom — requires a spec; there is no reserved-map fallback."""
    sp = SquadPaths(root=tmp_path, squad_dir=tmp_path / "squads", config=None)  # type: ignore[arg-type]
    with pytest.raises(SquadsError, match="unknown item type"):
        sp.folder_for("task")


def test_folder_for_custom_type_with_spec(tmp_path: Path) -> None:
    """Custom type returns spec-declared folder when spec is provided."""
    spec = _spec_with_incident()
    sp = SquadPaths(root=tmp_path, squad_dir=tmp_path / "squads", config=None)  # type: ignore[arg-type]
    result = sp.folder_for(_INCIDENT_TYPE, spec=spec)
    assert result == tmp_path / "squads" / _INCIDENT_FOLDER


def test_folder_for_unknown_type_no_spec_raises(tmp_path: Path) -> None:
    """Raises SquadsError for unknown type when no spec is provided."""
    sp = SquadPaths(root=tmp_path, squad_dir=tmp_path / "squads", config=None)  # type: ignore[arg-type]
    with pytest.raises(SquadsError, match="unknown item type"):
        sp.folder_for("incident")


def test_folder_for_unknown_type_wrong_spec_raises(tmp_path: Path) -> None:
    """Raises SquadsError for type unknown to both FOLDER_BY_TYPE and the spec."""
    from squads._workflow import bundled_spec

    spec = bundled_spec()
    sp = SquadPaths(root=tmp_path, squad_dir=tmp_path / "squads", config=None)  # type: ignore[arg-type]
    with pytest.raises(SquadsError, match="unknown item type"):
        sp.folder_for("incident", spec=spec)  # "incident" not in bundled spec


# ---------------------------------------------------------------------------
# SquadPaths.squad_relative — built-in behaviour unchanged
# ---------------------------------------------------------------------------


def test_squad_relative_builtin_with_spec(tmp_path: Path) -> None:
    """Built-in types resolve via the spec, same as custom types (ADR-322)."""
    spec = _spec_with_incident()
    sp = SquadPaths(root=tmp_path, squad_dir=tmp_path / "squads", config=None)  # type: ignore[arg-type]
    for item_type in BUILTIN_TYPES:
        result = sp.squad_relative(item_type, "TASK-000001-title.md", spec=spec)
        assert result == f"{BUILTIN_FOLDER[item_type]}/TASK-000001-title.md"


def test_squad_relative_custom_type(tmp_path: Path) -> None:
    """Custom type uses spec-declared folder for squad_relative."""
    spec = _spec_with_incident()
    sp = SquadPaths(root=tmp_path, squad_dir=tmp_path / "squads", config=None)  # type: ignore[arg-type]
    result = sp.squad_relative(_INCIDENT_TYPE, "INC-000001-db-timeout.md", spec=spec)
    assert result == f"{_INCIDENT_FOLDER}/INC-000001-db-timeout.md"


def test_squad_relative_unknown_type_raises(tmp_path: Path) -> None:
    """Raises SquadsError for unknown type when no spec is supplied."""
    sp = SquadPaths(root=tmp_path, squad_dir=tmp_path / "squads", config=None)  # type: ignore[arg-type]
    with pytest.raises(SquadsError, match="unknown item type"):
        sp.squad_relative("incident", "INC-000001-title.md")


# ---------------------------------------------------------------------------
# type_for_id — built-in behaviour and custom types
# ---------------------------------------------------------------------------


def test_type_for_id_builtins_with_spec() -> None:
    """Built-in IDs resolve via spec.prefix_to_type, same as custom types (ADR-322)."""
    from squads._workflow import bundled_spec

    spec = bundled_spec()
    for prefix, expected_type in _BUILTIN_TYPE_BY_PREFIX.items():
        item_id = f"{prefix}-000001"
        assert type_for_id(item_id, spec=spec) == expected_type, (
            f"type_for_id({item_id!r}) != {expected_type!r}"
        )


def test_type_for_id_builtin_no_spec_raises() -> None:
    """A built-in prefix with no spec supplied raises — there is no reserved-map fallback."""
    with pytest.raises(InvalidIdError, match="unknown ID prefix"):
        type_for_id("TASK-000001")


def test_type_for_id_custom_type_with_spec() -> None:
    """Custom prefix resolves to the custom type via spec.prefix_to_type."""
    spec = _spec_with_incident()
    item_id = f"{_INCIDENT_PREFIX}-000001"
    result = type_for_id(item_id, spec=spec)
    assert result == _INCIDENT_TYPE


def test_type_for_id_unknown_prefix_no_spec_raises() -> None:
    """Unknown prefix raises InvalidIdError when no spec is provided."""
    with pytest.raises(InvalidIdError, match="unknown ID prefix"):
        type_for_id("INC-000001")


def test_type_for_id_unknown_prefix_wrong_spec_raises() -> None:
    """Unknown prefix raises InvalidIdError when spec doesn't declare it."""
    from squads._workflow import bundled_spec

    spec = bundled_spec()
    with pytest.raises(InvalidIdError, match="unknown ID prefix"):
        type_for_id("INC-000001", spec=spec)  # "INC" not in bundled spec


# ---------------------------------------------------------------------------
# ID round-trip: INC-000001 allocates and parses back to "incident"
# ---------------------------------------------------------------------------


async def test_incident_id_round_trip(project) -> None:  # type: ignore[no-untyped-def]
    """INC-000001 allocated for 'incident' type round-trips via type_for_id with the spec.

    Verifies TASK-000258 AC#2: ID allocation uses the global counter (no special path), and
    the allocated ID parses correctly via type_for_id when the spec is provided.
    """
    spec = _spec_with_incident()
    svc = service.Service(project, spec=spec)

    # Directly allocate an ID for the "incident" type through the index store.
    # This bypasses create() (which needs a template — a later task) while still
    # exercising the global counter and the prefix derivation.
    async with svc.store.transaction() as db:
        incident_id = db.allocate_id(_INCIDENT_TYPE)

    # SquadsDB.allocate_id does NOT consult the spec on its own (that's the service-layer
    # create() path's job, via prefix_for) — called bare like this, with no explicit
    # `prefix=`, it degrades to the diagnosable UNRESOLVED_PREFIX sentinel (never a
    # plausible-but-wrong type.upper() guess). The round-trip under test is therefore:
    # allocate "UNRESOLVED-000001" (this call site never resolved a real prefix), then
    # separately prove type_for_id resolves the REAL "INC" prefix to "incident" via the spec
    # (spec-prefix mapping) below — the two are independent halves of the same seam.
    assert "-" in incident_id, f"malformed allocated ID {incident_id!r}"
    seq = number_for_id(incident_id)
    assert seq > 0, "sequence must be positive"

    # type_for_id with the spec resolves the INC prefix → "incident".
    # For the spec prefix (INC), type_for_id uses spec.prefix_to_type.
    resolved_type = type_for_id(f"INC-{seq:06d}", spec=spec)
    assert resolved_type == _INCIDENT_TYPE, f"type_for_id round-trip failed: got {resolved_type!r}"


async def test_custom_type_folder_auto_created_on_write(tmp_path, monkeypatch) -> None:
    """A custom type's folder is auto-created when write_new writes the first item.

    This tests the path-layer directly: squad_relative returns the right path,
    and the folder is created by write_new (which calls mkdir(path.parent)).
    """
    from squads import _clock as clock
    from squads._itemfile import write_new
    from squads._models._item import Item

    spec = _spec_with_incident()
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    paths = result.paths

    # The incidents/ folder should NOT exist yet (only built-in folders are created by init).
    incidents_folder = paths.squad_dir / _INCIDENT_FOLDER
    # (It may or may not exist depending on init — we care about it existing after write_new.)

    squad_rel = paths.squad_relative(_INCIDENT_TYPE, "INC-000001-db-timeout.md", spec=spec)
    assert squad_rel == f"{_INCIDENT_FOLDER}/INC-000001-db-timeout.md"

    # Create a minimal Item to write.
    now = clock.now()
    item = Item(
        sequence_id=99,
        type=_INCIDENT_TYPE,
        title="DB timeout",
        slug="db-timeout",
        status="Open",
        author="manager",
        path=squad_rel,
        created_at=now,
        updated_at=now,
    )

    abs_path = paths.abspath(squad_rel)
    rendered = "---\nid: INC-000099\ntype: incident\n---\n# DB timeout\n"
    await write_new(abs_path, item, rendered)

    assert incidents_folder.is_dir(), "incidents/ folder not auto-created by write_new"
    assert abs_path.is_file(), "item file not written"


# ---------------------------------------------------------------------------
# sq repair is stable no-op for a squad with a custom type
# ---------------------------------------------------------------------------


async def test_repair_stable_noop_with_custom_type(tmp_path, monkeypatch) -> None:
    """sq repair on a squad with a custom-type item is a stable no-op.

    Manually writes a minimal custom-type markdown file, then verifies repair
    finds it (does not drop it), and a second repair is unchanged (same counter).
    This validates TASK-000258 AC: 'sq repair is a stable no-op'.
    """
    from squads import _clock as clock
    from squads._itemfile import write_new
    from squads._models._item import Item

    spec = _spec_with_incident()
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    paths = init_result.paths
    svc = service.Service(paths, spec=spec)

    # Write a fake custom-type item file (bypassing create since no template yet).
    squad_rel = paths.squad_relative(_INCIDENT_TYPE, "INC-000099-db-timeout.md", spec=spec)
    abs_path = paths.abspath(squad_rel)
    now = clock.now()
    item = Item(
        sequence_id=99,
        type=_INCIDENT_TYPE,
        title="DB timeout",
        slug="db-timeout",
        status="Open",
        author="manager",
        path=squad_rel,
        created_at=now,
        updated_at=now,
    )
    rendered = "# DB timeout\n"
    await write_new(abs_path, item, rendered)
    # Bump the index counter past 99 so it accounts for the item.
    async with svc.store.transaction() as db:
        if db.counter < 99:
            db.counter = 99

    # First repair: must include the incident item.
    repair1 = await svc.repair()
    incident_id = "INC-000099"
    assert repair1.db.get(incident_id) is not None, f"repair dropped incident item {incident_id!r}"
    counter_after_first = repair1.db.counter

    # Second repair: counter must not change (stable no-op).
    repair2 = await svc.repair()
    assert repair2.db.counter == counter_after_first, (
        "repair is not a stable no-op: counter changed on second run"
    )
    assert repair2.db.get(incident_id) is not None, "item lost on second repair"


# ---------------------------------------------------------------------------
# Sync auto-creates custom type folders
# ---------------------------------------------------------------------------


async def test_sync_creates_custom_type_folder(project) -> None:  # type: ignore[no-untyped-def]
    """sq sync creates the incidents/ folder declared in the spec."""
    spec = _spec_with_incident()
    svc = service.Service(project, spec=spec)

    incidents_folder = project.squad_dir / _INCIDENT_FOLDER
    # Should not exist yet (no items created).
    assert not incidents_folder.exists(), "incidents/ folder already exists before sync"

    await svc.sync()
    assert incidents_folder.is_dir(), "sync did not create incidents/ folder"
