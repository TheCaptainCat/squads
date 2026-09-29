"""A view tag never enters through the prose door: ``reject_markers`` refuses it exactly like
any other marker, while the identical unwrapped text is accepted. Placement is the only door."""

import inspect

import pytest

from _helpers import create_item
from squads import _sections as sections
from squads._errors import SquadsError
from squads._models import _markers as markers
from squads._services._base import reject_markers

pytestmark = pytest.mark.anyio

_NAME = "milestone_rollup"
_WRAPPED = markers.open_marker(markers.view_tag(_NAME))
_UNWRAPPED = markers.view_tag(_NAME)
_WRAPPED_DISABLED = markers.open_marker(markers.view_tag(_NAME, disabled=True))


def test_reject_markers_takes_no_per_name_exception_or_allow_parameter() -> None:
    """No parameter here can be used to admit one tag while refusing others."""
    params = list(inspect.signature(reject_markers).parameters)
    assert params == ["text", "what"]


@pytest.mark.parametrize(
    ("label", "write"),
    [
        ("wrapped, set", lambda svc, tid: svc.set_body(tid, f"see {_WRAPPED}")),
        ("wrapped, append", lambda svc, tid: svc.set_body(tid, f"see {_WRAPPED}", append=True)),
        (
            "wrapped disabled, set",
            lambda svc, tid: svc.set_body(tid, f"see {_WRAPPED_DISABLED}"),
        ),
        (
            "wrapped disabled, append",
            lambda svc, tid: svc.set_body(tid, f"see {_WRAPPED_DISABLED}", append=True),
        ),
    ],
    ids=["set", "append", "set-disabled", "append-disabled"],
)
async def test_body_write_refuses_the_wrapped_view_tag(svc, label, write) -> None:
    task = (await create_item(svc, "task", "t")).item
    with pytest.raises(SquadsError, match="marker"):
        await write(svc, task.id)


async def test_body_write_accepts_the_identical_text_unwrapped_the_control(svc) -> None:
    """The identical text unwrapped is accepted, the control: the refusal is about shape."""
    task = (await create_item(svc, "task", "t")).item
    it = await svc.set_body(task.id, f"see {_UNWRAPPED}")
    body = await svc.read_body(it.id)
    assert _UNWRAPPED in body


async def test_a_view_tag_never_reaches_the_body_via_a_refused_write(svc) -> None:
    """A refused write leaves the file untouched; the tag genuinely never lands."""
    task = (await create_item(svc, "task", "t")).item
    path = svc.paths.abspath((await svc.get(task.id)).path)
    before = path.read_text(encoding="utf-8")
    with pytest.raises(SquadsError, match="marker"):
        await svc.set_body(task.id, f"see {_WRAPPED}")
    after = path.read_text(encoding="utf-8")
    assert after == before
    assert sections.find_markers(after) == sections.find_markers(before)


async def test_placement_is_the_only_door_the_tag_gets_in_through(svc) -> None:
    """The same view on the same item is refused through prose but accepted through placement."""
    task = (await create_item(svc, "task", "t")).item
    with pytest.raises(SquadsError, match="marker"):
        await svc.set_body(task.id, f"see {_WRAPPED}")

    inserted = await svc.add_view(task.id, _NAME)

    assert inserted is True
    path = svc.paths.abspath((await svc.get(task.id)).path)
    assert _WRAPPED in path.read_text(encoding="utf-8")
