"""Every playbook consumer reads the per-request MERGED playbook, not the bundled singleton:
the generated ``sq-<type>`` skill body, the skills a role's pointer preloads, and the
config-integrity always-on floor all reflect a project's ``.overrides/playbook.toml`` once the
squad is reopened through ``open_service`` — and, with no override present, every one of those
artefacts is unchanged from today (proven at the whole-repo scale separately by a byte-for-byte
regeneration diff; this file proves the *mechanism* reaches each consumer end to end).
"""

from pathlib import Path

import pytest

from squads import _interactions as interactions
from squads._services import _config_integrity as config_integrity
from squads._services import _service as service

pytestmark = pytest.mark.anyio


def _write_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "playbook.toml").write_text(content, encoding="utf-8")


_APPEND_ARCHITECT_TO_TASK = """
[types.task]
roles = [
    "$(*self)",
    { slug = "architect", enter = ["confirm the design"], do = ["review the architecture"] },
]
"""


async def _skill_body(svc, item_type: str) -> str:
    """The type's generated skill definition, as *svc* resolves it on read."""
    return await svc.skill_definition_text(interactions.item_skill_name(item_type))


async def test_generated_sq_task_skill_body_reflects_the_playbook_override(project) -> None:
    _write_override(project.squad_dir, _APPEND_ARCHITECT_TO_TASK)
    svc = service.open_service()
    await svc.activate_role("architect")
    await svc.refresh_managed()

    body = await _skill_body(svc, "task")
    assert "confirm the design" in body
    assert "review the architecture" in body
    assert "Robert Architect" in body


async def test_with_no_override_the_generated_skill_body_is_unchanged(project, svc) -> None:
    """The control: no ``.overrides/playbook.toml`` at all — the same squad, same role
    activation, produces the SAME body as the bundled-only path (no "architect" section)."""
    await svc.activate_role("architect")
    await svc.refresh_managed()
    body = await _skill_body(svc, "task")
    assert "confirm the design" not in body
    assert "Robert Architect" not in body  # architect has no bundled task guide


async def test_a_roles_preloaded_skill_list_reflects_the_playbook_override(project) -> None:
    _write_override(project.squad_dir, _APPEND_ARCHITECT_TO_TASK)
    svc = service.open_service()
    assert "sq-task" not in interactions.skills_for_role("architect", svc.spec)  # bundled-blind
    assert "sq-task" in interactions.skills_for_role("architect", svc.spec, svc.playbook)


async def test_config_integrity_type_implied_finding_reflects_the_playbook_override(
    project, svc
) -> None:
    """``check_preloaded_skill``'s ``type_implied`` kind names the interacting types straight
    off ``item_types_for_role`` — the direct proof this clause reads the merged playbook: a
    live ``architect`` role only implies ``sq-task`` once the override is threaded through.

    The override is written to disk only AFTER the skill is archived (against the un-overridden
    ``svc``, where architect implies nothing and the retirement gate has nothing to refuse) —
    this test calls the pure ``check_preloaded_skill`` predicate directly afterwards, on the
    same snapshot, with and without the playbook argument, rather than driving the live gate
    (which — correctly, per this very feature — would now refuse the transition outright)."""
    await svc.activate_role("architect")
    skill = await svc.add_skill("sq-task")
    await svc.set_status(skill.id, "Archived")  # non-live, so it's a preloaded_skill candidate

    _write_override(project.squad_dir, _APPEND_ARCHITECT_TO_TASK)
    from squads._interactions._loader import load_playbook
    from squads._roles._catalog import get_catalog

    merged_playbook = load_playbook(get_catalog(), spec=svc.spec, squad_dir=project.squad_dir)
    db = await svc.store.load()
    with_playbook = config_integrity.check_preloaded_skill(
        db, svc.spec, ["claude_code"], merged_playbook
    )
    without_playbook = config_integrity.check_preloaded_skill(db, svc.spec, ["claude_code"], None)

    def _names_task_as_type_implied(
        findings: list[config_integrity.ConfigIntegrityFinding],
    ) -> bool:
        return any(
            f.kind == config_integrity.TYPE_IMPLIED and "task" in f.message for f in findings
        )

    assert _names_task_as_type_implied(with_playbook) is True
    assert _names_task_as_type_implied(without_playbook) is False
