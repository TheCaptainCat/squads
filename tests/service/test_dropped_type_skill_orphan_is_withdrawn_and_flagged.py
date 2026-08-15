"""When a workflow override drops or renames a built-in type, its bundled ``sq-<type>``
skill must not survive as an orphan: nothing should point at it once the type it described
is gone, and ``sq check`` must not stay silent about a SKILL item still sitting Active for a
type the active spec no longer declares.

Both halves are driven end to end (a real squad, a real override, a real ``sq sync``/``sq
check``), including the reversible round trip: restoring the dropped type brings the
generated pointer straight back with no manual reconciliation step.
"""

from pathlib import Path

import pytest

from squads._services import _service as service
from squads._workflow import bundled_spec

pytestmark = pytest.mark.anyio


def _drop_type(squad_dir: Path, dropped: str) -> None:
    kept = sorted(set(bundled_spec().items) - {dropped})
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(f"[selected]\nitems = {kept!r}\n", encoding="utf-8")


async def test_dropping_a_type_withdraws_its_bundled_skills_pointer_on_sync(project):
    svc = service.Service(project)
    await svc.seed_bundled_skills()
    pointer = project.root / ".claude" / "skills" / "sq-guide"
    assert pointer.is_dir()  # sanity: seeded and materialised before the drop

    _drop_type(project.squad_dir, "guide")
    from squads._services._service import open_service

    dropped_svc = open_service(dir_override=str(project.squad_dir))
    notices = await dropped_svc.sync()
    assert any("sq-guide" in n and "guide" in n for n in notices)
    assert not pointer.exists()

    skills = await dropped_svc.list_items(item_type="skill")
    skill = next(s for s in skills if s.extra.get("slug") == "sq-guide")
    assert skill.status == "Active"  # the item's own record is untouched, only the file is


async def test_check_flags_a_live_skill_whose_type_the_active_spec_no_longer_declares(project):
    svc = service.Service(project)
    await svc.seed_bundled_skills()
    _drop_type(project.squad_dir, "guide")

    from squads._services._service import open_service

    dropped_svc = open_service(dir_override=str(project.squad_dir))
    await dropped_svc.sync()
    issues = await dropped_svc.check()
    matches = [i for i in issues if "sq-guide" in i.message]
    assert len(matches) == 1
    assert matches[0].level == "warn"
    assert "guide" in matches[0].message


async def test_restoring_the_dropped_type_re_materialises_the_skill_with_no_manual_step(project):
    svc = service.Service(project)
    await svc.seed_bundled_skills()
    _drop_type(project.squad_dir, "guide")

    from squads._services._service import open_service

    dropped_svc = open_service(dir_override=str(project.squad_dir))
    await dropped_svc.sync()
    pointer = project.root / ".claude" / "skills" / "sq-guide"
    assert not pointer.exists()

    (project.squad_dir / ".overrides" / "workflow.toml").unlink()
    restored_svc = open_service(dir_override=str(project.squad_dir))
    notices = await restored_svc.sync()
    assert not any("sq-guide" in n for n in notices)
    assert pointer.is_dir()
    issues = await restored_svc.check()
    assert not any("sq-guide" in i.message for i in issues)


async def test_an_author_created_skill_named_sq_something_is_never_swept(project):
    """The sweep must key off whether a skill was actually generated for a type, not the
    ``sq-`` prefix alone: on a clean squad with NO override at all, an author-created skill
    that happens to share the house naming convention (every bundled skill uses ``sq-``) must
    survive `sq check`/`sq sync` untouched — never withdrawn, never flagged."""
    svc = service.Service(project)
    await svc.seed_bundled_skills()
    await svc.add_skill("sq-onboarding", description="House onboarding runbook")
    await svc.sync()  # materialise the pointer sq skill add just created
    pointer = project.root / ".claude" / "skills" / "sq-onboarding"
    assert pointer.is_dir()

    issues = await svc.check()
    assert not any("sq-onboarding" in i.message for i in issues)

    notices = await svc.sync()
    assert not any("sq-onboarding" in n for n in notices)
    assert pointer.is_dir()  # still there — sync must not have withdrawn it


async def test_a_still_current_type_skill_is_untouched(project):
    """The negative case: dropping `guide` must not disturb any other bundled skill's
    projection or trip a false `sq check` finding on it."""
    svc = service.Service(project)
    await svc.seed_bundled_skills()
    _drop_type(project.squad_dir, "guide")

    from squads._services._service import open_service

    dropped_svc = open_service(dir_override=str(project.squad_dir))
    await dropped_svc.sync()
    assert (project.root / ".claude" / "skills" / "sq-task").is_dir()
    issues = await dropped_svc.check()
    assert not any("sq-task" in i.message for i in issues)
