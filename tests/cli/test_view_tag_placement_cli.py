"""``sq <type> <n> view add|disable <name>`` through the CLI: place, idempotent re-place,
disable, no-op disable, and the dangling-name refusal — asserted against the stored file."""

from pathlib import Path

import pytest

from squads import __version__
from squads._rendering._engine import invalidate_squad_dir

pytestmark = pytest.mark.anyio

_BUNDLED_VIEW = "milestone_rollup"


def _task_file(project) -> Path:
    return next(iter((project.squad_dir / "tasks").glob("TASK-*.md")))


def _declare_resolvable_subentity_view(squad_dir: Path, name: str, kind: str) -> None:
    """Declare a resolvable, templated ``subentity``-source view over sub-entity *kind*."""
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    templates_dir = override_dir / "templates" / "views"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / f"{name}.md.j2").write_text(f"{name}\n", encoding="utf-8")
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n"
        f'[views.{name}]\nsource = {{ kind = "subentity", name = "{kind}" }}\n',
        encoding="utf-8",
    )
    invalidate_squad_dir(squad_dir)


async def test_view_add_places_the_tag_in_the_stored_file(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])

    r = await invoke(["task", "2", "view", "add", _BUNDLED_VIEW])
    assert r.exit_code == 0, r.output
    assert "placed" in r.output

    text = _task_file(project).read_text(encoding="utf-8")
    assert f"<!-- sq:view:{_BUNDLED_VIEW} -->" in text


async def test_view_add_twice_is_idempotent_and_says_so(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    first = await invoke(["task", "2", "view", "add", _BUNDLED_VIEW])
    assert first.exit_code == 0, first.output

    second = await invoke(["task", "2", "view", "add", _BUNDLED_VIEW])

    assert second.exit_code == 0, second.output
    assert "already present" in second.output
    text = _task_file(project).read_text(encoding="utf-8")
    assert text.count(f"<!-- sq:view:{_BUNDLED_VIEW} -->") == 1


async def test_view_disable_turns_the_tag_disabled_not_removed(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    await invoke(["task", "2", "view", "add", _BUNDLED_VIEW])

    r = await invoke(["task", "2", "view", "disable", _BUNDLED_VIEW])

    assert r.exit_code == 0, r.output
    assert "disabled" in r.output
    text = _task_file(project).read_text(encoding="utf-8")
    assert f"<!-- sq:view:{_BUNDLED_VIEW}:disabled -->" in text
    assert f"<!-- sq:view:{_BUNDLED_VIEW} -->" not in text


async def test_view_disable_of_an_absent_tag_places_it_disabled(project, invoke) -> None:
    """Disabling an absent tag places a fresh disabled one and says "placed", not "disabled"."""
    await invoke(["create", "task", "T", "--author", "manager"])

    r = await invoke(["task", "2", "view", "disable", _BUNDLED_VIEW])

    assert r.exit_code == 0, r.output
    assert "had no existing tag — placed disabled" in r.output
    text = _task_file(project).read_text(encoding="utf-8")
    assert f"<!-- sq:view:{_BUNDLED_VIEW}:disabled -->" in text


async def test_view_disable_twice_is_a_safe_no_op(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    await invoke(["task", "2", "view", "disable", _BUNDLED_VIEW])

    r = await invoke(["task", "2", "view", "disable", _BUNDLED_VIEW])

    assert r.exit_code == 0, r.output
    assert "already disabled" in r.output


async def test_view_rm_is_not_a_command(project, invoke) -> None:
    """Retired outright, with no alias — a tag is disabled, never deleted."""
    await invoke(["create", "task", "T", "--author", "manager"])

    r = await invoke(["task", "2", "view", "rm", _BUNDLED_VIEW])

    assert r.exit_code != 0


async def test_view_add_an_undeclared_name_exits_nonzero_with_a_clear_message(
    project, invoke
) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])

    r = await invoke(["task", "2", "view", "add", "no-such-view"])

    assert r.exit_code == 1
    assert "no declared view" in r.output


async def test_view_add_a_source_incompatible_host_exits_nonzero_with_a_clear_message(
    project, invoke
) -> None:
    """A subentity-source view placed on a host with no matching sub-entity kind is refused
    before any write."""
    _declare_resolvable_subentity_view(project.squad_dir, "story_board", "story")
    await invoke(["create", "epic", "An epic", "--author", "manager"])
    epic_file = next(iter((project.squad_dir / "epics").glob("EPIC-*.md")))
    text_before = epic_file.read_text(encoding="utf-8")

    r = await invoke(["epic", "2", "view", "add", "story_board"])

    assert r.exit_code == 1
    assert "hosts" in r.output
    assert epic_file.read_text(encoding="utf-8") == text_before


async def test_view_is_not_a_flag_on_body(project, invoke) -> None:
    """Placement lives in its own verb group, never as a `body` option."""
    r = await invoke(["task", "--help"])
    assert r.exit_code == 0, r.output
    assert "view" in r.output

    body_help = await invoke(["task", "1", "body", "--help"])
    assert "--view" not in body_help.output
