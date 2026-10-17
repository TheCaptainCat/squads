"""`ref_rule_target_typed@error` at the write doors. Over the edge shapes, a write on an item
is refused exactly when `check()` on the resulting state reports the edge; a create carrying a
misdirected ref is refused; `ref add` and `ref rm` are not gated, so the state they leave is
reported by `check()` and refuses the item's next write until the edge is removed.
"""

import json

import pytest

from _helpers import create_item
from _selection_table import REF_RULE_TARGET_TYPED, member_findings, service_with
from squads._errors import SquadsError

pytestmark = pytest.mark.anyio

_RULES = (
    '[items.feature]\nref_rules = [{ kind = "related", target = "milestone" },'
    ' { kind = "implements", target = "contract" }, { kind = "addresses" }]\n'
)
_UNSELECTED = _RULES
_TOML = _RULES + 'validators = ["ref_rule_target_typed@error"]\n'

_MESSAGE = "refs must point at a"

#: Edge shape -> (target type or None for a dangling id, kind as spelled).
_SHAPES: dict[str, tuple[str | None, str]] = {
    "typed-right": ("contract", "implements"),
    "typed-wrong": ("task", "implements"),
    "default-kind-right": ("milestone", ""),
    "default-kind-wrong": ("task", ""),
    "default-kind-spelled-wrong": ("task", "related"),
    "untyped-kind": ("task", "addresses"),
    "unruled-kind": ("task", "depends-on"),
    "dangling": (None, "implements"),
}


async def _seed(svc, shape: str) -> tuple[str, list[str]]:
    """A feature carrying one edge of *shape*, returning its id and the refs it was made with."""
    target_type, kind = _SHAPES[shape]
    if target_type is None:
        return "", ["TASK-999999:implements"]
    target = (await create_item(svc, target_type, "target")).item
    return target.id, [f"{target.id}:{kind}" if kind else target.id]


@pytest.mark.parametrize("shape", _SHAPES)
async def test_a_write_is_refused_exactly_when_check_reports_the_resulting_state(
    project, shape: str
) -> None:
    unselected = service_with(project.squad_dir, _UNSELECTED)
    _, refs = await _seed(unselected, shape)
    feature = (await create_item(unselected, "feature", "source", refs=refs)).item
    svc = service_with(project.squad_dir, _TOML)
    reported = bool(member_findings(await svc.check(), REF_RULE_TARGET_TYPED))
    try:
        await svc.update(feature.id, add_labels=["touched"])
    except SquadsError as err:
        assert reported
        assert _MESSAGE in str(err)
    else:
        assert not reported


@pytest.mark.parametrize("shape", _SHAPES)
async def test_a_create_is_refused_exactly_when_it_carries_a_misdirected_ref(
    project, shape: str
) -> None:
    svc = service_with(project.squad_dir, _TOML)
    _, refs = await _seed(svc, shape)
    misdirected = shape in {"typed-wrong", "default-kind-wrong", "default-kind-spelled-wrong"}
    try:
        created = (await create_item(svc, "feature", "source", refs=refs)).item
    except SquadsError as err:
        assert misdirected
        assert _MESSAGE in str(err)
        assert [i for i in await svc.list_items() if i.type == "feature"] == []
    else:
        assert not misdirected
        assert created.id


async def test_ref_add_is_not_gated_and_the_next_write_is_refused_until_the_edge_is_removed(
    project,
) -> None:
    svc = service_with(project.squad_dir, _TOML)
    feature = (await create_item(svc, "feature", "source")).item
    wrong = (await create_item(svc, "task", "wrong")).item
    await svc.add_ref(feature.id, wrong.id, kind="implements")

    assert [i for _, i, _ in member_findings(await svc.check(), REF_RULE_TARGET_TYPED)] == [
        feature.id
    ]
    with pytest.raises(SquadsError, match=_MESSAGE):
        await svc.update(feature.id, add_labels=["touched"])
    with pytest.raises(SquadsError, match=_MESSAGE):
        await svc.update(feature.id, status="Ready")

    await svc.rm_ref(feature.id, wrong.id)
    await svc.update(feature.id, add_labels=["touched"])
    assert member_findings(await svc.check(), REF_RULE_TARGET_TYPED) == []


def _event(handle: str, ref: str) -> str:
    return json.dumps(
        {
            "op": "create",
            "type": "feature",
            "title": handle,
            "as": "manager",
            "handle": handle,
            "refs": [ref],
        }
    )


async def test_an_import_with_a_misdirected_ref_is_refused_by_the_pre_pass(project) -> None:
    svc = service_with(project.squad_dir, _TOML)
    wrong = (await create_item(svc, "task", "wrong")).item
    right = (await create_item(svc, "contract", "right")).item
    refused = await svc.import_events(_event("bad", f"{wrong.id}:implements"))
    assert refused.applied is None
    assert any(_MESSAGE in i.message for i in refused.plan.issues), refused.plan.issues
    accepted = await svc.import_events(_event("good", f"{right.id}:implements"))
    assert accepted.applied is not None, accepted.plan.issues
