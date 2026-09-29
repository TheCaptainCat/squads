"""A custom skill's body is storage and survives untouched; a system skill's is not stored at
all — proven against a fixture where the folder, item type, and ``sq-`` prefix all pick the
wrong classification, so only ``is_system_skill`` gets it right."""

from pathlib import Path

import pytest

from squads import _sections as sections
from squads._errors import SquadsError
from squads._interactions import is_system_skill
from squads._models import _markers as markers
from squads._services import _service as service
from squads._workflow._loader import load_workflow_spec

pytestmark = pytest.mark.anyio

#: An adopter-declared type: no bundled playbook entry, so its ``sq-incident`` skill is the
#: *thin* branch of the system render — the per-type case furthest from a bundled skill.
_INCIDENT_TOML = """\
[lifecycles.triage]
initial = "Open"
[lifecycles.triage.transitions]
Open = ["Done"]
Done = []

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "triage"
"""

_AUTHORED = "## Instructions\n\nCut the branch, tag it, then publish."
_AUTHORED_SQ = "## Instructions\n\nDay one: read the guides, then shadow a review."


def _write_override(squad_dir: Path) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(_INCIDENT_TOML, encoding="utf-8")


@pytest.fixture
async def squad(tmp_path, monkeypatch, frozen_time):
    """A synced squad with bundled system skills, an adopter type's thin system skill, and two
    custom skills (one ``sq-``-prefixed) carrying authored bodies."""
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal")
    _write_override(result.paths.squad_dir)
    svc = service.Service(result.paths, spec=load_workflow_spec(squad_dir=result.paths.squad_dir))
    await svc.sync()

    runbook = await svc.add_skill("Release Runbook", description="Ship a release safely.")
    await svc.set_body(runbook.id, _AUTHORED)
    onboarding = await svc.add_skill("sq-onboarding", description="Get a new agent productive.")
    await svc.set_body(onboarding.id, _AUTHORED_SQ)
    return svc, runbook, onboarding


async def test_the_two_custom_skills_are_classified_custom_and_the_declared_types_skill_system(
    squad,
):
    """Both custom skills classify custom and the declared type's skill classifies system."""
    svc, _runbook, _onboarding = squad
    assert not is_system_skill("release-runbook", svc.spec)
    assert not is_system_skill("sq-onboarding", svc.spec)
    assert is_system_skill("sq-incident", svc.spec)
    assert is_system_skill("squads", svc.spec)


async def test_an_authored_body_is_byte_identical_across_one_sync_and_across_two(squad):
    svc, runbook, onboarding = squad

    await svc.sync()
    assert await svc.read_body(runbook.id) == _AUTHORED
    assert await svc.read_body(onboarding.id) == _AUTHORED_SQ

    await svc.sync()
    assert await svc.read_body(runbook.id) == _AUTHORED
    assert await svc.read_body(onboarding.id) == _AUTHORED_SQ


async def test_a_custom_skills_whole_file_is_untouched_by_a_sync(squad):
    """The ``sq-``-prefixed custom skill's whole file, byte for byte, survives a sync."""
    svc, _runbook, onboarding = squad
    path = svc.paths.abspath((await svc.get(onboarding.id)).path)
    before = path.read_text(encoding="utf-8")

    await svc.sync()

    assert path.read_text(encoding="utf-8") == before


async def test_a_body_write_is_still_admitted_on_a_custom_skill_and_survives_the_next_sync(squad):
    svc, _runbook, onboarding = squad
    revised = _AUTHORED_SQ + "\n\nWeek one: take a small task end to end."
    await svc.set_body(onboarding.id, revised, force=True)

    await svc.sync()

    assert await svc.read_body(onboarding.id) == revised


async def test_a_body_write_is_refused_on_the_declared_types_thin_system_skill(squad):
    """A declared type's skill with no playbook entry at all is still template-owned."""
    svc, _runbook, _onboarding = squad
    incident = await svc.roster_item("skill", "sq-incident")
    assert incident is not None, "the declared type's skill must have been seeded"

    with pytest.raises(SquadsError, match="renders through its declared sq:view:") as exc:
        await svc.set_body(incident.id, "free-form body")
    assert "`.overrides/playbook.toml`" in str(exc.value)
    assert "Drop the view from `[selected]`" in str(exc.value)


async def test_a_custom_slugs_body_reads_as_authored_and_the_declared_types_skill_reads_thin(
    squad,
):
    svc, _runbook, onboarding = squad

    assert await svc.read_body(onboarding.id) == _AUTHORED_SQ

    incident = await svc.roster_item("skill", "sq-incident")
    assert incident is not None
    thin = await svc.read_body(incident.id)
    assert "Open → Done" in thin
    assert "## For " not in thin


async def test_show_prints_the_authored_text_for_one_and_the_rendered_text_for_the_other(
    squad, invoke
):
    """The authored/rendered branch selects per skill, not per squad, in one run."""
    svc, _runbook, _onboarding = squad
    incident = await svc.roster_item("skill", "sq-incident")
    assert incident is not None

    authored = await invoke(["skill", "sq-onboarding", "show", "--raw"])
    assert authored.exit_code == 0, authored.output
    assert "custom (authored)" in authored.output
    assert "shadow a review" in authored.output

    rendered = await invoke(["skill", "sq-incident", "show", "--raw"])
    assert rendered.exit_code == 0, rendered.output
    assert "system (template-owned)" in rendered.output
    assert "Open → Done" in rendered.output
    stored = svc.paths.abspath(incident.path).read_text(encoding="utf-8")
    region = (sections.get_section(stored, markers.BODY) or "").strip("\n")
    assert region == markers.open_marker(markers.view_tag("item_skill"))
