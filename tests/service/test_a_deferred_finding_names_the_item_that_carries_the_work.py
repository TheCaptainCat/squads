"""A finding closes as Noted or Deferred, and a Deferred one stores the item that carries the
work. Driven over the lifecycle edges, over each way the pointer is given, refused, moved and
cleared, over the other doors into the same rule, and over a project's own deferred status.
"""

import json

import pytest

from _helpers import create_item
from _selection_table import service_with
from squads._errors import InvalidTransitionError, SquadsError
from squads._itemfile import read_frontmatter
from squads._services._service import Service

pytestmark = pytest.mark.anyio


async def _review_with_finding(svc: Service) -> tuple[str, str]:
    """A review holding one Open finding, and a task to carry work."""
    review = (await create_item(svc, "review", "r")).item
    await svc.add_finding(review.id, "f")
    carrier = (await create_item(svc, "task", "carrier")).item
    return review.id, carrier.id


async def _finding(svc: Service, review_id: str):
    return (await svc.list_findings(review_id))[0]


#: (states to pass through, target, force) -> whether the last move is allowed.
_EDGES: dict[str, tuple[list[str], str, bool, bool]] = {
    "open-to-noted": ([], "Noted", False, True),
    "noted-to-open": (["Noted"], "Open", False, False),
    "noted-to-open-forced": (["Noted"], "Open", True, True),
}


@pytest.mark.parametrize("edge", _EDGES)
async def test_noted_is_reached_from_open_and_left_only_with_force(svc, edge: str) -> None:
    path, target, force, allowed = _EDGES[edge]
    review, _ = await _review_with_finding(svc)
    for step in path:
        await svc.update_finding(review, "F1", status=step)
    move = svc.update_finding(review, "F1", status=target, force=force)
    if allowed:
        await move
        assert (await _finding(svc, review)).status == target
    else:
        with pytest.raises(InvalidTransitionError, match="--force"):
            await move
        assert (await _finding(svc, review)).status == path[-1]


#: shape -> (finding starts deferred to "carrier", update arguments, error fragment or None,
#: expected (status, pointer) afterwards). Pointer tokens: "carrier", "second", "seq" (the
#: carrier's bare number), "self" (the review), "role" (a roster item), "missing".
_POINTER_SHAPES: dict[str, tuple[bool, dict[str, object], str | None, tuple[str, str | None]]] = {
    "no-pointer": (False, {"status": "Deferred"}, "--deferred-to", ("Open", None)),
    "no-pointer-forced": (
        False,
        {"status": "Deferred", "force": True},
        "--deferred-to",
        ("Open", None),
    ),
    "missing-item": (
        False,
        {"status": "Deferred", "deferred_to": "missing"},
        "no item",
        ("Open", None),
    ),
    "own-review": (
        False,
        {"status": "Deferred", "deferred_to": "self"},
        "cannot carry its own",
        ("Open", None),
    ),
    "roster-item": (
        False,
        {"status": "Deferred", "deferred_to": "role"},
        "not an item that carries work",
        ("Open", None),
    ),
    "full-id": (
        False,
        {"status": "Deferred", "deferred_to": "carrier"},
        None,
        ("Deferred", "carrier"),
    ),
    "bare-number": (
        False,
        {"status": "Deferred", "deferred_to": "seq"},
        None,
        ("Deferred", "carrier"),
    ),
    "pointer-without-a-move": (
        False,
        {"deferred_to": "carrier"},
        "deferred status",
        ("Open", None),
    ),
    "pointer-with-a-non-deferred-move": (
        False,
        {"status": "Fixed", "deferred_to": "carrier"},
        "deferred status",
        ("Open", None),
    ),
    "pointer-moved-alone": (True, {"deferred_to": "second"}, None, ("Deferred", "second")),
    "leaving-clears-it": (True, {"status": "Open", "force": True}, None, ("Open", None)),
}


@pytest.mark.parametrize("shape", _POINTER_SHAPES)
async def test_the_pointer_is_given_refused_moved_and_cleared_per_shape(svc, shape: str) -> None:
    starts_deferred, arguments, refusal, (status, pointer) = _POINTER_SHAPES[shape]
    review, carrier = await _review_with_finding(svc)
    second = (await create_item(svc, "task", "second")).item.id
    tokens = {
        "carrier": carrier,
        "second": second,
        "seq": str((await svc.get(carrier)).sequence_id),
        "self": review,
        "role": "ROLE-1",
        "missing": "TASK-000999",
    }
    if starts_deferred:
        await svc.update_finding(review, "F1", status="Deferred", deferred_to=carrier)
    call = {k: tokens.get(str(v), v) if k == "deferred_to" else v for k, v in arguments.items()}
    if refusal:
        with pytest.raises(SquadsError, match=refusal):
            await svc.update_finding(review, "F1", **call)
        status, pointer = ("Deferred", carrier) if starts_deferred else (status, pointer)
    else:
        await svc.update_finding(review, "F1", **call)
    found = await _finding(svc, review)
    assert (found.status, found.deferred_to) == (status, tokens.get(str(pointer), pointer))
    path = svc.paths.abspath((await svc.get(review)).path)
    assert read_frontmatter(path)["subentities"][0].get("deferred_to") == found.deferred_to


async def test_a_pointer_on_a_kind_that_reaches_no_deferred_status_is_refused(svc) -> None:
    feature = (await create_item(svc, "feature", "f")).item
    await svc.add_story(feature.id, "s")
    carrier = (await create_item(svc, "task", "carrier")).item
    with pytest.raises(SquadsError, match="no deferred status"):
        await svc.update_block(feature.id, "story", "US1", deferred_to=carrier.id)


async def test_a_finding_added_as_deferred_stores_its_pointer(svc) -> None:
    review = (await create_item(svc, "review", "r")).item
    carrier = (await create_item(svc, "task", "carrier")).item
    with pytest.raises(SquadsError, match="--deferred-to"):
        await svc.add_finding(review.id, "no pointer", status="Deferred")
    await svc.add_finding(review.id, "handed on", status="Deferred", deferred_to=carrier.id)
    assert [(f.status, f.deferred_to) for f in await svc.list_findings(review.id)] == [
        ("Deferred", carrier.id)
    ]


#: op -> the event beyond its target; each is tried without and with the pointer.
_IMPORT_OPS: dict[str, dict[str, object]] = {
    "sub-status": {"kind": "finding", "local": "F1", "status": "Deferred"},
    "add-finding": {"title": "seeded", "severity": "low", "status": "Deferred"},
}


@pytest.mark.parametrize("op", _IMPORT_OPS)
async def test_an_import_defers_a_finding_only_with_a_pointer(svc, op: str) -> None:
    review, carrier = await _review_with_finding(svc)
    event = {"op": op, "target": review, "as": "manager", **_IMPORT_OPS[op]}

    refused = await svc.import_events(json.dumps(event))
    assert refused.applied is None
    assert "deferred_to" in " ".join(str(i) for i in refused.plan.issues)
    assert [f.status for f in await svc.list_findings(review)] == ["Open"]

    result = await svc.import_events(json.dumps({**event, "deferred_to": carrier}))
    assert result.applied is not None, result.plan.issues
    assert {(f.status, f.deferred_to) for f in await svc.list_findings(review)} >= {
        ("Deferred", carrier)
    }


_POSTPONED = """
[roles.parked]
settled = true
hidden = true
color = "info"
deferred = true

[statuses.Postponed]
role = "parked"
badge = "🟤"

[lifecycles.finding.transitions]
Open = ["$(*lifecycles.finding.transitions.Open)", "Postponed"]
"""


async def test_a_project_status_with_a_deferred_role_gets_the_same_refusal(project) -> None:
    svc = service_with(project.squad_dir, _POSTPONED)
    review, carrier = await _review_with_finding(svc)
    with pytest.raises(SquadsError, match="--deferred-to"):
        await svc.update_finding(review, "F1", status="Postponed")
    await svc.update_finding(review, "F1", status="Postponed", deferred_to=carrier)
    assert (await _finding(svc, review)).deferred_to == carrier


_PARKED_FIRST = """
[roles.parked]
settled = true
hidden = true
color = "info"
deferred = true

[statuses.Parked]
role = "parked"

[lifecycles.finding]
initial = "Parked"

[lifecycles.finding.transitions]
Parked = ["Open"]
"""


async def test_adding_into_a_deferred_initial_status_needs_the_pointer(project) -> None:
    svc = service_with(project.squad_dir, _PARKED_FIRST)
    review = (await create_item(svc, "review", "r")).item
    carrier = (await create_item(svc, "task", "carrier")).item
    with pytest.raises(SquadsError, match="--deferred-to"):
        await svc.add_finding(review.id, "plain add")
    await svc.add_finding(review.id, "handed on", deferred_to=carrier.id)
    assert [(f.status, f.deferred_to) for f in await svc.list_findings(review.id)] == [
        ("Parked", carrier.id)
    ]
