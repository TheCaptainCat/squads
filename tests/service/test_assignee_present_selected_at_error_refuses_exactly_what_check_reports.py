"""`assignee_present@error` at the write doors. Over the status and assignee shapes, a write on
an item is refused exactly when `check()` on the resulting state reports it; moving an
unassigned item to an active status is refused, doing it with an assignee in the same command
is accepted, clearing the assignee of an active item is refused, and assigning first then moving
is the way through.
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
from squads._errors import SquadsError

pytestmark = pytest.mark.anyio

_TASK = TypeRow("task", "task")
_AT_ERROR = ("assignee_present@error",)
_MESSAGE = "nobody is assigned"
#: (status, assignee) -> whether the state is reported.
_SHAPES: dict[tuple[str, str | None], bool] = {
    ("Draft", None): False,
    ("Draft", "manager"): False,
    ("Ready", None): False,
    ("InProgress", None): True,
    ("InProgress", "manager"): False,
    ("InReview", None): True,
    ("InReview", "manager"): False,
    ("Blocked", None): False,
    ("Done", None): False,
}


@pytest.mark.parametrize(("status", "assignee"), _SHAPES, ids=lambda v: str(v))
async def test_a_write_is_refused_exactly_when_check_reports_the_resulting_state(
    project, status: str, assignee: str | None
) -> None:
    unselected = service_with(project.squad_dir, override_toml(_TASK, ()))
    item = (await create_item(unselected, "task", "t", assignee=assignee)).item
    await unselected.update(item.id, status=status, force=True)
    svc = service_with(project.squad_dir, override_toml(_TASK, _AT_ERROR))
    reported = bool(member_findings(await svc.check(), ASSIGNEE_PRESENT))
    assert reported is _SHAPES[(status, assignee)]
    try:
        await svc.update(item.id, add_labels=["touched"])
    except SquadsError as err:
        assert reported
        assert _MESSAGE in str(err)
    else:
        assert not reported


async def test_moving_to_an_active_status_needs_an_assignee_in_the_same_command(project) -> None:
    svc = service_with(project.squad_dir, override_toml(_TASK, _AT_ERROR))
    item = (await create_item(svc, "task", "t")).item
    with pytest.raises(SquadsError, match=_MESSAGE):
        await svc.update(item.id, status="InProgress", force=True)
    moved = await svc.update(item.id, status="InProgress", assignee="manager", force=True)
    assert (moved.status, moved.assignee) == ("InProgress", "manager")


async def test_assigning_first_and_then_moving_is_the_way_through(project) -> None:
    svc = service_with(project.squad_dir, override_toml(_TASK, _AT_ERROR))
    item = (await create_item(svc, "task", "t")).item
    await svc.update(item.id, assignee="manager")
    await svc.update(item.id, status="InProgress", force=True)
    with pytest.raises(SquadsError, match=_MESSAGE):
        await svc.update(item.id, assignee="")
    await svc.update(item.id, status="Done", force=True)
    await svc.update(item.id, assignee="")
    assert member_findings(await svc.check(), ASSIGNEE_PRESENT) == []


@pytest.mark.parametrize(
    ("assignee", "refused"), [(None, True), ("manager", False)], ids=["unassigned", "assigned"]
)
async def test_a_create_at_an_active_status_is_refused_exactly_when_nobody_is_assigned(
    project, assignee: str | None, refused: bool
) -> None:
    svc = service_with(project.squad_dir, override_toml(_TASK, _AT_ERROR))
    try:
        await create_item(svc, "task", "t", status="InProgress", assignee=assignee)
    except SquadsError as err:
        assert refused
        assert _MESSAGE in str(err)
    else:
        assert not refused
