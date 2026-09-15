"""``MaintenanceMixin._repair_body_tag``'s role and system-skill branches, gated on
``self.spec.views`` the same way the per-item-type branch already gates on the declared type.

Dropping ``role_definition`` via a ``.overrides/workflow.toml`` ``[selected]`` block is ordinary,
supported customisation — an adopter is free to decide the mechanism does not apply to them. What
must not happen is the classifier naming a tag for that undeclared view against a body that is
not already carrying one: an empty or freshly-created body under a dropped view must stay empty,
not be seeded with a tag `sq check`'s own dangling-tag rule would then flag on a file the adopter
never touched. An already-tagged body is a separate, accepted case — a tag valid when placed and
no longer valid stays visible rather than being stripped, relocated, or repaired — and is
untouched either way, gated or not — this module's tests are all about the *empty* body, where
the gate is the only thing that decides whether a fresh dangling tag gets created.
"""

from pathlib import Path

import pytest

from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._sections import get_section, replace_section
from squads._services import _service as service
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio

#: Drops `role_definition` from the declared view set. Every other bundled view stays selected,
#: including `milestone_rollup` — a type-owned view still attached via `items.milestone.views`,
#: which would otherwise be refused at load as a dangling attachment (a different failure mode
#: this test does not want to exercise).
_DROP_ROLE_DEFINITION = """\
[selected]
views = ["milestone_rollup", "squads_skill", "greeting_skill", "memory_skill", "item_skill"]
"""


def _write_override(squad_dir: Path, content: str) -> None:
    from squads import __version__

    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{content}", encoding="utf-8"
    )


def _empty_role_body(svc, path: Path) -> None:
    text = replace_section(path.read_text(encoding="utf-8"), markers.BODY, "")
    path.write_text(text, encoding="utf-8")


async def test_role_definition_is_dropped_from_the_active_spec(svc) -> None:
    """Precondition, driven: the override really does remove the view."""
    _write_override(svc.paths.squad_dir, _DROP_ROLE_DEFINITION)
    spec = load_workflow_spec(squad_dir=svc.paths.squad_dir)
    assert "role_definition" not in spec.views


@pytest.mark.gate_for("squads/_services/_maintenance.py::_converge_body_tag")
async def test_the_classifier_declines_a_role_under_a_dropped_view(svc) -> None:
    _write_override(svc.paths.squad_dir, _DROP_ROLE_DEFINITION)
    spec = load_workflow_spec(squad_dir=svc.paths.squad_dir)
    declared = service.Service(svc.paths, spec=spec)
    role = await declared.roster_item("role", "manager") or await declared.activate_role("manager")

    assert declared._repair_body_tag(role) is None


async def test_an_empty_body_under_a_dropped_view_stays_empty_through_the_sweep(svc) -> None:
    """The end-to-end shape: an empty role body, the view dropped, ``sq repair`` run — the
    sweep must not seed a tag naming a view the active spec does not declare."""
    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    path = item_file(svc.paths, role)
    _empty_role_body(svc, path)
    assert not (get_section(path.read_text(encoding="utf-8"), markers.BODY) or "").strip()

    _write_override(svc.paths.squad_dir, _DROP_ROLE_DEFINITION)
    spec = load_workflow_spec(squad_dir=svc.paths.squad_dir)
    declared = service.Service(svc.paths, spec=spec)

    await declared.repair()

    region = (get_section(path.read_text(encoding="utf-8"), markers.BODY) or "").strip()
    assert region == "", "the sweep seeded a tag naming a view the spec no longer declares"


async def test_an_already_tagged_body_under_a_dropped_view_is_left_exactly_as_is(svc) -> None:
    """The companion case the gate does NOT change: a body that already carries the (now
    dangling) tag is untouched either way — `_converge_body_tag`'s own idempotent early return
    fires before the gate would ever matter. Recorded here so the two cases are not conflated:
    the gate protects against *seeding a new* dangling tag, not against an existing one."""
    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    path = item_file(svc.paths, role)
    before = path.read_bytes()

    _write_override(svc.paths.squad_dir, _DROP_ROLE_DEFINITION)
    spec = load_workflow_spec(squad_dir=svc.paths.squad_dir)
    declared = service.Service(svc.paths, spec=spec)

    await declared.repair()

    assert path.read_bytes() == before


#: Drops `squads_skill` instead of `role_definition` — the system-skill branch gets the same
#: gate, checked here so the two branches aren't only proven by one shared code path.
_DROP_SQUADS_SKILL = """\
[selected]
views = ["milestone_rollup", "role_definition", "greeting_skill", "memory_skill", "item_skill"]
"""


async def test_the_classifier_declines_a_system_skill_under_a_dropped_view(svc) -> None:
    await svc.seed_bundled_skills()
    _write_override(svc.paths.squad_dir, _DROP_SQUADS_SKILL)
    spec = load_workflow_spec(squad_dir=svc.paths.squad_dir)
    declared = service.Service(svc.paths, spec=spec)
    skill = await declared.roster_item("skill", "squads")
    assert skill is not None

    assert declared._repair_body_tag(skill) is None


async def test_an_empty_system_skill_body_under_a_dropped_view_stays_empty(svc) -> None:
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", "squads")
    assert skill is not None
    path = item_file(svc.paths, skill)
    _empty_role_body(svc, path)

    _write_override(svc.paths.squad_dir, _DROP_SQUADS_SKILL)
    spec = load_workflow_spec(squad_dir=svc.paths.squad_dir)
    declared = service.Service(svc.paths, spec=spec)

    await declared.repair()

    region = (get_section(path.read_text(encoding="utf-8"), markers.BODY) or "").strip()
    assert region == "", "the sweep seeded a tag naming a view the spec no longer declares"
