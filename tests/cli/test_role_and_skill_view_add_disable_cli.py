"""``sq role <addr> view add|disable <name>`` and ``sq skill <addr> view add|disable <name>``,
including the dangling-tag recovery through to ``sq check`` going clean. ``view rm`` is retired."""

from pathlib import Path

import pytest

from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._sections import get_section, replace_section, strip_marker_lines

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


def _strip_tag_on_disk(svc, item, name: str) -> None:
    """Remove *name*'s tag straight on disk, bypassing the service entirely — used to set up a
    tag-absent role/skill body for a test that needs one, without going through any verb."""
    path = item_file(svc.paths, item)
    text = path.read_text(encoding="utf-8")
    region = get_section(text, markers.BODY) or ""
    stripped_region, removed = strip_marker_lines(
        region, lambda raw: raw != f"sq:{markers.view_tag(name)}"
    )
    assert removed, "fixture setup: the tag was not present to strip"
    new_text = replace_section(text, markers.BODY, stripped_region)
    path.write_text(new_text, encoding="utf-8")


# --------------------------------------------------------------------------- sq role … view


async def test_role_view_disable_is_ungated_on_a_declared_host(svc, invoke) -> None:
    """Disabling never writes prose, so it is admitted even on a declared view."""
    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    assert _body(svc, role) == markers.open_marker(markers.view_tag("role_definition"))

    r = await invoke(["role", "manager", "view", "disable", "role_definition"])

    assert r.exit_code == 0, r.output
    assert "disabled" in r.output
    assert _body(svc, role) == markers.open_marker(
        markers.view_tag("role_definition", disabled=True)
    )


async def test_role_view_disable_places_it_disabled_even_when_absent(svc, invoke) -> None:
    """Disabling an absent tag places a fresh disabled one and says "placed", not "disabled"."""
    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    _strip_tag_on_disk(svc, role, "role_definition")

    r = await invoke(["role", "manager", "view", "disable", "role_definition"])

    assert r.exit_code == 0, r.output
    assert "had no existing tag — placed disabled" in r.output
    assert _body(svc, role) == markers.open_marker(
        markers.view_tag("role_definition", disabled=True)
    )


async def test_role_view_add_places_the_tag_back(svc, invoke) -> None:
    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    _strip_tag_on_disk(svc, role, "role_definition")

    r = await invoke(["role", "manager", "view", "add", "role_definition"])

    assert r.exit_code == 0, r.output
    assert "placed" in r.output
    assert _body(svc, role) == markers.open_marker(markers.view_tag("role_definition"))


async def test_role_view_add_re_enables_a_disabled_tag(svc, invoke) -> None:
    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    await invoke(["role", "manager", "view", "disable", "role_definition"])

    r = await invoke(["role", "manager", "view", "add", "role_definition"])

    assert r.exit_code == 0, r.output
    assert _body(svc, role) == markers.open_marker(markers.view_tag("role_definition"))


async def test_role_view_add_twice_is_idempotent(svc, invoke) -> None:
    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    _strip_tag_on_disk(svc, role, "role_definition")
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


async def test_role_view_rm_is_not_a_command(svc, invoke) -> None:
    _ = await svc.roster_item("role", "manager") or await svc.activate_role("manager")

    r = await invoke(["role", "manager", "view", "rm", "role_definition"])

    assert r.exit_code != 0


async def test_role_view_disable_clears_a_dangling_tag_left_by_a_dropped_view_and_sq_check_recovers(
    svc, invoke
) -> None:
    """`view disable` clears a dangling tag left by a dropped view, and `sq check` goes clean."""
    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    assert _body(svc, role) == markers.open_marker(markers.view_tag("role_definition"))

    _write_override(svc.paths.squad_dir, _DROP_ROLE_DEFINITION)

    before = await invoke(["check"])
    assert before.exit_code != 0
    assert "role_definition" in before.output

    r = await invoke(["role", "manager", "view", "disable", "role_definition"])
    assert r.exit_code == 0, r.output
    assert _body(svc, role) == markers.open_marker(
        markers.view_tag("role_definition", disabled=True)
    )

    after = await invoke(["check"])
    assert after.exit_code == 0, after.output


# --------------------------------------------------------------------------- sq skill … view


async def test_skill_view_disable_is_ungated_on_a_declared_host(svc, invoke) -> None:
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", "squads")
    assert skill is not None
    assert _body(svc, skill) == markers.open_marker(markers.view_tag("squads_skill"))

    r = await invoke(["skill", "squads", "view", "disable", "squads_skill"])

    assert r.exit_code == 0, r.output
    assert _body(svc, skill) == markers.open_marker(markers.view_tag("squads_skill", disabled=True))


async def test_skill_view_disable_places_it_disabled_even_when_absent(svc, invoke) -> None:
    """Disabling an absent tag on a skill says "placed", not "disabled" (the role-case sibling)."""
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", "squads")
    assert skill is not None
    _strip_tag_on_disk(svc, skill, "squads_skill")

    r = await invoke(["skill", "squads", "view", "disable", "squads_skill"])

    assert r.exit_code == 0, r.output
    assert "had no existing tag — placed disabled" in r.output
    assert _body(svc, skill) == markers.open_marker(markers.view_tag("squads_skill", disabled=True))


async def test_skill_view_add_places_the_tag_back(svc, invoke) -> None:
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", "squads")
    assert skill is not None
    _strip_tag_on_disk(svc, skill, "squads_skill")

    r = await invoke(["skill", "squads", "view", "add", "squads_skill"])

    assert r.exit_code == 0, r.output
    assert "placed" in r.output
    assert _body(svc, skill) == markers.open_marker(markers.view_tag("squads_skill"))


async def test_skill_view_disable_clears_a_dangling_tag_and_sq_check_recovers(svc, invoke) -> None:
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

    r = await invoke(["skill", "squads", "view", "disable", "squads_skill"])
    assert r.exit_code == 0, r.output

    after = await invoke(["check"])
    assert after.exit_code == 0, after.output


async def test_skill_view_add_an_undeclared_name_is_refused(svc, invoke) -> None:
    await svc.seed_bundled_skills()
    await svc.roster_item("skill", "squads")

    r = await invoke(["skill", "squads", "view", "add", "no-such-view"])

    assert r.exit_code == 1
    assert "no declared view" in r.output


async def test_skill_view_rm_is_not_a_command(svc, invoke) -> None:
    await svc.seed_bundled_skills()
    await svc.roster_item("skill", "squads")

    r = await invoke(["skill", "squads", "view", "rm", "squads_skill"])

    assert r.exit_code != 0


# --------------------------------------------------------------------------- surfaced in help


async def test_role_group_help_lists_the_view_verb(invoke) -> None:
    r = await invoke(["role", "--help"])
    assert r.exit_code == 0, r.output
    assert "view" in r.output


async def test_skill_group_help_lists_the_view_verb(invoke) -> None:
    r = await invoke(["skill", "--help"])
    assert r.exit_code == 0, r.output
    assert "view" in r.output
