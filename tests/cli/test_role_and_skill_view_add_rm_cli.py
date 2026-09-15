"""``sq role <addr> view add|rm <name>`` and ``sq skill <addr> view add|rm <name>`` — the
recovery verb exposed on the two roster addressing groups that never had one.

Mirrors ``tests/cli/test_view_tag_placement_cli.py``'s coverage of the generic
``sq <type> <n> view add|rm`` group (insert, idempotent re-insert, remove, no-op remove) but
through the role/skill groups' own slug addressing, and adds the one case those groups exist
for: clearing an already-tagged body left behind by ``_create_core``/``sq repair`` seeding a
tag before the view it names was dropped from the spec (see the two service-level fixes this
recovery verb is the companion of). ``sq check`` going from an error back to clean is the
end-to-end proof the recovery actually works, not just that the marker byte pattern changed.
"""

from pathlib import Path

import pytest

from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._sections import get_section

pytestmark = pytest.mark.anyio

_DROP_ROLE_DEFINITION = """\
[selected]
views = ["milestone_rollup", "squads_skill", "greeting_skill", "memory_skill", "item_skill"]
"""


def _write_override(squad_dir: Path, content: str) -> None:
    from squads import __version__

    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{content}", encoding="utf-8"
    )


def _body(svc, item) -> str:
    path = item_file(svc.paths, item)
    return (get_section(path.read_text(encoding="utf-8"), markers.BODY) or "").strip()


# --------------------------------------------------------------------------- sq role … view


async def test_role_view_rm_removes_the_tag(svc, invoke) -> None:
    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    assert _body(svc, role) == markers.open_marker(markers.view_tag("role_definition"))

    r = await invoke(["role", "manager", "view", "rm", "role_definition"])

    assert r.exit_code == 0, r.output
    assert "removed" in r.output
    assert _body(svc, role) == ""


async def test_role_view_rm_of_an_absent_tag_is_a_safe_no_op(svc, invoke) -> None:
    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    await invoke(["role", "manager", "view", "rm", "role_definition"])

    r = await invoke(["role", "manager", "view", "rm", "role_definition"])

    assert r.exit_code == 0, r.output
    assert "not present" in r.output
    assert _body(svc, role) == ""


async def test_role_view_add_places_the_tag_back(svc, invoke) -> None:
    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    await invoke(["role", "manager", "view", "rm", "role_definition"])

    r = await invoke(["role", "manager", "view", "add", "role_definition"])

    assert r.exit_code == 0, r.output
    assert "placed" in r.output
    assert _body(svc, role) == markers.open_marker(markers.view_tag("role_definition"))


async def test_role_view_add_twice_is_idempotent(svc, invoke) -> None:
    _ = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    await invoke(["role", "manager", "view", "rm", "role_definition"])
    first = await invoke(["role", "manager", "view", "add", "role_definition"])
    assert first.exit_code == 0, first.output

    second = await invoke(["role", "manager", "view", "add", "role_definition"])

    assert second.exit_code == 0, second.output
    assert "already present" in second.output


async def test_role_view_add_an_undeclared_name_is_refused(svc, invoke) -> None:
    _ = await svc.roster_item("role", "manager") or await svc.activate_role("manager")

    r = await invoke(["role", "manager", "view", "add", "no-such-view"])

    assert r.exit_code == 1
    assert "no declared view" in r.output


async def test_role_view_rm_clears_a_dangling_tag_left_by_a_dropped_view_and_sq_check_recovers(
    svc, invoke
) -> None:
    """The end-to-end recovery this verb exists for: a role activated before the view was
    dropped (or under an older build predating the creation-path gate) has a body that already
    carries the now-dangling tag. `sq check` reports it; `view rm` clears it without any
    automatic sweep touching the file, and `sq check` goes clean."""
    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    assert _body(svc, role) == markers.open_marker(markers.view_tag("role_definition"))

    _write_override(svc.paths.squad_dir, _DROP_ROLE_DEFINITION)

    before = await invoke(["check"])
    assert before.exit_code != 0
    assert "role_definition" in before.output

    r = await invoke(["role", "manager", "view", "rm", "role_definition"])
    assert r.exit_code == 0, r.output
    assert _body(svc, role) == ""

    after = await invoke(["check"])
    assert after.exit_code == 0, after.output


# --------------------------------------------------------------------------- sq skill … view


async def test_skill_view_rm_removes_the_tag(svc, invoke) -> None:
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", "squads")
    assert skill is not None
    assert _body(svc, skill) == markers.open_marker(markers.view_tag("squads_skill"))

    r = await invoke(["skill", "squads", "view", "rm", "squads_skill"])

    assert r.exit_code == 0, r.output
    assert "removed" in r.output
    assert _body(svc, skill) == ""


async def test_skill_view_add_places_the_tag_back(svc, invoke) -> None:
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", "squads")
    assert skill is not None
    await invoke(["skill", "squads", "view", "rm", "squads_skill"])

    r = await invoke(["skill", "squads", "view", "add", "squads_skill"])

    assert r.exit_code == 0, r.output
    assert "placed" in r.output
    assert _body(svc, skill) == markers.open_marker(markers.view_tag("squads_skill"))


async def test_skill_view_rm_clears_a_dangling_tag_and_sq_check_recovers(svc, invoke) -> None:
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", "squads")
    assert skill is not None
    assert _body(svc, skill) == markers.open_marker(markers.view_tag("squads_skill"))

    _write_override(
        svc.paths.squad_dir,
        '[selected]\nviews = ["milestone_rollup", "role_definition", "greeting_skill", '
        '"memory_skill", "item_skill"]\n',
    )

    before = await invoke(["check"])
    assert before.exit_code != 0
    assert "squads_skill" in before.output

    r = await invoke(["skill", "squads", "view", "rm", "squads_skill"])
    assert r.exit_code == 0, r.output

    after = await invoke(["check"])
    assert after.exit_code == 0, after.output


async def test_skill_view_add_an_undeclared_name_is_refused(svc, invoke) -> None:
    await svc.seed_bundled_skills()
    await svc.roster_item("skill", "squads")

    r = await invoke(["skill", "squads", "view", "add", "no-such-view"])

    assert r.exit_code == 1
    assert "no declared view" in r.output


# --------------------------------------------------------------------------- surfaced in help


async def test_role_group_help_lists_the_view_verb(invoke) -> None:
    r = await invoke(["role", "--help"])
    assert r.exit_code == 0, r.output
    assert "view" in r.output


async def test_skill_group_help_lists_the_view_verb(invoke) -> None:
    r = await invoke(["skill", "--help"])
    assert r.exit_code == 0, r.output
    assert "view" in r.output
