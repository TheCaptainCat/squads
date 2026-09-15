"""An empty role/skill body's hint must name an action that can actually be taken, not the
generic ``body`` verb (roles have none, and ``set_body`` refuses a role body unconditionally),
and must not diagnose something false of the item in front of it — a system skill's type can be
perfectly declared, with nothing having backfilled the tag yet, which is a different fact from
"the type is no longer declared", and is also a different fact from "the *view* this body would
render is not declared" — an empty body under a dropped view is a state ``sq sync`` provably
cannot fix, so the hint must not send an operator to run it.
"""

from pathlib import Path

import pytest

from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._sections import replace_section
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio


def _collapsed(text: str) -> str:
    """*text* with all whitespace runs collapsed to a single space — console output can wrap
    a multi-word phrase across a line boundary, so a raw substring check on it is unsound; this
    is the same fix the project's own line-wrap lesson prescribes, applied to assertion text."""
    return " ".join(text.split())


#: Drops `role_definition` from the declared view set. Every other bundled view stays selected,
#: including `milestone_rollup` — a type-owned view still attached via `items.milestone.views`,
#: which would otherwise be refused at load as a dangling attachment (a different failure mode
#: this module does not want to exercise).
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
    assert "sq sync" in r.output


async def test_an_empty_system_skill_body_under_a_live_type_points_at_sync_not_the_type(
    svc, invoke
) -> None:
    """The type ``squads`` documents is perfectly declared — nothing dropped it. Only the
    backfill has not run yet (an empty body simulates exactly that pre-convergence moment), so
    the hint must not claim the type is gone."""
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", "squads")
    assert skill is not None
    _empty_body(svc, skill)

    r = await invoke(["skill", "squads", "show", "--raw"])

    assert r.exit_code == 0, r.output
    assert "sq sync" in r.output
    assert "no longer" not in r.output


async def test_an_empty_per_type_skill_body_under_a_live_type_also_points_at_sync(
    svc, invoke
) -> None:
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", "sq-task")
    assert skill is not None
    _empty_body(svc, skill)

    r = await invoke(["skill", "sq-task", "show", "--raw"])

    assert r.exit_code == 0, r.output
    assert "sq sync" in r.output
    assert "no longer" not in r.output


# --------------------------------------------------------------------------- dropped view
# The companion state: the view itself, not the item type, is undeclared — `sq sync` provably
# cannot populate the body, so the hint must not name it, and must say why in a way that names
# the actual view rather than repeating the same generic text as the sync-pending case.


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
    """Precedence, driven: when a per-type skill's own item type is gone (not merely its
    view), the more specific "type is gone" message still fires — dropping `item_skill` too
    must not change which branch answers for `sq-guide` once `guide` itself is undeclared."""
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
# Once `view rm` exists it is the honest remedy for a body that already carries the dangling
# tag; the empty-body hint names it as general guidance without claiming the item in front of
# it currently carries one (its body is, after all, empty — there is nothing to remove yet).


async def test_the_dropped_view_hint_names_view_rm_as_the_tag_clearing_remedy(svc, invoke) -> None:
    _write_override(svc.paths.squad_dir, _DROP_ROLE_DEFINITION)
    spec = load_workflow_spec(squad_dir=svc.paths.squad_dir)
    from squads._services import _service as service

    declared = service.Service(svc.paths, spec=spec)
    role = await declared.activate_role("reviewer")
    _empty_body(declared, role)

    r = await invoke(["role", "reviewer", "show", "--raw"])

    assert r.exit_code == 0, r.output
    assert "view rm role_definition" in _collapsed(r.output)
