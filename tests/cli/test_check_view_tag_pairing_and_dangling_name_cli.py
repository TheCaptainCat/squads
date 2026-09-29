"""``sq check`` over ``sq:view:<name>`` tags, end to end through the CLI: a well-placed,
resolvable tag reports clean (exit 0), while a tag naming an undeclared view, a declared one
with no resolvable template, or a declared and templated one whose source cannot apply to the
host's type — exits 3 and names both the file and the offending view.
"""

from pathlib import Path

import pytest

from squads import __version__

pytestmark = pytest.mark.anyio

_BUNDLED_VIEW = "milestone_rollup"


def _task_file(project) -> Path:
    return next(iter((project.squad_dir / "tasks").glob("TASK-*.md")))


def _epic_file(project) -> Path:
    return next(iter((project.squad_dir / "epics").glob("EPIC-*.md")))


async def test_check_is_clean_for_a_well_placed_resolvable_view_tag(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    placed = await invoke(["task", "2", "view", "add", _BUNDLED_VIEW])
    assert placed.exit_code == 0, placed.output

    result = await invoke(["check"])
    assert result.exit_code == 0, result.output


async def test_check_exits_3_and_names_the_view_for_an_undeclared_name(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    path = _task_file(project)
    text = path.read_text(encoding="utf-8")
    seeded = text.replace(
        "<!-- sq:body -->", "<!-- sq:body -->\n<!-- sq:view:no-such-view -->\n", 1
    )
    path.write_text(seeded, encoding="utf-8")

    result = await invoke(["check"])
    assert result.exit_code == 3, result.output
    assert "no-such-view" in result.output
    assert path.name in result.output


async def test_check_json_reports_the_dangling_view_finding_as_error_level(project, invoke) -> None:
    import json

    await invoke(["create", "task", "T", "--author", "manager"])
    path = _task_file(project)
    text = path.read_text(encoding="utf-8")
    seeded = text.replace(
        "<!-- sq:body -->", "<!-- sq:body -->\n<!-- sq:view:no-such-view -->\n", 1
    )
    path.write_text(seeded, encoding="utf-8")

    result = await invoke(["check", "--json"])
    assert result.exit_code == 3, result.output
    issues = json.loads(result.output)
    matches = [i for i in issues if "no-such-view" in i["message"]]
    assert matches, issues
    assert all(i["level"] == "error" for i in matches)


async def test_check_exits_3_and_names_the_view_for_a_source_incompatible_host(
    project, invoke
) -> None:
    """Driven end to end through the CLI: a body seeded directly with a ``story_board`` view tag
    (a ``subentity``-source view) on an epic, which hosts no ``story``, makes ``sq check`` exit 3
    and name both the file and the reason."""
    override_dir = project.squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    templates_dir = override_dir / "templates" / "views"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "story_board.md.j2").write_text("story board\n", encoding="utf-8")
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n"
        '[views.story_board]\nsource = { kind = "subentity", name = "story" }\n',
        encoding="utf-8",
    )
    await invoke(["create", "epic", "An epic", "--author", "manager"])
    path = _epic_file(project)
    text = path.read_text(encoding="utf-8")
    seeded = text.replace("<!-- sq:body -->", "<!-- sq:body -->\n<!-- sq:view:story_board -->\n", 1)
    path.write_text(seeded, encoding="utf-8")

    result = await invoke(["check"])

    assert result.exit_code == 3, result.output
    assert "story_board" in result.output
    assert "hosts" in result.output
    assert path.name in result.output


async def test_check_does_not_report_a_duplicate_tag_as_unclosed(project, invoke) -> None:
    """The control on the CLI surface, mirroring the service-level exemption test: a doubled
    view tag is reported as a duplicate, never as unclosed."""
    await invoke(["create", "task", "T", "--author", "manager"])
    path = _task_file(project)
    text = path.read_text(encoding="utf-8")
    seeded = text.replace(
        "<!-- sq:body -->",
        f"<!-- sq:body -->\n<!-- sq:view:{_BUNDLED_VIEW} -->\n<!-- sq:view:{_BUNDLED_VIEW} -->\n",
        1,
    )
    path.write_text(seeded, encoding="utf-8")

    result = await invoke(["check"])
    assert result.exit_code == 3, result.output
    assert "duplicate marker" in result.output
    assert "unclosed marker" not in result.output
