"""`blocked_has_blocker@error` at the write doors. Over the status and edge shapes, a write on an
item is refused exactly when `check()` on the resulting state reports it; moving an item to
Blocked is refused until a dependency edge exists, whether it is the item's own or another
item's pointing at it; `ref rm` is not gated, so removing the last edge leaves a state the next
gated write refuses; and at `warn` nothing is refused.
"""

import json

import pytest

from _helpers import create_item
from _selection_table import (
    BLOCKED_HAS_BLOCKER,
    TypeRow,
    member_findings,
    override_toml,
    service_with,
)
from squads._errors import SquadsError
from squads._services import _service as service
from squads._services import _validators as validators

pytestmark = pytest.mark.anyio

_TASK = TypeRow("task", "task")
_AT_ERROR = ("blocked_has_blocker@error",)
_MESSAGE = "no dependency edge is recorded"

#: (status, edge) -> whether the state is reported. The edge is where the dependency ref sits.
_SHAPES: dict[tuple[str, str], bool] = {
    ("Draft", "none"): False,
    ("InProgress", "none"): False,
    ("Blocked", "none"): True,
    ("Blocked", "own"): False,
    ("Blocked", "incoming"): False,
    ("Done", "none"): False,
}


async def _planted(svc: service.Service, status: str, edge: str) -> str:
    item = (await create_item(svc, "task", "t")).item
    other = (await create_item(svc, "task", "other")).item
    if edge == "own":
        await svc.add_ref(item.id, other.id, kind="depends-on")
    elif edge == "incoming":
        await svc.add_ref(other.id, item.id, kind="blocks")
    await svc.update(item.id, status=status, force=True)
    return item.id


@pytest.mark.parametrize(("status", "edge"), _SHAPES, ids=lambda v: str(v))
async def test_a_write_is_refused_exactly_when_check_reports_the_resulting_state(
    project, status: str, edge: str
) -> None:
    item_id = await _planted(
        service_with(project.squad_dir, override_toml(_TASK, ())), status, edge
    )
    svc = service_with(project.squad_dir, override_toml(_TASK, _AT_ERROR))
    reported = bool(member_findings(await svc.check(), BLOCKED_HAS_BLOCKER))
    assert reported is _SHAPES[(status, edge)]
    try:
        await svc.update(item_id, add_labels=["touched"])
    except SquadsError as err:
        assert reported
        assert _MESSAGE in str(err)
    else:
        assert not reported


@pytest.mark.parametrize("edge", ["own", "incoming"])
async def test_moving_to_blocked_is_refused_until_an_edge_exists_on_either_end(
    project, edge: str
) -> None:
    svc = service_with(project.squad_dir, override_toml(_TASK, _AT_ERROR))
    item = (await create_item(svc, "task", "t")).item
    other = (await create_item(svc, "task", "other")).item
    with pytest.raises(SquadsError, match=_MESSAGE):
        await svc.update(item.id, status="Blocked", force=True)
    if edge == "own":
        await svc.add_ref(item.id, other.id, kind="depends-on")
    else:
        await svc.add_ref(other.id, item.id, kind="blocks")
    moved = await svc.update(item.id, status="Blocked", force=True)
    assert moved.status == "Blocked"
    assert member_findings(await svc.check(), BLOCKED_HAS_BLOCKER) == []


async def test_leaving_blocked_is_accepted_for_an_item_with_no_edge(project) -> None:
    item_id = await _planted(
        service_with(project.squad_dir, override_toml(_TASK, ())), "Blocked", "none"
    )
    svc = service_with(project.squad_dir, override_toml(_TASK, _AT_ERROR))
    with pytest.raises(SquadsError, match=_MESSAGE):
        await svc.update(item_id, add_labels=["touched"])
    moved = await svc.update(item_id, status="InProgress", force=True)
    assert moved.status == "InProgress"


@pytest.mark.parametrize("edge", ["own", "incoming"])
async def test_removing_the_last_edge_is_not_gated_and_the_next_write_is_refused(
    project, edge: str
) -> None:
    svc = service_with(project.squad_dir, override_toml(_TASK, _AT_ERROR))
    item = (await create_item(svc, "task", "t")).item
    other = (await create_item(svc, "task", "other")).item
    if edge == "own":
        await svc.add_ref(item.id, other.id, kind="depends-on")
    else:
        await svc.add_ref(other.id, item.id, kind="blocks")
    await svc.update(item.id, status="Blocked", force=True)
    if edge == "own":
        await svc.rm_ref(item.id, other.id, kind="depends-on")
    else:
        await svc.rm_ref(other.id, item.id, kind="blocks")
    assert [i for _, i, _ in member_findings(await svc.check(), BLOCKED_HAS_BLOCKER)] == [item.id]
    with pytest.raises(SquadsError, match=_MESSAGE):
        await svc.update(item.id, add_labels=["touched"])
    await svc.add_ref(item.id, other.id, kind="depends-on")
    await svc.update(item.id, add_labels=["touched"])


@pytest.mark.parametrize(
    ("refs", "refused"),
    [([], True), (["TASK-000999:depends-on"], False), (["TASK-000999:related"], True)],
    ids=["no-ref", "dependency-ref", "other-kind-ref"],
)
async def test_a_create_at_blocked_is_refused_exactly_when_it_carries_no_dependency_ref(
    project, refs: list[str], refused: bool
) -> None:
    svc = service_with(project.squad_dir, override_toml(_TASK, _AT_ERROR))
    try:
        await create_item(svc, "task", "t", status="Blocked", refs=refs)
    except SquadsError as err:
        assert refused
        assert _MESSAGE in str(err)
        assert [i for i in await svc.list_items() if i.type == "task"] == []
    else:
        assert not refused


async def test_a_parent_link_on_a_stranded_blocked_item_is_refused(project) -> None:
    item_id = await _planted(
        service_with(project.squad_dir, override_toml(_TASK, ())), "Blocked", "none"
    )
    feature = (
        await create_item(service_with(project.squad_dir, override_toml(_TASK, ())), "feature", "f")
    ).item
    svc = service_with(project.squad_dir, override_toml(_TASK, _AT_ERROR))
    with pytest.raises(SquadsError, match=_MESSAGE):
        await svc.link(item_id, feature.id)


async def test_at_warn_a_move_to_blocked_with_no_edge_is_accepted(project) -> None:
    svc = service_with(project.squad_dir, override_toml(_TASK, ("blocked_has_blocker@warn",)))
    item = (await create_item(svc, "task", "t")).item
    moved = await svc.update(item.id, status="Blocked", force=True)
    assert moved.status == "Blocked"
    assert len(member_findings(await svc.check(), BLOCKED_HAS_BLOCKER)) == 1


async def test_the_gate_reads_the_index_for_incoming_edges_once_per_call(
    project, monkeypatch: pytest.MonkeyPatch
) -> None:
    svc = service_with(project.squad_dir, override_toml(_TASK, _AT_ERROR))
    item = (await create_item(svc, "task", "t")).item
    calls = {"incoming_edges": 0, "registered_slugs": 0}
    for name in calls:
        original = getattr(validators, name)

        def counted(*args, _name=name, _original=original):
            calls[_name] += 1
            return _original(*args)

        monkeypatch.setattr(validators, name, counted)
    await svc.update(item.id, add_labels=["touched"])
    assert calls == {"incoming_edges": 1, "registered_slugs": 1}


async def test_an_import_create_at_blocked_is_refused_with_nothing_written(project) -> None:
    svc = service_with(project.squad_dir, override_toml(_TASK, _AT_ERROR))
    event = {"op": "create", "type": "task", "as": "manager", "handle": "h", "title": "t"}
    refused = await svc.import_events(json.dumps({**event, "status": "Blocked"}))
    assert refused.applied is None
    assert any(_MESSAGE in i.message for i in refused.plan.issues), refused.plan.issues
    assert [i for i in await svc.list_items() if i.type == "task"] == []
    applied = await svc.import_events(
        json.dumps({**event, "status": "Blocked", "refs": ["TASK-000999:depends-on"]})
    )
    assert applied.applied is not None, applied.plan.issues
