"""Declared vocabulary is validated against the scope that declares it, not against a global
set — for a badge field's collection and for an entity's status alike.

One mechanism, two symptoms. The load boundary read a stored badge value with a dynamic
attribute lookup keyed on the field's own code, so it saw only the codes that happen to be real
model attributes (``priority``, ``severity``) and silently skipped every adopter-declared one,
whose value lives in the generic ``extra`` store. Driven as an asymmetry on the same operation:
shrinking the bundled ``priority`` collection under a live item made every command exit 1
naming it; shrinking an override-declared ``impact`` collection left everything at exit 0
forever, with the item keeping an undeclared code.

The status half is the same shape one level up: ``sq workflow lint`` judged a status against
the flat, spec-wide status set instead of the lifecycle the entity is actually driven by, so an
item or sub-entity parked on a state its own machine cannot reach passed lint clean while
``sq check`` — which has always asked per lifecycle — called it an error. That one stays a
*report* on both planes rather than becoming a load refusal: the remedy is a per-item ``--force``
move, which is only reachable while commands still run.
"""

from pathlib import Path

import pytest

from squads import __version__

pytestmark = pytest.mark.anyio

_DECLARES_IMPACT = """\
[collections.impact]
label = "Impact"
ordered = true
default = "medium"
badges = [
  { code = "low", label = "Low" },
  { code = "medium", label = "Medium" },
  { code = "high", label = "High" },
]

[items.bug]
fields = [
  { code = "priority", label = "Priority", collection = "priority" },
  { code = "impact", label = "Impact", collection = "impact", default = "medium" },
]
"""

#: The same declaration with `high` removed — the code a live item already carries.
_SHRINKS_IMPACT = _DECLARES_IMPACT.replace('  { code = "high", label = "High" },\n', "")

_SUBTASK_MACHINE_WITHOUT_TODO = """\
[statuses.Pending]
role = "pending"
[statuses.Doing]
role = "active"
[statuses.Complete]
role = "done"

[subentity_kinds.subtask]
lifecycle = "custom_subtask"
completion = "Complete"

[lifecycles.custom_subtask]
initial = "Pending"

[lifecycles.custom_subtask.transitions]
Pending = ["Doing"]
Doing = ["Complete"]
Complete = []
"""


def _write_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{content}", encoding="utf-8"
    )
    from squads._workflow._loader import load_workflow_spec

    load_workflow_spec(squad_dir=squad_dir)  # loud setup: an unloadable fixture proves nothing


async def _bug_carrying_impact(project, invoke) -> str:
    _write_override(project.squad_dir, _DECLARES_IMPACT)
    from squads._services import _service as service

    svc = service.open_service()
    bug = (await svc.create("bug", "Impactful", author="manager", priority="urgent")).item
    setter = await invoke(["bug", str(bug.sequence_id), "update", "--set", "impact=high"])
    assert setter.exit_code == 0, setter.output
    return bug.id


async def test_shrinking_an_adopter_declared_collection_is_caught_at_the_load_boundary(
    project, invoke
) -> None:
    bug_id = await _bug_carrying_impact(project, invoke)

    _write_override(project.squad_dir, _SHRINKS_IMPACT)
    result = await invoke(["list", "-a"])

    assert result.exit_code != 0, result.output
    assert bug_id in result.output
    assert "impact" in result.output


async def test_the_bundled_and_declared_axes_now_behave_the_same_way(project, invoke) -> None:
    """The asymmetry itself, driven as a comparison rather than as two separate expectations —
    that is what made the gap invisible: each axis looked fine on its own."""
    bug_id = await _bug_carrying_impact(project, invoke)

    _write_override(project.squad_dir, _SHRINKS_IMPACT)
    declared_axis = await invoke(["list", "-a"])

    _write_override(
        project.squad_dir,
        '[collections.priority]\nlabel = "Priority"\nordered = true\n'
        'badges = [{ code = "low", label = "Low" }]\n',
    )
    bundled_axis = await invoke(["list", "-a"])

    assert declared_axis.exit_code == bundled_axis.exit_code != 0
    assert bug_id in declared_axis.output


async def test_a_still_declared_code_is_left_alone(project, invoke) -> None:
    """The control: the check must fire on the *removal*, not on the field being adopter-
    declared. Without this, refusing every custom field would pass the two tests above."""
    await _bug_carrying_impact(project, invoke)

    result = await invoke(["list", "-a"])

    assert result.exit_code == 0, result.output


async def test_lint_reports_a_subentity_resting_on_an_unreachable_status(
    project, svc, invoke
) -> None:
    task = (await svc.create("task", "Auth", author="manager")).item
    await svc.add_subtask(task.id, "Validate")
    _write_override(project.squad_dir, _SUBTASK_MACHINE_WITHOUT_TODO)

    lint = await invoke(["workflow", "lint"])

    assert lint.exit_code == 1
    flat = lint.output.replace("\n", " ")
    assert task.id in flat
    assert "custom_subtask" in flat


async def test_check_and_lint_agree_about_the_same_corpus(project, svc, invoke) -> None:
    """The disagreement is the defect: one gate calling a corpus clean while the other calls the
    same item an error is what makes a report unreadable."""
    task = (await svc.create("task", "Auth", author="manager")).item
    await svc.add_subtask(task.id, "Validate")
    _write_override(project.squad_dir, _SUBTASK_MACHINE_WITHOUT_TODO)

    assert (await invoke(["workflow", "lint"])).exit_code == 1
    assert (await invoke(["check"])).exit_code == 3


async def test_an_unreachable_status_is_reported_not_refused_at_load(project, svc, invoke) -> None:
    """The remedy is a per-item ``--force`` move, so the tool has to keep working: making this a
    fail-closed clause would leave the item unfixable from inside ``sq``."""
    task = (await svc.create("task", "Auth", author="manager")).item
    await svc.add_subtask(task.id, "Validate")
    _write_override(project.squad_dir, _SUBTASK_MACHINE_WITHOUT_TODO)

    listing = await invoke(["list", "-a"])
    assert listing.exit_code == 0, listing.output

    moved = await invoke(
        ["task", str(task.sequence_id), "subtask", "ST1", "update", "--status", "Doing", "--force"]
    )
    assert moved.exit_code == 0, moved.output
    assert (await invoke(["workflow", "lint"])).exit_code == 0
