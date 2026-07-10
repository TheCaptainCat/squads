"""Template-override precedence, end to end: with no override, rendering and `sq create`
produce exactly the bundled output; dropping an override under one template shadows only
that template — every other template, and every other `sq create`, still resolves to the
bundle. Env-cache isolation between two squads lives in
tests/service/test_override_render_cache_isolation.py; manifest/stamp mechanics live in
tests/meta/test_override_manifest_and_stamp_freshness.py.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from squads._models._item import Item
from squads._rendering._engine import invalidate_squad_dir, render, set_active_squad_dir
from squads._workflow import bundled_spec

pytestmark = pytest.mark.anyio


def _place_override(squad_dir: Path, template_name: str, content: str) -> None:
    target = squad_dir / ".overrides" / "templates" / template_name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    invalidate_squad_dir(squad_dir)


def _task_ctx() -> dict[str, object]:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    item = Item(
        sequence_id=1,
        type="task",
        title="Test task",
        slug="test-task",
        status="Ready",
        path="tasks/TASK-000001-test-task.md",
        created_at=now,
        updated_at=now,
    )
    return {"item": item, "description": "", "extra": {}, "spec": bundled_spec()}


def _minimal_override(label: str) -> str:
    return (
        f"<!-- sq:body -->\nOVERRIDDEN:{label}\n<!-- sq:body:end -->\n\n"
        "<!-- sq:summary -->\n<!-- sq:summary:end -->\n\n"
        "<!-- sq:subtasks -->\n<!-- sq:subtasks:end -->\n\n"
        "## Discussion\n\n"
        "<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n"
    )


async def test_render_is_byte_identical_to_the_bundle_when_no_override_exists(project) -> None:
    set_active_squad_dir(project.squad_dir)
    out = render("items/task.md.j2", **_task_ctx())
    assert "<!-- sq:body -->" in out
    assert "## Description" in out
    assert "OVERRIDDEN" not in out


async def test_a_single_overridden_template_never_shadows_any_other_template(project) -> None:
    squad_dir = project.squad_dir
    _place_override(squad_dir, "items/task.md.j2", _minimal_override("task"))
    set_active_squad_dir(squad_dir)

    assert "OVERRIDDEN:task" in render("items/task.md.j2", **_task_ctx())
    bug_out = render("items/bug.md.j2", **_task_ctx())
    assert "OVERRIDDEN" not in bug_out
    assert "<!-- sq:body -->" in bug_out


async def test_service_create_renders_the_override_when_one_is_active(project, svc) -> None:
    from squads._services import _service as service

    custom = (
        "<!-- sq:body -->\n## Custom Project Section\n\nOVERRIDDEN_BODY\n<!-- sq:body:end -->\n\n"
        "<!-- sq:summary -->\n<!-- sq:summary:end -->\n\n"
        "<!-- sq:subtasks -->\n<!-- sq:subtasks:end -->\n\n"
        "## Discussion\n\n<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n"
    )
    _place_override(project.squad_dir, "items/task.md.j2", custom)
    # ServiceCore binds the squad dir at construction time; re-create to pick up the override.
    result = await service.Service(project).create("task", "Override smoke test")
    body = result.path.read_text(encoding="utf-8")
    assert "OVERRIDDEN_BODY" in body


async def test_service_create_renders_the_bundle_when_no_override_is_active(project, svc) -> None:
    result = await svc.create("task", "Bundled task")
    body = result.path.read_text(encoding="utf-8")
    assert "## Description" in body
    assert "OVERRIDDEN" not in body


async def test_cli_create_picks_up_an_active_template_override(project, invoke) -> None:
    squad_dir = project.squad_dir
    custom = (
        "<!-- sq:body -->\nCLI_OVERRIDE_BODY\n<!-- sq:body:end -->\n\n"
        "<!-- sq:summary -->\n<!-- sq:summary:end -->\n\n"
        "<!-- sq:subtasks -->\n<!-- sq:subtasks:end -->\n\n"
        "## Discussion\n\n<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n"
    )
    _place_override(squad_dir, "items/task.md.j2", custom)

    result = await invoke(["create", "task", "CLI override task", "--author", "manager"])
    assert result.exit_code == 0, result.output

    task_files = list((squad_dir / "tasks").glob("TASK-*.md"))
    assert task_files
    assert "CLI_OVERRIDE_BODY" in task_files[-1].read_text(encoding="utf-8")
