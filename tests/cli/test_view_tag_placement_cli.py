"""``sq <type> <n> view add|rm <name>`` — the CLI surface over the marker-safe view-tag
placement verb. A distinct verb group from ``body``, exercised end to end through the CLI:
insert, idempotent re-insert, remove, no-op remove, and the dangling-name refusal.

Placement is asserted against the item's **stored file** rather than ``show --raw``'s
console output: read-time expansion (see
``tests/cli/test_view_tag_expansion_at_read_time_cli.py``) renders a tag in ``show --raw``
to its view's output, so the file is the one place a literal, not-yet-expanded tag is
assertable against.
"""

from pathlib import Path

import pytest

from squads import __version__
from squads._rendering._engine import invalidate_squad_dir

pytestmark = pytest.mark.anyio

_BUNDLED_VIEW = "milestone_rollup"


def _task_file(project) -> Path:
    return next(iter((project.squad_dir / "tasks").glob("TASK-*.md")))


def _declare_resolvable_subentity_view(squad_dir: Path, name: str, kind: str) -> None:
    """A declared, templated ``subentity``-source view over sub-entity *kind* — resolvable, so
    placing it exercises the source-applicability question rather than the "undeclared" one."""
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


async def test_view_rm_removes_the_tag(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    await invoke(["task", "2", "view", "add", _BUNDLED_VIEW])

    r = await invoke(["task", "2", "view", "rm", _BUNDLED_VIEW])

    assert r.exit_code == 0, r.output
    assert "removed" in r.output
    text = _task_file(project).read_text(encoding="utf-8")
    assert f"sq:view:{_BUNDLED_VIEW}" not in text


async def test_view_rm_of_an_absent_tag_is_a_safe_no_op_not_an_error(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])

    r = await invoke(["task", "2", "view", "rm", _BUNDLED_VIEW])

    assert r.exit_code == 0, r.output
    assert "not present" in r.output


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
    """Driven end to end through the CLI: a declared, templated ``subentity``-source view over
    ``story`` placed on an ``epic`` (which hosts no sub-entity kind at all) is refused at the
    door, before any write."""
    _declare_resolvable_subentity_view(project.squad_dir, "story_board", "story")
    await invoke(["create", "epic", "An epic", "--author", "manager"])
    epic_file = next(iter((project.squad_dir / "epics").glob("EPIC-*.md")))
    text_before = epic_file.read_text(encoding="utf-8")

    r = await invoke(["epic", "2", "view", "add", "story_board"])

    assert r.exit_code == 1
    assert "hosts" in r.output
    assert epic_file.read_text(encoding="utf-8") == text_before  # refused before any write


async def test_view_is_not_a_flag_on_body(project, invoke) -> None:
    """Placement lives in its own verb group, never as a `body` option."""
    r = await invoke(["task", "--help"])
    assert r.exit_code == 0, r.output
    assert "view" in r.output

    body_help = await invoke(["task", "1", "body", "--help"])
    assert "--view" not in body_help.output
