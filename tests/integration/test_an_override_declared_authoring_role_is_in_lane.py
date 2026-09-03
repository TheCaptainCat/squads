"""The advisory create-lane follows the ACTIVE playbook, so the tool never contradicts the
instructions it just generated.

The create-lane used to live in a hand-maintained slug→type map beside the playbook, with no
override seam and its own module-level singleton of laned types computed at import. Two
consequences, both driven here:

* a project that declared an authoring role through ``.overrides/playbook.toml`` got a generated
  ``sq-<type>`` skill containing the exact ``sq create`` command, and running that command
  printed an advisory saying the role was not the in-lane author for it;
* a type the project declared (or renamed into) was never in the laned set at all, so the check
  short-circuited and lane discipline went dark for it — no advisory ever, for anyone.

Both directions are asserted: the declaration silences the advisory, and its absence still
raises one. The control cases keep the bundled behaviour pinned.
"""

from pathlib import Path

import pytest

from squads._services import _service as service

pytestmark = pytest.mark.anyio


def _write_playbook_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "playbook.toml").write_text(content, encoding="utf-8")


#: ``devops`` has no bundled guide on ``bug`` at all, so this ADDS a guide rather than
#: restating one — the shape an adopter writes to put a role of theirs in a lane.
_DEVOPS_AUTHORS_BUGS = """
[types.bug]
roles = [
    "$(*self)",
    { slug = "devops", authors = true, do = ["file the incident as a bug"] },
]
"""

#: The same guide WITHOUT the declaration — the control that proves it is the flag doing the
#: work, not merely the presence of a guide.
_DEVOPS_ONLY_READS_BUGS = """
[types.bug]
roles = [
    "$(*self)",
    { slug = "devops", do = ["read the incident's bug"] },
]
"""


async def test_an_override_declared_authoring_role_creates_in_lane(project) -> None:
    _write_playbook_override(project.squad_dir, _DEVOPS_AUTHORS_BUGS)
    svc = service.open_service()
    await svc.activate_role("devops")
    res = await svc.create("bug", "Deploy wedges on rollback", author="devops")
    assert res.lane_warning is None


async def test_the_same_guide_without_the_declaration_still_warns(project) -> None:
    _write_playbook_override(project.squad_dir, _DEVOPS_ONLY_READS_BUGS)
    svc = service.open_service()
    await svc.activate_role("devops")
    res = await svc.create("bug", "Deploy wedges on rollback", author="devops")
    assert res.lane_warning is not None
    assert "devops" in res.lane_warning
    assert "qa" in res.lane_warning  # the bundled author is still named as expected


async def test_the_declaration_does_not_displace_the_bundled_author(project) -> None:
    """Adding a lane is additive: the bundled in-lane author keeps its own lane."""
    _write_playbook_override(project.squad_dir, _DEVOPS_AUTHORS_BUGS)
    svc = service.open_service()
    await svc.activate_role("qa")
    res = await svc.create("bug", "Login rejects a valid password", author="qa")
    assert res.lane_warning is None


async def test_with_no_override_the_bundled_lane_is_unchanged(project, svc) -> None:
    """The control: the same squad with no override warns for devops and not for qa."""
    await svc.activate_role("devops")
    await svc.activate_role("qa")
    warned = await svc.create("bug", "Deploy wedges on rollback", author="devops")
    assert warned.lane_warning is not None
    clean = await svc.create("bug", "Login rejects a valid password", author="qa")
    assert clean.lane_warning is None


async def test_the_advisory_reaches_the_cli_and_the_declaration_silences_it(
    project, invoke
) -> None:
    """End to end through `sq create`, because the advisory is a printed line, not a value."""
    await service.open_service().activate_role("qa")
    in_lane = await invoke(["create", "bug", "Deploy wedges", "--author", "qa"])
    assert in_lane.exit_code == 0
    assert "in-lane author" not in in_lane.output

    _write_playbook_override(project.squad_dir, _DEVOPS_ONLY_READS_BUGS)
    svc = service.open_service()
    await svc.activate_role("devops")
    still_warned = await invoke(["create", "bug", "Deploy wedges again", "--author", "devops"])
    assert still_warned.exit_code == 0
    assert "is not the in-lane author" in still_warned.output

    _write_playbook_override(project.squad_dir, _DEVOPS_AUTHORS_BUGS)
    silenced = await invoke(["create", "bug", "Deploy wedges once more", "--author", "devops"])
    assert silenced.exit_code == 0
    assert "in-lane author" not in silenced.output


async def test_the_generated_skill_and_the_lane_check_agree(project) -> None:
    """The contradiction itself: the generated guidance tells devops to run the create command,
    so running it must not be answered with 'you are not the in-lane author'."""
    _write_playbook_override(project.squad_dir, _DEVOPS_AUTHORS_BUGS)
    svc = service.open_service()
    await svc.activate_role("devops")
    await svc.refresh_managed()

    body = await svc.skill_definition_text("sq-bug")
    assert "file the incident as a bug" in body  # the generated instruction

    res = await svc.create("bug", "Deploy wedges on rollback", author="devops")
    assert res.lane_warning is None  # and the tool does not contradict it


#: A project-declared type. Before the lane derivation followed the playbook, a type like this
#: could never enter the laned set at all — it was a frozenset computed at import off the
#: bundled document — so no create of it was ever lane-checked, for any author.
_INCIDENT_TYPE = """
[statuses.Triage]
[statuses.Resolved]
role = "done"

[lifecycles.incident_lc]
initial = "Triage"
[lifecycles.incident_lc.transitions]
Triage = ["Resolved"]
Resolved = []

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "incident_lc"
"""

_QA_AUTHORS_INCIDENTS = """
[types.incident]
overview = "An operational incident."
lifecycle = "Triage → Resolved"
commands = ['sq create incident "…" --author qa']
roles = [
    { slug = "qa", authors = true, do = ['file it (`sq create incident "…" --author qa`)'] },
]
"""


def _write_workflow_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(content, encoding="utf-8")


async def test_a_project_declared_type_is_lane_checked_once_it_declares_an_author(
    project,
) -> None:
    _write_workflow_override(project.squad_dir, _INCIDENT_TYPE)
    _write_playbook_override(project.squad_dir, _QA_AUTHORS_INCIDENTS)
    svc = service.open_service()
    await svc.activate_role("qa")
    await svc.activate_role("devops")

    in_lane = await svc.create("incident", "Region us-east is down", author="qa")
    assert in_lane.lane_warning is None

    out_of_lane = await svc.create("incident", "Queue backed up", author="devops")
    assert out_of_lane.lane_warning is not None
    assert "incident" in out_of_lane.lane_warning
    assert "qa" in out_of_lane.lane_warning


async def test_a_project_declared_type_with_no_declared_author_is_not_lane_checked(
    project,
) -> None:
    """The complement, and the reason the check is gated on the type at all: a type nobody is
    declared to author has no lane to be out of, so nobody is warned about it."""
    _write_workflow_override(project.squad_dir, _INCIDENT_TYPE)
    svc = service.open_service()
    await svc.activate_role("devops")
    res = await svc.create("incident", "Queue backed up", author="devops")
    assert res.lane_warning is None
