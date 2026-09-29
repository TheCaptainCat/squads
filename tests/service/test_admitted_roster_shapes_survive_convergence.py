"""A document whose roster classification is absent takes an ordinary authored write that
survives every convergence pass untouched, and once the classification returns, the write
refusal reapplies with the prose left exactly as it was."""

from pathlib import Path

import pytest

from squads import __version__
from squads._errors import SquadsError
from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._sections import get_section
from squads._services import _service as service
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio

_AUTHORED_PROSE = "A hand-authored definition, written while the classification did not apply."

_DROP_SQUADS_SKILL_VIEW = """\
[selected]
views = ["milestone_rollup", "role_definition", "greeting_skill", "memory_skill", "item_skill"]
"""

_DROP_BUG_TYPE = """\
[selected]
items = [
  "epic", "feature", "task", "decision", "contract", "milestone",
  "review", "role", "skill", "operator",
]
"""

_WIDGET_TYPE = """\
[lifecycles.widget]
initial = "Open"
[lifecycles.widget.transitions]
Open = ["Done"]
Done = []

[items.widget]
prefix = "WID"
folder = "widgets"
lifecycle = "widget"
"""


def _write_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{content}", encoding="utf-8"
    )


def _reopen(paths) -> service.Service:
    return service.Service(paths, spec=load_workflow_spec(squad_dir=paths.squad_dir))


def _region(path: Path) -> str:
    return (get_section(path.read_text(encoding="utf-8"), markers.BODY) or "").strip()


async def _drift_the_stamp(paths) -> None:
    cfg_path = paths.config_path
    text = cfg_path.read_text(encoding="utf-8")
    cfg_path.write_text(
        text.replace(f'squads_version = "{__version__}"', 'squads_version = "0.1.0"'),
        encoding="utf-8",
    )


async def test_a_permanently_system_skills_dropped_view_round_trip(svc) -> None:
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", "squads")
    assert skill is not None
    path = item_file(svc.paths, skill)

    _write_override(svc.paths.squad_dir, _DROP_SQUADS_SKILL_VIEW)
    dropped = _reopen(svc.paths)
    await dropped.set_body(skill.id, _AUTHORED_PROSE)
    region = _region(path)
    assert region.startswith(_AUTHORED_PROSE)
    assert region.endswith(markers.open_marker(markers.view_tag("squads_skill")))

    before = _region(path)
    await dropped.repair()
    assert _region(path) == before, "sq repair rewrote the authored body"

    await _drift_the_stamp(dropped.paths)
    await service.Service(dropped.paths, spec=dropped.spec).sync()
    assert _region(path) == before, "the version-drift backfill rewrote the authored body"

    (svc.paths.squad_dir / ".overrides" / "workflow.toml").unlink()
    redeclared = service.Service(svc.paths)
    with pytest.raises(SquadsError, match="renders through its declared sq:view:"):
        await redeclared.set_body(skill.id, "a second, doomed write")
    assert _region(path) == before, "the refused write must not have touched the prose"
    assert [i for i in await redeclared.check() if i.item == skill.id] == []


async def test_a_stale_bundled_sq_bug_after_its_type_is_dropped_round_trip(svc) -> None:
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", "sq-bug")
    assert skill is not None
    path = item_file(svc.paths, skill)

    _write_override(svc.paths.squad_dir, _DROP_BUG_TYPE)
    dropped = _reopen(svc.paths)
    await dropped.set_body(skill.id, _AUTHORED_PROSE)
    region = _region(path)
    assert region.startswith(_AUTHORED_PROSE)
    assert region.endswith(markers.open_marker(markers.view_tag("item_skill")))

    before = _region(path)
    await dropped.repair()
    assert _region(path) == before, "sq repair rewrote the authored body"

    await _drift_the_stamp(dropped.paths)
    await service.Service(dropped.paths, spec=dropped.spec).sync()
    assert _region(path) == before, "the version-drift backfill rewrote the authored body"

    (svc.paths.squad_dir / ".overrides" / "workflow.toml").unlink()
    redeclared = service.Service(svc.paths)
    with pytest.raises(SquadsError, match="renders through its declared sq:view:"):
        await redeclared.set_body(skill.id, "a second, doomed write")
    assert _region(path) == before, "the refused write must not have touched the prose"

    warnings = [i for i in await redeclared.check() if i.level == "warn"]
    assert any(
        "documents declared type 'bug'" in i.message and "item_skill" in i.message for i in warnings
    ), [i.message for i in warnings]


async def test_a_project_declared_types_stale_sq_widget_round_trip(svc) -> None:
    """A skill authored before its slug's type is declared survives, then reports shadowed
    once the type is declared."""
    skill = await svc.add_skill("sq-widget", description="A hand-authored runbook.")
    await svc.set_body(skill.id, _AUTHORED_PROSE)
    path = item_file(svc.paths, skill)
    assert _region(path) == _AUTHORED_PROSE

    before = _region(path)
    await svc.repair()
    assert _region(path) == before, "sq repair rewrote an authored custom-skill body"

    await _drift_the_stamp(svc.paths)
    await service.Service(svc.paths).sync()
    assert _region(path) == before, "the version-drift backfill rewrote an authored body"

    _write_override(svc.paths.squad_dir, _WIDGET_TYPE)
    declared = _reopen(svc.paths)
    with pytest.raises(SquadsError, match="renders through its declared sq:view:"):
        await declared.set_body(skill.id, "a second, doomed write")
    assert _region(path) == before, "the refused write must not have touched the prose"

    warnings = [i for i in await declared.check() if i.level == "warn"]
    assert any(
        "documents declared type 'widget'" in i.message and "authored content" in i.message
        for i in warnings
    ), [i.message for i in warnings]
