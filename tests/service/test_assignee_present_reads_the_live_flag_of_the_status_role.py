"""`assignee_present` reads the `live` flag of the role a status resolves to, never a role or a
status name. Driven over every state of each bundled lifecycle, over a role renamed by an
override, a role and status the project declares, a role named `active` that declares
`live = false`, and a status with no role; and over the assignee shapes.
"""

import pytest

from _helpers import create_item
from _selection_table import (
    ASSIGNEE_PRESENT,
    TypeRow,
    member_findings,
    override_toml,
    service_with,
)
from squads._services import _service as service
from squads._workflow import bundled_spec

pytestmark = pytest.mark.anyio

#: Bundled type -> the statuses of its lifecycle that resolve to a live role.
_LIVE: dict[str, frozenset[str]] = {
    "epic": frozenset({"InProgress", "InReview"}),
    "feature": frozenset({"InProgress", "InReview"}),
    "task": frozenset({"InProgress", "InReview"}),
    "bug": frozenset({"InProgress", "Fixed"}),
    "review": frozenset({"InReview", "ChangesRequested"}),
    "contract": frozenset({"Active"}),
    "milestone": frozenset({"InProgress"}),
}
_STATE_CELLS = [
    (type_name, status)
    for type_name in _LIVE
    for status in sorted(bundled_spec().machine_for(type_name).states)
]


async def _unassigned_at(svc: service.Service, item_type: str, status: str) -> str:
    item = (await create_item(svc, item_type, "t")).item
    await svc.update(item.id, status=status, force=True)
    return item.id


def _reported(issues, item_id: str) -> bool:
    return any(i == item_id for _, i, _ in member_findings(issues, ASSIGNEE_PRESENT))


@pytest.mark.parametrize(("item_type", "status"), _STATE_CELLS)
async def test_every_state_of_a_bundled_lifecycle_is_reported_exactly_when_its_role_is_live(
    project, item_type: str, status: str
) -> None:
    row = TypeRow(item_type, item_type)
    svc = service_with(project.squad_dir, override_toml(row, ("assignee_present",)))
    item_id = await _unassigned_at(svc, item_type, status)
    assert _reported(await svc.check(), item_id) is (status in _LIVE[item_type])


async def test_a_role_renamed_by_an_override_and_still_live_is_reported(project) -> None:
    toml = (
        '[roles.busy]\nsettled = false\ncolor = "positive"\nlive = true\n\n'
        '[statuses.InProgress]\nrole = "busy"\n\n'
        '[items.task]\nvalidators = ["assignee_present"]\n'
    )
    svc = service_with(project.squad_dir, toml)
    renamed = await _unassigned_at(svc, "task", "InProgress")
    kept = await _unassigned_at(svc, "task", "InReview")
    pending = await _unassigned_at(svc, "task", "Ready")
    issues = await svc.check()
    assert (_reported(issues, renamed), _reported(issues, kept), _reported(issues, pending)) == (
        True,
        True,
        False,
    )


_FLOW = (
    '[roles.busy]\nsettled = false\ncolor = "positive"\nlive = true\n\n'
    '[statuses.Todo2]\nrole = "pending"\n[statuses.Doing]\nrole = "busy"\n'
    '[statuses.Limbo]\n[statuses.Closed]\nrole = "done"\n\n'
    '[lifecycles.flow]\ninitial = "Todo2"\n\n'
    '[lifecycles.flow.transitions]\nTodo2 = ["Doing", "Limbo"]\nDoing = ["Closed"]\n'
    'Limbo = ["Closed"]\nClosed = []\n\n'
    '[items.incident]\nprefix = "INC"\nfolder = "incidents"\nlifecycle = "flow"\n'
    'aliases = ["inc"]\ncategory = "work"\norder = 66\nvalidators = ["assignee_present"]\n'
)


@pytest.mark.parametrize(
    ("status", "reported"),
    [("Todo2", False), ("Doing", True), ("Limbo", False), ("Closed", False)],
)
async def test_a_role_and_status_the_project_declares_are_read_by_the_flag(
    project, status: str, reported: bool
) -> None:
    svc = service_with(project.squad_dir, _FLOW)
    item_id = await _unassigned_at(svc, "incident", status)
    assert _reported(await svc.check(), item_id) is reported


async def test_a_role_named_active_that_declares_live_false_is_silent(project) -> None:
    toml = (
        '[roles.working]\nsettled = false\ncolor = "positive"\nlive = true\n\n'
        '[roles.active]\nsettled = false\ncolor = "positive"\nlive = false\n\n'
        '[statuses.Active]\nrole = "working"\n[statuses.Deprecated]\nrole = "active"\n\n'
        '[items.contract]\nvalidators = ["assignee_present"]\n'
    )
    svc = service_with(project.squad_dir, toml)
    live = await _unassigned_at(svc, "contract", "Active")
    named_active = await _unassigned_at(svc, "contract", "Deprecated")
    issues = await svc.check()
    assert (_reported(issues, live), _reported(issues, named_active)) == (True, False)


async def test_an_item_with_an_assignee_is_silent_whatever_kind_of_slug_it_holds(project) -> None:
    row = TypeRow("task", "task")
    svc = service_with(project.squad_dir, override_toml(row, ("assignee_present",)))
    await svc.add_operator("Alice Tester")
    held = {}
    for name, assignee in {"role": "manager", "operator": "op-alice"}.items():
        item = (await create_item(svc, "task", name, assignee=assignee)).item
        await svc.update(item.id, status="InProgress", force=True)
        held[name] = item.id
    cleared = (await create_item(svc, "task", "cleared", assignee="manager")).item
    await svc.update(cleared.id, status="InProgress", force=True)
    await svc.update(cleared.id, assignee="")
    unregistered = (await create_item(svc, "task", "ghost", assignee="manager")).item
    await svc.update(unregistered.id, status="InProgress", force=True)
    blank = (await create_item(svc, "task", "blank", assignee="manager")).item
    await svc.update(blank.id, status="InProgress", force=True)
    async with svc.store.transaction() as db:
        db.items[unregistered.sequence_id].assignee = "ghost"
        db.items[blank.sequence_id].assignee = ""

    issues = await svc.check()
    assert {name: _reported(issues, item_id) for name, item_id in held.items()} == {
        "role": False,
        "operator": False,
    }
    assert _reported(issues, cleared.id)
    assert _reported(issues, blank.id)
    assert not _reported(issues, unregistered.id)
    assert any("ghost" in i.message for i in issues if i.item == unregistered.id)
