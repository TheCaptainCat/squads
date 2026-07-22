"""A custom type participates in every generic item-lifecycle service operation exactly like a
built-in one: retype stamps the spec's own prefix/folder (never ``TYPE.upper()``), refs
add/remove/backref-lookup never ``KeyError`` on prefix resolution, ``sync`` auto-creates its
folder, and ``repair`` is a stable no-op over its items.
"""

from pathlib import Path

import pytest

from squads._itemfile import write_new
from squads._models._item import Item
from squads._services import _service as service
from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import ItemSpec, Lifecycle, WorkflowSpec

pytestmark = pytest.mark.anyio

_INCIDENT_TYPE = "incident"
_INCIDENT_PREFIX = "INC"
_INCIDENT_FOLDER = "incidents"

_OVERRIDE_TOML = """\
[lifecycles.triage]
initial = "Open"
[lifecycles.triage.transitions]
Open = ["Done", "WontFix"]
Done = []
WontFix = ["Open"]

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "triage"
"""


def _write_override(squad_dir: Path) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(_OVERRIDE_TOML, encoding="utf-8")


def _spec_with_incident() -> WorkflowSpec:
    base = load_workflow_spec()
    triage = Lifecycle(
        initial="Open", transitions={"Open": ["Done", "WontFix"], "Done": [], "WontFix": ["Open"]}
    )
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
        }
    )


async def _open_custom_svc(project) -> service.Service:
    _write_override(project.squad_dir)
    return service.open_service()


# --------------------------------------------------------------------------- retype


async def test_retype_to_a_custom_type_stamps_its_own_prefix_folder_and_file_name(
    project, frozen_time
) -> None:
    svc = await _open_custom_svc(project)
    task = (await svc.create("task", "A task to retype", author="manager")).item

    retyped = (await svc.retype(task.id, _INCIDENT_TYPE)).item

    assert retyped.prefix == _INCIDENT_PREFIX
    assert retyped.id.startswith(f"{_INCIDENT_PREFIX}-")
    assert not retyped.id.startswith("INCIDENT-")
    assert f"{_INCIDENT_FOLDER}/{_INCIDENT_PREFIX}-" in retyped.path
    assert (project.squad_dir / retyped.path).exists()

    reloaded = await svc.get(retyped.id)
    assert reloaded.type == _INCIDENT_TYPE and reloaded.prefix == _INCIDENT_PREFIX

    incidents = await svc.list_items(item_type=_INCIDENT_TYPE)
    assert [i.id for i in incidents] == [retyped.id]


# --------------------------------------------------------------------------- refs


async def test_ref_add_remove_and_backrefs_do_not_keyerror_for_a_custom_type_item(
    project, frozen_time
) -> None:
    svc = await _open_custom_svc(project)
    task = (await svc.create("task", "Task ref source", author="manager")).item
    bug = (await svc.create("bug", "A bug", author="manager")).item
    incident = (await svc.retype(bug.id, _INCIDENT_TYPE)).item

    added = await svc.add_ref(task.id, incident.id, kind="related")
    assert any(incident.id in r for r in added.refs)

    backrefs = await svc.refs_in(incident.id)
    assert any(bid == task.id for bid, _ in backrefs)

    removed = await svc.rm_ref(task.id, incident.id)
    assert not any(incident.id in r for r in removed.refs)


# --------------------------------------------------------------------------- sync / repair


async def test_sync_creates_the_spec_declared_folder_for_a_custom_type(project) -> None:
    svc = service.Service(project, spec=_spec_with_incident())
    incidents_folder = project.squad_dir / _INCIDENT_FOLDER
    assert not incidents_folder.exists()

    await svc.sync()
    assert incidents_folder.is_dir()


async def test_repair_is_a_stable_noop_for_a_squad_holding_a_custom_type_item(
    project, frozen_time
) -> None:
    """Repair-idempotency-after-a-variety-of-setups is proven generically at
    tests/integration/test_repair_integrity.py; a custom-type setup can't share that test's
    ``svc`` fixture (it needs its own overridden-spec Service), so it's proven here instead."""
    from squads import _clock as clock

    spec = _spec_with_incident()
    svc = service.Service(project, spec=spec)

    squad_rel = project.squad_relative(_INCIDENT_TYPE, "INC-000099-db-timeout.md", spec=spec)
    abs_path = project.abspath(squad_rel)
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
    await write_new(abs_path, item, "# DB timeout\n")
    async with svc.store.transaction() as db:
        if db.counter < 99:
            db.counter = 99

    first = await svc.repair()
    incident_id = "INC-000099"
    assert first.db.get(incident_id) is not None
    counter_after_first = first.db.counter

    second = await svc.repair()
    assert second.db.counter == counter_after_first
    assert second.db.get(incident_id) is not None
