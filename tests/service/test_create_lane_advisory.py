"""The advisory create-lane warning: CreateResult.lane_warning is set for an out-of-lane
create, None for an in-lane one, manager/op-* are exempt, non-laned roster types (role/skill/
operator) never carry the warning, and status mutations never trigger the check (create-time
only). The lane table itself lives in tests/unit/test_create_lane_derivation.py.
"""

import pytest

from squads import _actor as actor
from squads._index._reflog import read_lines, reflog_path

pytestmark = pytest.mark.anyio


async def test_an_out_of_lane_create_returns_an_advisory_warning_naming_actor_and_owner(
    svc, frozen_time
) -> None:
    await svc.add_dev("python")
    actor.set_actor("python-dev")
    res = await svc.create("feature", "Oops", author="python-dev")
    assert res.lane_warning is not None
    assert "python-dev" in res.lane_warning
    assert "product-owner" in res.lane_warning
    assert "feature" in res.lane_warning
    assert "advisory" in res.lane_warning
    assert res.item.id is not None  # the item is still created despite the warning


async def test_an_in_lane_create_returns_no_warning(svc, frozen_time) -> None:
    await svc.activate_role("tech-lead")
    actor.set_actor("tech-lead")
    res = await svc.create("task", "Fix stuff", author="tech-lead")
    assert res.lane_warning is None


async def test_manager_is_exempt_from_the_lane_check(svc, frozen_time) -> None:
    actor.set_actor("manager")
    res = await svc.create("feature", "Manager feature", author="manager")
    assert res.lane_warning is None


async def test_an_op_slug_is_exempt_from_the_lane_check(svc, frozen_time) -> None:
    await svc.add_operator("Pierre", slug="op-pierre")
    actor.set_actor("op-pierre")
    res = await svc.create("feature", "Human feature", author="op-pierre")
    assert res.lane_warning is None


async def test_a_dev_creating_a_bug_still_gets_the_advisory_warning_not_a_hard_block(
    svc, frozen_time
) -> None:
    """The dev lane is empty (bug is owned by qa) — dev-authored bugs proceed with a warning,
    not a hard --author qa requirement."""
    await svc.add_dev("python")
    actor.set_actor("python-dev")
    res = await svc.create("bug", "Found a defect", author="python-dev")
    assert res.lane_warning is not None
    assert "python-dev" in res.lane_warning
    assert "qa" in res.lane_warning
    assert res.item.id is not None


async def test_qa_creating_a_bug_gets_no_warning(svc, frozen_time) -> None:
    await svc.activate_role("qa")
    actor.set_actor("qa")
    res = await svc.create("bug", "Known defect", author="qa")
    assert res.lane_warning is None


async def test_the_reflog_delta_for_an_out_of_lane_create_carries_the_lane_warning_tag(
    svc, frozen_time
) -> None:
    await svc.add_dev("python")
    actor.set_actor("python-dev")
    res = await svc.create("feature", "Bad feature", author="python-dev")
    lines = await read_lines(reflog_path(svc.paths.squad_dir))
    (create_line,) = [ln for ln in lines if ln.op == "create" and ln.target == res.item.id]
    lw = create_line.delta["lane_warning"]
    assert isinstance(lw, dict)
    assert lw["advisory"] is True
    assert lw["actor"] == "python-dev"
    assert "product-owner" in lw["expected"]
    assert lw["type"] == "feature"


async def test_the_reflog_delta_for_an_in_lane_create_has_no_lane_warning_key(
    svc, frozen_time
) -> None:
    await svc.activate_role("tech-lead")
    actor.set_actor("tech-lead")
    res = await svc.create("task", "Clean task", author="tech-lead")
    lines = await read_lines(reflog_path(svc.paths.squad_dir))
    (create_line,) = [ln for ln in lines if ln.op == "create" and ln.target == res.item.id]
    assert "lane_warning" not in create_line.delta


async def test_a_status_mutation_never_triggers_the_lane_check(svc, frozen_time) -> None:
    actor.set_actor("python-dev")
    res = await svc.create("feature", "Feature", author="manager")
    await svc.set_status(res.item.id, "InProgress")  # must not raise or warn


async def test_creating_a_role_meta_item_never_carries_a_lane_warning(svc, frozen_time) -> None:
    """role/skill/operator are outside the lane domain entirely."""
    role_item = await svc.activate_role("architect")
    lines = await read_lines(reflog_path(svc.paths.squad_dir))
    (create_line,) = [ln for ln in lines if ln.op == "create" and ln.target == role_item.id]
    assert "lane_warning" not in create_line.delta


async def test_creating_an_operator_meta_item_never_carries_a_lane_warning(
    svc, frozen_time
) -> None:
    op_item = await svc.add_operator("Test User", slug="op-test")
    lines = await read_lines(reflog_path(svc.paths.squad_dir))
    (create_line,) = [ln for ln in lines if ln.op == "create" and ln.target == op_item.id]
    assert "lane_warning" not in create_line.delta
