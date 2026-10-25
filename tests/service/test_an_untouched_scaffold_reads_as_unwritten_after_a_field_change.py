"""A body still equal to the scaffold its item holds is re-rendered when `update --set` or
`retype` changes what the scaffold is built from, so it keeps reading as unwritten: the body
write replaces it and `body_written` reports it. A written body is never rewritten."""

from pathlib import Path

import pytest

from _helpers import create_item
from squads import __version__
from squads._errors import SquadsError
from squads._rendering._engine import invalidate_squad_dir
from squads._services import _service as service

pytestmark = pytest.mark.anyio

_SELECT = '[items.review]\nvalidators = ["body_written"]\n\n'

_OVERRIDE = """\
[lifecycles.triage]
initial = "Open"
[lifecycles.triage.transitions]
Open = ["Done"]
Done = []

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "triage"
validators = ["body_written"]

[items.problem]
prefix = "PRB"
folder = "problems"
lifecycle = "triage"
validators = ["body_written"]
"""

#: A review template whose field ends the line and starts another.
_REVIEW_TEMPLATE = """\
<!-- sq:body -->
## Scope

_TODO: what is under review?_
{% if item.target_ref is defined and item.target_ref %}

**Target:** {{ item.target_ref }}

{{ item.target_ref }} is the target
{% endif %}
<!-- sq:body:end -->

## Findings

<!-- sq:findings -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
"""

_UNWRITTEN = "body is unwritten"


def _open(squad_dir: Path, extra: str = "") -> service.Service:
    (squad_dir / ".overrides").mkdir(parents=True, exist_ok=True)
    (squad_dir / ".overrides" / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n" + _SELECT + extra, encoding="utf-8"
    )
    return service.open_service()


@pytest.fixture
def svc(project) -> service.Service:
    return _open(project.squad_dir)


async def _unwritten(svc, item_id: str) -> bool:
    return any(_UNWRITTEN in i.message for i in await svc.check() if i.item == item_id)


async def _set_target(svc, item_id: str, value: str):
    await svc.update(item_id, set_attributes={"target_ref": value})


async def _unset_target(svc, item_id: str, _value: str):
    await svc.update(item_id, unset_attributes=["target_ref"])


_REVIEW_ROWS = [
    pytest.param(None, _set_target, "main", id="set-after-created-without"),
    pytest.param("old", _set_target, "new", id="changed"),
    pytest.param("old", _unset_target, "", id="unset"),
    pytest.param("old", None, "", id="untouched-control"),
]


async def _review(svc, target):
    attrs = {"target_ref": target} if target else None
    return (await create_item(svc, "review", "A review", attributes=attrs)).item.id


@pytest.mark.parametrize(("created_with", "change", "value"), _REVIEW_ROWS)
async def test_an_untouched_review_scaffold_stays_unwritten_after_a_target_change(
    svc, created_with, change, value
):
    item_id = await _review(svc, created_with)
    if change is not None:
        await change(svc, item_id, value)

    assert await _unwritten(svc, item_id)
    await svc.set_body(item_id, "Real scope.")
    assert not await _unwritten(svc, item_id)


@pytest.mark.parametrize(("created_with", "change", "value"), _REVIEW_ROWS)
async def test_an_authored_review_body_is_never_rewritten_by_a_field_change(
    svc, created_with, change, value
):
    item_id = await _review(svc, created_with)
    await svc.set_body(item_id, "Real scope.", force=True)
    if change is not None:
        await change(svc, item_id, value)

    assert (await svc.read_stored_body(item_id)).strip() == "Real scope."
    with pytest.raises(SquadsError, match="already has a body"):
        await svc.set_body(item_id, "Replacement.")


_LOOK_ALIKES = [
    pytest.param(
        "## Scope\n\n_TODO: what is under review?_\n\nAlso this.", id="scaffold-plus-prose"
    ),
    pytest.param("**Target:** `old`", id="target-line-alone"),
    pytest.param(
        "## Scope\n\n_TODO: what is under review?_\n\n**Target:** `src/a.py`: races with b\n\n"
        "**Target:** `src/b.py`: same",
        id="several-target-shaped-lines",
    ),
]


@pytest.mark.parametrize("body", _LOOK_ALIKES)
async def test_a_body_that_only_resembles_the_scaffold_stays_authored(svc, body):
    item_id = await _review(svc, None)
    await svc.set_body(item_id, body, force=True)
    await _set_target(svc, item_id, "main")

    assert not await _unwritten(svc, item_id)
    with pytest.raises(SquadsError, match="already has a body"):
        await svc.set_body(item_id, "Replacement.")


async def test_a_template_field_at_a_line_edge_is_rendered_again(project):
    (project.squad_dir / ".overrides" / "templates" / "items").mkdir(parents=True)
    (project.squad_dir / ".overrides" / "templates" / "items" / "review.md.j2").write_text(
        _REVIEW_TEMPLATE, encoding="utf-8"
    )
    invalidate_squad_dir(project.squad_dir)
    svc = _open(project.squad_dir)
    item_id = await _review(svc, "abc")

    await _set_target(svc, item_id, "def")

    body = await svc.read_stored_body(item_id)
    assert "**Target:** def" in body
    assert "abc" not in body
    assert await _unwritten(svc, item_id)


_RETYPES = [
    pytest.param("bug", "decision", id="dedicated-to-dedicated"),
    pytest.param("task", "bug", id="task-to-bug"),
    pytest.param("incident", "problem", id="default-to-default"),
]


@pytest.mark.parametrize(("source", "target"), _RETYPES)
async def test_a_retyped_untouched_scaffold_is_the_new_types_scaffold(project, source, target):
    svc = _open(project.squad_dir, _OVERRIDE)
    item = (await create_item(svc, source, "Subject")).item

    await svc.retype(item.id, target)

    (moved,) = await svc.list_items(item_type=target)
    expected = svc.pristine_body(moved)
    assert (await svc.read_stored_body(moved.id)).strip() == expected
    await svc.set_body(moved.id, "Real description.")


@pytest.mark.parametrize(("source", "target"), _RETYPES)
async def test_a_retyped_authored_body_is_kept(project, source, target):
    svc = _open(project.squad_dir, _OVERRIDE)
    item = (await create_item(svc, source, "Subject")).item
    await svc.set_body(item.id, "Real description.")

    await svc.retype(item.id, target)

    (moved,) = await svc.list_items(item_type=target)
    assert (await svc.read_stored_body(moved.id)).strip() == "Real description."
    with pytest.raises(SquadsError, match="already has a body"):
        await svc.set_body(moved.id, "Replacement.")
