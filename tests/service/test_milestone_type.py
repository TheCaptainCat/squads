"""The ``milestone`` item type: its lifecycle, its target date, membership by forward ``targets``
refs written only on the work item, and its roll-up view (the mechanism's first bundled
consumer).

``svc.create()``'s ``extra`` kwarg is the generic settable-at-create door (the same one every
type's ``extra`` metadata already goes through — see ``guide``'s ``--tech``/``--tag`` CLI
flags, which pass raw values the same way); ``svc.update(set_extra=...)`` is the generic
settable-afterwards door, and the only one that validates/normalises through
``_models._metadata.coerce_extra``.
"""

from typing import cast

import pytest

from _helpers import create_item
from squads._errors import SquadsError
from squads._models._extras import ExtraKey as X
from squads._views import projection_json

pytestmark = pytest.mark.anyio


async def _milestone(svc, **kwargs):
    return (await create_item(svc, "milestone", "Ship the release", **kwargs)).item


# --------------------------------------------------------------------------- the type + lifecycle


async def test_a_milestone_is_created_with_the_declared_prefix_and_initial_status(svc) -> None:
    m = await _milestone(svc)
    assert m.id.startswith("MILE-")
    assert m.status == "Draft"


async def test_the_milestone_lifecycle_reaches_both_terminals(svc) -> None:
    m = await _milestone(svc)
    await svc.set_status(m.id, "InProgress")
    done = await svc.set_status(m.id, "Done")
    assert done.status == "Done"

    m2 = await _milestone(svc)
    cancelled = await svc.set_status(m2.id, "Cancelled")
    assert cancelled.status == "Cancelled"


async def test_a_milestone_carries_no_parent_and_no_subentities(svc) -> None:
    m = await _milestone(svc)
    assert m.parent is None
    assert m.subentities == []


# --------------------------------------------------------------------------- target date


async def test_target_date_is_settable_at_create_through_the_generic_extra_door(svc) -> None:
    m = await _milestone(svc, extra={X.TARGET_DATE: "2026-12-01"})
    assert m.extra[X.TARGET_DATE] == "2026-12-01"
    reread = await svc.get(m.id)
    assert reread.extra[X.TARGET_DATE] == "2026-12-01"


async def test_target_date_is_settable_afterwards_through_generic_set_and_normalised(svc) -> None:
    m = await _milestone(svc)
    updated = await svc.update(m.id, set_extra={X.TARGET_DATE: "2026-12-01"})
    assert updated.extra[X.TARGET_DATE] == "2026-12-01"
    reread = await svc.get(m.id)
    assert reread.extra[X.TARGET_DATE] == "2026-12-01"


async def test_an_unparseable_target_date_is_refused_naming_the_field_and_not_stored(svc) -> None:
    m = await _milestone(svc)
    with pytest.raises(SquadsError, match="target_date"):
        await svc.update(m.id, set_extra={X.TARGET_DATE: "not-a-date"})
    reread = await svc.get(m.id)
    assert X.TARGET_DATE not in reread.extra


# --------------------------------------------------------------------------- membership by targets


async def _file_bytes(project, item) -> bytes:
    return (project.squad_dir / item.path).read_bytes()


async def test_ref_add_targets_writes_only_the_work_item_leaving_the_milestone_byte_identical(
    project, svc
) -> None:
    m = await _milestone(svc)
    task = (await create_item(svc, "task", "Do the work")).item
    before = await _file_bytes(project, m)

    await svc.add_ref(task.id, m.id, kind="targets")
    task2 = (await create_item(svc, "task", "Do more work")).item
    await svc.add_ref(task2.id, m.id, kind="targets")
    await svc.set_status(task.id, "Ready")

    after = await _file_bytes(project, m)
    assert after == before

    updated_task = await svc.get(task.id)
    assert f"{m.id}:targets" in updated_task.refs or m.id in updated_task.refs


async def test_membership_is_recovered_by_inverting_stored_forward_refs(project, svc) -> None:
    m = await _milestone(svc)
    a = (await create_item(svc, "task", "A")).item
    b = (await create_item(svc, "bug", "B")).item
    unrelated = (await create_item(svc, "task", "Not targeting the milestone")).item
    await svc.add_ref(a.id, m.id, kind="targets")
    await svc.add_ref(b.id, m.id, kind="targets")

    projection = await svc.resolve_view("milestone_rollup", m.id)
    ids = {r.values["id"].text for r in projection.records()}
    assert ids == {a.id, b.id}
    assert unrelated.id not in ids


# --------------------------------------------------------------------------- the roll-up view


async def test_the_rollup_groups_delivered_and_outstanding_by_status_role_across_types(
    project, svc
) -> None:
    """A milestone can hold members of several types on several lifecycles — grouping must
    resolve each member's own status *role*, not a literal status spelling, or a bug's 'Fixed'
    (role=active) would be mis-grouped against a task's 'Done' (role=done)."""
    m = await _milestone(svc)
    delivered_task = (await create_item(svc, "task", "Delivered task")).item
    await svc.add_ref(delivered_task.id, m.id, kind="targets")
    await svc.set_status(delivered_task.id, "Ready")
    await svc.set_status(delivered_task.id, "InProgress")
    await svc.set_status(delivered_task.id, "Done")

    outstanding_bug = (await create_item(svc, "bug", "Open bug")).item
    await svc.add_ref(outstanding_bug.id, m.id, kind="targets")

    delivered_bug = (await create_item(svc, "bug", "Verified bug")).item
    await svc.add_ref(delivered_bug.id, m.id, kind="targets")
    await svc.set_status(delivered_bug.id, "InProgress")
    await svc.set_status(delivered_bug.id, "Fixed")
    await svc.set_status(delivered_bug.id, "Verified")

    rendered = await svc.render_view("milestone_rollup", m.id)
    delivered_section, outstanding_section = rendered.split("## Outstanding")
    assert delivered_task.id in delivered_section
    assert delivered_bug.id in delivered_section
    assert outstanding_bug.id not in delivered_section
    assert outstanding_bug.id in outstanding_section
    assert delivered_task.id not in outstanding_section


async def test_the_rollup_files_a_settled_but_not_delivered_member_separately(project, svc) -> None:
    """A cancelled/superseded member delivered nothing and is not outstanding either — it is
    gone. Filing it under Outstanding is the defect this guards: a milestone holding only a
    delivered and a settled-but-not-delivered member must still report zero outstanding."""
    m = await _milestone(svc)
    delivered_decision = (await create_item(svc, "decision", "Accepted decision")).item
    await svc.add_ref(delivered_decision.id, m.id, kind="targets")
    await svc.set_status(delivered_decision.id, "Accepted")

    cancelled_bug = (await create_item(svc, "bug", "Dropped bug")).item
    await svc.add_ref(cancelled_bug.id, m.id, kind="targets")
    await svc.set_status(cancelled_bug.id, "Cancelled")

    rendered = await svc.render_view("milestone_rollup", m.id)
    assert "## Delivered (1)" in rendered
    assert "## Outstanding (0)" in rendered
    assert "## Settled without delivering (1)" in rendered
    delivered_section, rest = rendered.split("## Outstanding")
    outstanding_section, settled_section = rest.split("## Settled without delivering")
    assert delivered_decision.id in delivered_section
    assert cancelled_bug.id not in delivered_section
    assert cancelled_bug.id not in outstanding_section
    assert cancelled_bug.id in settled_section


async def test_the_rollup_is_never_written_to_the_milestone_file_and_is_computed_fresh(
    project, svc
) -> None:
    m = await _milestone(svc)
    before = await _file_bytes(project, m)
    task = (await create_item(svc, "task", "Fresh work")).item
    await svc.add_ref(task.id, m.id, kind="targets")

    rendered_first = await svc.render_view("milestone_rollup", m.id)
    assert task.id in rendered_first
    assert await _file_bytes(project, m) == before

    await svc.set_status(task.id, "Ready")
    await svc.set_status(task.id, "InProgress")
    await svc.set_status(task.id, "Done")
    rendered_second = await svc.render_view("milestone_rollup", m.id)
    assert rendered_first != rendered_second  # re-computed, not cached
    assert await _file_bytes(project, m) == before


async def test_json_emits_the_same_records_as_records_with_no_presentation_output(svc) -> None:
    m = await _milestone(svc)
    task = (await create_item(svc, "task", "Counted work")).item
    await svc.add_ref(task.id, m.id, kind="targets")

    projection = await svc.resolve_view("milestone_rollup", m.id)
    payload = projection_json(projection)
    groups = cast("list[dict[str, object]]", payload["groups"])
    all_ids = {
        cast("dict[str, object]", rec)["id"]
        for g in groups
        for rec in cast("list[object]", g["records"])
    }
    assert all_ids == {task.id}
    assert "## Outstanding" not in str(payload)


# --------------------------------------------------------------------------- adopter override


async def test_a_project_template_override_of_the_rollup_wins_on_milestone_show(
    project, svc
) -> None:
    from squads._rendering._engine import invalidate_squad_dir

    m = await _milestone(svc)
    task = (await create_item(svc, "task", "Overridden rendering")).item
    await svc.add_ref(task.id, m.id, kind="targets")

    override_path = (
        project.squad_dir / ".overrides" / "templates" / "views" / "milestone_rollup.md.j2"
    )
    override_path.parent.mkdir(parents=True, exist_ok=True)
    override_path.write_text(
        "PROJECT ROLLUP\n"
        "{% for group in groups %}{% for record in group.records %}"
        "{{ record.values['id'].text }}!\n{% endfor %}{% endfor %}",
        encoding="utf-8",
    )
    invalidate_squad_dir(project.squad_dir)

    rendered = await svc.render_view("milestone_rollup", m.id)
    assert "PROJECT ROLLUP" in rendered
    assert f"{task.id}!" in rendered
    assert "## Delivered" not in rendered
