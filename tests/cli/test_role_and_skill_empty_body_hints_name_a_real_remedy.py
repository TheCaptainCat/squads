"""An empty role/skill body's hint names an action that can actually be taken, and never
misdiagnoses which of type-dropped, view-dropped, or merely-unbackfilled state applies."""

from pathlib import Path

import pytest

from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._sections import replace_section
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio


def _collapsed(text: str) -> str:
    """Collapse whitespace so a wrapped multi-word phrase still matches a substring check."""
    return " ".join(text.split())


#: Drops `role_definition` from the declared view set.
_DROP_ROLE_DEFINITION = """\
[selected]
views = ["milestone_rollup", "squads_skill", "greeting_skill", "memory_skill", "item_skill"]
"""

#: Drops `squads_skill` (one of the three permanently-system slugs) instead.
_DROP_SQUADS_SKILL = """\
[selected]
views = ["milestone_rollup", "role_definition", "greeting_skill", "memory_skill", "item_skill"]
"""

#: Drops `item_skill` — the one view every per-item-type `sq-<type>` skill shares.
_DROP_ITEM_SKILL = """\
[selected]
views = ["milestone_rollup", "role_definition", "squads_skill", "greeting_skill", "memory_skill"]
"""


def _empty_body(svc, item) -> None:
    path = item_file(svc.paths, item)
    text = replace_section(path.read_text(encoding="utf-8"), markers.BODY, "")
    path.write_text(text, encoding="utf-8")


def _write_override(squad_dir: Path, content: str) -> None:
    from squads import __version__

    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{content}", encoding="utf-8"
    )


async def test_an_empty_role_body_does_not_name_the_nonexistent_body_verb(svc, invoke) -> None:
    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    _empty_body(svc, role)

    r = await invoke(["role", "manager", "show", "--raw"])

    assert r.exit_code == 0, r.output
    assert "set it with" not in r.output
    assert "roles.toml" in r.output
    assert "sq sync" not in r.output


async def test_an_empty_system_skill_body_under_a_live_type_points_at_sync_not_the_type(
    svc, invoke
) -> None:
    """A declared type with just no backfill yet must not be reported as gone."""
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", "squads")
    assert skill is not None
    _empty_body(svc, skill)

    r = await invoke(["skill", "squads", "show", "--raw"])

    assert r.exit_code == 0, r.output
    assert "`.overrides/playbook.toml`" in r.output
    assert "sq sync" not in r.output
    assert "no longer" not in r.output


async def test_an_empty_per_type_skill_body_under_a_live_type_also_points_at_the_overrides(
    svc, invoke
) -> None:
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", "sq-task")
    assert skill is not None
    _empty_body(svc, skill)

    r = await invoke(["skill", "sq-task", "show", "--raw"])

    assert r.exit_code == 0, r.output
    assert "the `[types.task]` lane in `.overrides/playbook.toml`" in _collapsed(r.output)
    assert "sq sync" not in r.output
    assert "no longer" not in r.output


# --------------------------------------------------------------------------- dropped view


async def test_an_empty_role_body_under_a_dropped_view_does_not_point_at_sync(svc, invoke) -> None:
    _write_override(svc.paths.squad_dir, _DROP_ROLE_DEFINITION)
    spec = load_workflow_spec(squad_dir=svc.paths.squad_dir)
    from squads._services import _service as service

    declared = service.Service(svc.paths, spec=spec)
    role = await declared.activate_role("reviewer")
    _empty_body(declared, role)

    r = await invoke(["role", "reviewer", "show", "--raw"])

    assert r.exit_code == 0, r.output
    assert "run `sq sync` to populate it" not in r.output
    assert "role_definition" in r.output
    assert "not declared" in r.output


async def test_an_empty_system_skill_body_under_a_dropped_view_does_not_point_at_sync(
    svc, invoke
) -> None:
    await svc.seed_bundled_skills()
    _write_override(svc.paths.squad_dir, _DROP_SQUADS_SKILL)
    skill = await svc.roster_item("skill", "squads")
    assert skill is not None
    _empty_body(svc, skill)

    r = await invoke(["skill", "squads", "show", "--raw"])

    assert r.exit_code == 0, r.output
    assert "run `sq sync` to populate it" not in r.output
    assert "squads_skill" in r.output
    assert "not declared" in r.output


async def test_an_empty_per_type_skill_body_under_a_dropped_view_does_not_point_at_sync(
    svc, invoke
) -> None:
    await svc.seed_bundled_skills()
    _write_override(svc.paths.squad_dir, _DROP_ITEM_SKILL)
    skill = await svc.roster_item("skill", "sq-task")
    assert skill is not None
    _empty_body(svc, skill)

    r = await invoke(["skill", "sq-task", "show", "--raw"])

    assert r.exit_code == 0, r.output
    assert "run `sq sync` to populate it" not in r.output
    assert "item_skill" in r.output
    assert "not declared" in r.output


async def test_a_dropped_item_type_hint_still_wins_over_a_dropped_view_hint(svc, invoke) -> None:
    """A skill whose item type is gone gets the type-gone message even with its view dropped."""
    await svc.seed_bundled_skills()
    kept_items = ", ".join(
        f'"{t}"' for t in ("epic", "feature", "task", "bug", "decision", "contract", "milestone")
    )
    _write_override(
        svc.paths.squad_dir,
        f'[selected]\nitems = [{kept_items}, "role", "skill", "operator"]\n',
    )
    skill = await svc.roster_item("skill", "sq-guide")
    assert skill is not None
    _empty_body(svc, skill)

    r = await invoke(["skill", "sq-guide", "show", "--raw"])

    assert r.exit_code == 0, r.output
    assert "no longer declared" in _collapsed(r.output)
    assert "run `sq sync` to populate it" not in r.output


# --------------------------------------------------------------------------- recovery mention


async def test_the_dropped_view_hint_names_view_disable_as_the_tag_clearing_remedy(
    svc, invoke
) -> None:
    _write_override(svc.paths.squad_dir, _DROP_ROLE_DEFINITION)
    spec = load_workflow_spec(squad_dir=svc.paths.squad_dir)
    from squads._services import _service as service

    declared = service.Service(svc.paths, spec=spec)
    role = await declared.activate_role("reviewer")
    _empty_body(declared, role)

    r = await invoke(["role", "reviewer", "show", "--raw"])

    assert r.exit_code == 0, r.output
    assert "view disable role_definition" in _collapsed(r.output)
    assert "view rm" not in r.output
