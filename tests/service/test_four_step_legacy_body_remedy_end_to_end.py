"""A roster host whose body holds legacy prose beside a missing seeded-view tag converges to a
single live rendering through four steps: drop the view, clear the legacy text, restore the
view, `view add` — driven end to end per host kind through the real service surface."""

from pathlib import Path

import pytest

from squads import __version__
from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._sections import get_section, replace_section
from squads._services._service import Service
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio

_LEGACY_PROSE = "# Legacy definition\n\nStale pre-0.14 prose, no tag at all."


def _write_override(squad_dir: Path, views_kept: list[str]) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    kept = ", ".join(f'"{v}"' for v in views_kept)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n[selected]\nviews = [{kept}]\n",
        encoding="utf-8",
    )


def _clear_override(squad_dir: Path) -> None:
    path = squad_dir / ".overrides" / "workflow.toml"
    if path.exists():
        path.unlink()


def _reopen(project) -> Service:
    return Service(project, spec=load_workflow_spec(squad_dir=project.squad_dir))


def _region(text: str) -> str:
    return (get_section(text, markers.BODY) or "").strip()


def _issues_for(issues, filename: str) -> list[str]:
    return [i.message for i in issues if i.item == filename]


async def test_the_four_steps_converge_a_roles_stranded_prose_to_a_single_rendering(
    project, svc
) -> None:
    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    path = item_file(svc.paths, role)
    path.write_text(
        replace_section(path.read_text(encoding="utf-8"), markers.BODY, _LEGACY_PROSE),
        encoding="utf-8",
    )
    filename = path.name

    # Step 1: drop the view, lifting the roster write refusal.
    _write_override(
        project.squad_dir, ["squads_skill", "greeting_skill", "memory_skill", "item_skill"]
    )
    dropped = _reopen(project)
    assert not _issues_for(await dropped.check(), filename)

    # Step 2: clear the legacy text via a single-event bulk import (roles have no `body` verb).
    result = await dropped.import_events(
        f'{{"op": "body", "target": "{role.id}", "body": "", "force": true, "as": "manager"}}'
    )
    assert result.plan.ok, result.plan.issues
    assert _region(path.read_text(encoding="utf-8")) == ""

    # Step 3: restore the view — the tag is missing again, correctly reported.
    _clear_override(project.squad_dir)
    restored = _reopen(project)
    assert any(
        "missing seeded view tag" in m for m in _issues_for(await restored.check(), filename)
    )

    # Step 4: view add — a single live rendering, the legacy prose gone for good.
    changed = await restored.add_view(role.id, "role_definition")
    assert changed
    final_text = path.read_text(encoding="utf-8")
    assert _region(final_text) == markers.open_marker(markers.view_tag("role_definition"))
    assert "Stale pre-0.14 prose" not in final_text
    assert not _issues_for(await restored.check(), filename)


async def test_the_four_steps_converge_a_system_skills_stranded_prose(project, svc) -> None:
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", "greeting")
    assert skill is not None
    path = item_file(svc.paths, skill)
    path.write_text(
        replace_section(path.read_text(encoding="utf-8"), markers.BODY, _LEGACY_PROSE),
        encoding="utf-8",
    )
    filename = path.name

    # Step 1: drop the view.
    _write_override(
        project.squad_dir, ["role_definition", "squads_skill", "memory_skill", "item_skill"]
    )
    dropped = _reopen(project)
    assert not _issues_for(await dropped.check(), filename)

    # Step 2: clear the legacy text — a skill has its own `body` verb.
    await dropped.set_body(skill.id, "", force=True)
    assert _region(path.read_text(encoding="utf-8")) == ""

    # Step 3: restore the view.
    _clear_override(project.squad_dir)
    restored = _reopen(project)
    assert any(
        "missing seeded view tag" in m for m in _issues_for(await restored.check(), filename)
    )

    # Step 4: view add.
    changed = await restored.add_view(skill.id, "greeting_skill")
    assert changed
    final_text = path.read_text(encoding="utf-8")
    assert _region(final_text) == markers.open_marker(markers.view_tag("greeting_skill"))
    assert "Stale pre-0.14 prose" not in final_text
    assert not _issues_for(await restored.check(), filename)


async def test_the_four_steps_converge_a_per_item_type_skills_stranded_prose(project, svc) -> None:
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", "sq-task")
    assert skill is not None
    path = item_file(svc.paths, skill)
    path.write_text(
        replace_section(path.read_text(encoding="utf-8"), markers.BODY, _LEGACY_PROSE),
        encoding="utf-8",
    )
    filename = path.name

    # Step 1: drop the view (`item_skill` is shared by every per-item-type skill).
    _write_override(
        project.squad_dir, ["role_definition", "squads_skill", "greeting_skill", "memory_skill"]
    )
    dropped = _reopen(project)
    assert not _issues_for(await dropped.check(), filename)

    # Step 2: clear the legacy text.
    await dropped.set_body(skill.id, "", force=True)
    assert _region(path.read_text(encoding="utf-8")) == ""

    # Step 3: restore the view.
    _clear_override(project.squad_dir)
    restored = _reopen(project)
    assert any(
        "missing seeded view tag" in m for m in _issues_for(await restored.check(), filename)
    )

    # Step 4: view add.
    changed = await restored.add_view(skill.id, "item_skill")
    assert changed
    final_text = path.read_text(encoding="utf-8")
    assert _region(final_text) == markers.open_marker(markers.view_tag("item_skill"))
    assert "Stale pre-0.14 prose" not in final_text
    assert not _issues_for(await restored.check(), filename)
