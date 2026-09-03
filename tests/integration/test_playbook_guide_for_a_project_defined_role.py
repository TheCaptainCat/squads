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

from squads import _interactions as interactions
from squads._overrides._service import scaffold_new_role
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


def _fill_in_role_stub(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        'full_name = "TODO: full name (e.g. \\"Sam Security\\")"',
        'full_name = "Sam Reliability"',
    )
    text = text.replace(
        'title = "TODO: one-line title (e.g. \\"security analyst\\")"', 'title = "SRE"'
    )
    text = text.replace(
        'description = "TODO: one-line description for the Claude pointer frontmatter"',
        'description = "Keeps the lights on."',
    )
    text = text.replace(
        'mission = "TODO: what this role is responsible for accomplishing"',
        'mission = "Own incident response and rollback."',
    )
    path.write_text(text, encoding="utf-8")


async def test_check_accepts_a_playbook_guide_for_a_live_project_role(project) -> None:
    role_toml = scaffold_new_role(project.squad_dir, slug="sre")
    _fill_in_role_stub(role_toml)

    svc = service.open_service(dir_override=str(project.squad_dir))
    await svc.activate_role("sre")

    _write_playbook_override(project.squad_dir, _GIVE_SRE_TASK_GUIDANCE)

    # Reopening must not raise PlaybookConfigError (or anything else) — the project role's
    # slug is now a valid playbook-guide slug because it has a live override file on disk.
    reopened = service.open_service(dir_override=str(project.squad_dir))
    findings = await reopened.check()
    assert not any("playbook" in f.item or "catalog" in f.message for f in findings)


async def test_generated_task_skill_carries_the_project_roles_guidance(project) -> None:
    """Not just accepted — actually usable: the generated ``sq-task`` skill renders a real
    section for the project role, resolved off the live roster (full name + guide text)."""
    role_toml = scaffold_new_role(project.squad_dir, slug="sre")
    _fill_in_role_stub(role_toml)

    svc = service.open_service(dir_override=str(project.squad_dir))
    await svc.activate_role("sre")

    _write_playbook_override(project.squad_dir, _GIVE_SRE_TASK_GUIDANCE)

    reopened = service.open_service(dir_override=str(project.squad_dir))
    await reopened.refresh_managed()

    body = await reopened.skill_definition_text(interactions.item_skill_name("task"))
    assert "Sam Reliability" in body
    assert "Read the incident timeline" in body
    assert "Coordinate the rollback" in body


async def test_an_explicit_dev_tech_slug_is_also_accepted_once_it_has_an_override_file(
    project,
) -> None:
    """The same root cause blocked an explicit ``<tech>-dev`` slug too (``*dev`` being
    all-or-nothing). A dev slug is generated on the fly with no override file by default, but
    once a project creates one — even a near-empty customisation — the union picks it up the
    same way, so two devs CAN get distinct playbook guidance."""
    overrides_dir = project.squad_dir / ".overrides" / "roles"
    overrides_dir.mkdir(parents=True, exist_ok=True)
    (overrides_dir / "python-dev.toml").write_text('color = "green"\n', encoding="utf-8")

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

    reopened = service.open_service(dir_override=str(project.squad_dir))
    findings = await reopened.check()
    assert not any("playbook" in f.item or "catalog" in f.message for f in findings)


async def test_an_explicit_dev_tech_slug_with_no_override_file_is_still_refused(project) -> None:
    """The boundary the fix does NOT cross: a generated dev slug with no override file on
    disk is not a live, discoverable project role — refusing it is still correct, and the
    refusal must remain the same clear catalog message, not a crash."""
    from squads._errors import PlaybookConfigError

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

    with pytest.raises(PlaybookConfigError) as exc_info:
        service.open_service(dir_override=str(project.squad_dir))
    assert "role slug 'python-dev' not in role catalog" in str(exc_info.value)
