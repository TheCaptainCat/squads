"""A project-defined (not bundled) role, activated on the live roster via the shipped
``sq override scaffold --new`` / ``sq role activate`` path, must be nameable in a playbook
override's ``roles`` array end to end: ``sq check`` accepts it, and the generated skill body
actually carries that role's section.

Reproduces the mechanism by which a custom role is meant to enter a type's playbook guidance,
exactly the way it was driven end to end: a wholly-new
role slug (not the bundled catalog, not the ``*dev`` sentinel) given guidance for one type via
the ``$(*self)`` append idiom.
"""

from pathlib import Path

import pytest

from _helpers import add_role_from_file, resolved_skill_definition, write_role_file
from squads._interactions._skills import item_skill_name
from squads._services import _service as service

pytestmark = pytest.mark.anyio


def _write_playbook_override(squad_dir: Path, content: str) -> None:
    from squads import __version__

    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    stamped = f"# squads:override-base:{__version__}\n{content}"
    (override_dir / "playbook.toml").write_text(stamped, encoding="utf-8")


_GIVE_SRE_TASK_GUIDANCE = """
[types.task]
roles = [
    "$(*self)",
    { slug = "sre", enter = ["Read the incident timeline"], do = ["Coordinate the rollback"] },
]
"""


async def test_check_accepts_a_playbook_guide_for_a_live_project_role(project) -> None:
    write_role_file(project.squad_dir, "sre")

    svc = service.open_service(client_cwd=project.squad_dir)
    await add_role_from_file(svc, "sre")

    _write_playbook_override(project.squad_dir, _GIVE_SRE_TASK_GUIDANCE)

    # Reopening must not raise PlaybookConfigError (or anything else) — the project role's
    # slug is now a valid playbook-guide slug because it has a live override file on disk.
    reopened = service.open_service(client_cwd=project.squad_dir)
    findings = await reopened.check()
    assert not any("playbook" in f.item or "catalog" in f.message for f in findings)


async def test_generated_task_skill_carries_the_project_roles_guidance(project) -> None:
    """Not just accepted — actually usable: the generated ``sq-task`` skill renders a real
    section for the project role, resolved off the live roster (full name + guide text)."""
    write_role_file(project.squad_dir, "sre")

    svc = service.open_service(client_cwd=project.squad_dir)
    await add_role_from_file(svc, "sre")

    _write_playbook_override(project.squad_dir, _GIVE_SRE_TASK_GUIDANCE)

    reopened = service.open_service(client_cwd=project.squad_dir)
    await reopened.refresh_managed()

    body = await resolved_skill_definition(reopened, item_skill_name("task"))
    assert "Sam Reliability" in body
    assert "Read the incident timeline" in body
    assert "Coordinate the rollback" in body


async def test_an_explicit_dev_tech_slug_is_accepted_once_the_developer_exists(
    project, svc
) -> None:
    """Two developers can get distinct playbook guidance: a guide naming a developer's slug loads
    and, with that developer live, is not reported."""
    await svc.activate_role(None, from_template="dev", tech="python")

    _write_playbook_override(
        project.squad_dir,
        """
[types.task]
roles = [
    "$(*self)",
    { slug = "python-dev", enter = ["Read the task body"], do = ["Ship the fix"] },
]
""",
    )

    reopened = service.open_service(client_cwd=project.squad_dir)
    findings = await reopened.check()
    assert not any("playbook" in f.item or "catalog" in f.message for f in findings)


async def test_a_guide_naming_a_dev_slug_with_no_role_loads_and_is_reported_by_check(
    project,
) -> None:
    """The loader no longer decides whether a role holds a guide's slug: it loads, and `sq
    check` warns that the guide names no live role."""
    _write_playbook_override(
        project.squad_dir,
        """
[types.task]
roles = [
    "$(*self)",
    { slug = "python-dev", enter = ["x"], do = ["y"] },
]
""",
    )

    reopened = service.open_service(client_cwd=project.squad_dir)
    findings = await reopened.check()

    assert any(
        f.rule == "playbook_guide_role_live" and "'python-dev'" in f.message for f in findings
    )
