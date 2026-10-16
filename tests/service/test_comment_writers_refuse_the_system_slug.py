"""The service-level comment writers refuse the system slug whatever the roster holds, so a caller
that skips the CLI's actor resolution cannot write a system entry."""

import json

import pytest

from _helpers import create_item, squad_tree
from squads._errors import SquadsError
from squads._services import _base

pytestmark = pytest.mark.anyio


@pytest.fixture(params=["no-holder", "held-by-a-hand-written-operator"])
async def held(request, svc, monkeypatch):
    if request.param == "held-by-a-hand-written-operator":
        with monkeypatch.context() as unchecked:
            unchecked.setattr(_base, "_check_roster_slug", lambda *args, **kwargs: None)
            await svc.add_operator("Sys Op", slug="squads")
    return request.param


async def _write(svc, writer: str, task) -> None:
    if writer == "comment":
        await svc.comment(task.id, ["hello"], as_slug="squads")
    elif writer == "board":
        await svc.board_post("squads", "hello")
    else:
        event = {"op": "comment", "target": task.id, "message": "hello", "as": "squads"}
        result = await svc.import_events(json.dumps(event))
        if result.applied is None:
            raise SquadsError("; ".join(i.message for i in result.plan.issues))


@pytest.mark.parametrize("writer", ["comment", "board", "import"])
async def test_a_service_comment_writer_refuses_the_system_slug_and_writes_nothing(
    svc, project, held, writer
) -> None:
    task = (await create_item(svc, "task", "Target")).item
    before = squad_tree(project.root)

    with pytest.raises(SquadsError, match="reserved for system entries"):
        await _write(svc, writer, task)

    assert squad_tree(project.root) == before
