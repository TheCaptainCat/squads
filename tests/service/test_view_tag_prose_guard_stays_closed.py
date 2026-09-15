"""The view-tag placement design, driven with its own control: a view tag never enters through
the prose door. ``reject_markers`` refuses a well-formed ``sq:view:<name>`` tag typed into
``body -m``/
``--file`` exactly as it refuses any other well-formed marker — no per-name hole, no allow
parameter, no call-site bypass — while the identical text with its HTML-comment wrapper
stripped is accepted, because unwrapped text carries no marker shape at all. Placement
(``sq <type> <n> view add``) is the only door.
"""

import inspect

import pytest

from _helpers import create_item
from squads import _sections as sections
from squads._errors import SquadsError
from squads._models import _markers as markers
from squads._services._base import reject_markers

pytestmark = pytest.mark.anyio

_NAME = "milestone_rollup"
_WRAPPED = markers.open_marker(markers.view_tag(_NAME))  # "<!-- sq:view:milestone_rollup -->"
_UNWRAPPED = markers.view_tag(_NAME)  # "view:milestone_rollup" — no comment form, not a marker


def test_reject_markers_takes_no_per_name_exception_or_allow_parameter() -> None:
    """Structural guard: no parameter here can be used to admit one tag while refusing
    others."""
    params = list(inspect.signature(reject_markers).parameters)
    assert params == ["text", "what"]


@pytest.mark.parametrize(
    ("label", "write"),
    [
        ("wrapped, set", lambda svc, tid: svc.set_body(tid, f"see {_WRAPPED}")),
        ("wrapped, append", lambda svc, tid: svc.set_body(tid, f"see {_WRAPPED}", append=True)),
    ],
    ids=["set", "append"],
)
async def test_body_write_refuses_the_wrapped_view_tag(svc, label, write) -> None:
    task = (await create_item(svc, "task", "t")).item
    with pytest.raises(SquadsError, match="marker"):
        await write(svc, task.id)


async def test_body_write_accepts_the_identical_text_unwrapped_the_control(svc) -> None:
    """The control that proves the refusal above is about marker *shape*, not merely
    containing the substring ``view:milestone_rollup`` — with the comment wrapper stripped,
    the same characters are ordinary prose."""
    task = (await create_item(svc, "task", "t")).item
    it = await svc.set_body(task.id, f"see {_UNWRAPPED}")
    body = await svc.read_body(it.id)
    assert _UNWRAPPED in body


async def test_a_view_tag_never_reaches_the_body_via_a_refused_write(svc) -> None:
    """Refusal leaves the file untouched — the tag genuinely never lands, not merely that the
    call reported an error while writing it anyway."""
    task = (await create_item(svc, "task", "t")).item
    path = svc.paths.abspath((await svc.get(task.id)).path)
    before = path.read_text(encoding="utf-8")
    with pytest.raises(SquadsError, match="marker"):
        await svc.set_body(task.id, f"see {_WRAPPED}")
    after = path.read_text(encoding="utf-8")
    assert after == before
    assert sections.find_markers(after) == sections.find_markers(before)


async def test_placement_is_the_only_door_the_tag_gets_in_through(svc) -> None:
    """Same view, same item: the prose door refuses it, the placement verb accepts it — the
    two are genuinely different code paths, not a body write with the guard quietly loosened."""
    task = (await create_item(svc, "task", "t")).item
    with pytest.raises(SquadsError, match="marker"):
        await svc.set_body(task.id, f"see {_WRAPPED}")

    inserted = await svc.insert_view(task.id, _NAME)

    assert inserted is True
    path = svc.paths.abspath((await svc.get(task.id)).path)
    assert _WRAPPED in path.read_text(encoding="utf-8")
