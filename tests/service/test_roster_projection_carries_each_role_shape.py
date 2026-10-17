"""The roster projection a backend compiles from: one row per role shape, each field of the
``RoleView`` ``Service.roster()`` returns, and the same for ``Service.operators()``."""

from dataclasses import asdict
from pathlib import Path

import pytest

from squads._paths import SquadPaths
from squads._services import _service as service

pytestmark = pytest.mark.anyio

_CUSTOM = (
    'title = "guardian"\n'
    'description = "Guards the gate."\n'
    'mission = "Guard the gate."\n'
    'responsibilities = ["Watch", "Ward"]\n'
    'full_name = "Gwen Guardian"\n'
    'capabilities = ["guard"]\n'
)


def _role_file(paths: SquadPaths, slug: str, body: str) -> Path:
    path = paths.squad_dir / ".overrides" / "roles" / f"{slug}.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


async def _fields(svc: service.Service, slug: str) -> dict[str, object]:
    return asdict(next(r for r in await svc.roster() if r.slug == slug))


async def test_a_bundled_role_projects_its_catalog_entry(svc):
    await svc.activate_role("architect")
    assert await _fields(svc, "architect") == {
        "slug": "architect",
        "full_name": "Robert Architect",
        "title": "architect",
        "is_default": False,
        "mission": "Own the system's shape: design coherent solutions, record decisions as ADRs, "
        "and guide implementation.",
        "responsibilities": (
            "Design components and their interactions",
            "Record significant design decisions (ADRs in the bundled workflow)",
            "Author cross-cutting guides",
            "Review designs before implementation",
        ),
        "capabilities": (),
        "pronouns": None,
    }


async def test_the_default_role_projects_as_default(svc):
    await svc.activate_role("manager")
    assert (await _fields(svc, "manager"))["is_default"] is True


async def test_a_per_slug_override_that_renames_a_bundled_role_reaches_the_projection(project, svc):
    await svc.activate_role("qa")
    _role_file(project, "qa", 'title = "Chief Verifier"\nfull_name = "Vera Verifier"\n')
    fields = await _fields(svc, "qa")
    # The item pins the name it was created with; the override renames the title.
    assert (fields["full_name"], fields["title"]) == ("Mara Tester", "Chief Verifier")
    assert fields["mission"] == (
        "Prove the software works: design test cases from user stories and verify fixes."
    )


async def test_a_templated_developer_projects_the_generated_definition(svc):
    await svc.add_dev("python")
    assert await _fields(svc, "python-dev") == {
        "slug": "python-dev",
        "full_name": "Elias Python",
        "title": "Python developer",
        "is_default": False,
        "mission": "Implement assigned tasks in Python, following the project's guides, "
        "with tests.",
        "responsibilities": (
            "Implement tasks in Python",
            "Write tests for changes",
            "Follow the relevant guides; ask the architect when unsure",
        ),
        "capabilities": ("dev",),
        "pronouns": None,
    }


async def test_a_project_role_declared_by_a_role_file_projects_that_file(project, svc):
    _role_file(project, "guardian", _CUSTOM)
    await svc.activate_role("guardian")
    assert await _fields(svc, "guardian") == {
        "slug": "guardian",
        "full_name": "Gwen Guardian",
        "title": "guardian",
        "is_default": False,
        "mission": "Guard the gate.",
        "responsibilities": ("Watch", "Ward"),
        "capabilities": ("guard",),
        "pronouns": None,
    }


async def test_a_role_whose_backing_definition_is_gone_projects_what_the_item_stored(project, svc):
    path = _role_file(project, "guardian", _CUSTOM)
    await svc.activate_role("guardian")
    path.unlink()
    assert await _fields(svc, "guardian") == {
        "slug": "guardian",
        "full_name": "Gwen Guardian",
        "title": "Gwen Guardian",
        "is_default": False,
        "mission": "Guard the gate.",
        "responsibilities": (),
        "capabilities": (),
        "pronouns": None,
    }


async def test_operators_project_slug_and_name_and_a_retired_one_leaves_the_live_list(svc):
    await svc.add_operator("Alice Tester")
    bob = await svc.add_operator("Bob Gone")
    assert [asdict(o) for o in await svc.operators()] == [
        {"slug": "op-alice", "full_name": "Alice Tester", "pronouns": None},
        {"slug": "op-bob", "full_name": "Bob Gone", "pronouns": None},
    ]
    await svc.set_status(bob.id, "Archived")
    assert [o.slug for o in await svc.operators()] == ["op-alice"]
    assert [o.slug for o in await svc.operators_all()] == ["op-alice", "op-bob"]
