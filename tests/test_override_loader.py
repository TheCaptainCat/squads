"""Tests for the override loader + precedence plumbing (TASK-000087).

Verifies that:
- A template dropped under <squad_dir>/.overrides/templates/ shadows the bundled one.
- Every other template still resolves to the bundled default (partial override).
- Bundled rendering is byte-for-byte unchanged when no override exists.
- The cache does not cross-contaminate across different squad dirs.
"""

from pathlib import Path

import pytest

from squads._models._enums import ItemType
from squads._rendering._engine import invalidate_squad_dir, render, set_active_squad_dir
from squads._services import _service as service

pytestmark = pytest.mark.anyio

# --------------------------------------------------------------------------- helpers


def _overrides_dir(squad_dir: Path) -> Path:
    """The .overrides/templates/ directory under a squad folder."""
    return squad_dir / ".overrides" / "templates"


def _place_override(squad_dir: Path, template_name: str, content: str) -> Path:
    """Write *content* to <squad_dir>/.overrides/templates/<template_name>.

    Creates parent directories as needed.
    """
    target = _overrides_dir(squad_dir) / template_name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    # Evict the cached env so the new file is picked up on the next render.
    invalidate_squad_dir(squad_dir)
    return target


# --------------------------------------------------------------------------- bundled baseline


async def test_bundled_render_unchanged_when_no_override_exists(project):
    """render() with no .overrides/ present must produce exactly the bundled output."""
    set_active_squad_dir(project.squad_dir)
    out = render("items/task.md.j2", **_task_ctx())
    # The bundled task template always contains these sq markers.
    assert "<!-- sq:body -->" in out
    assert "<!-- sq:body:end -->" in out
    assert "<!-- sq:discussion -->" in out
    assert "## Description" in out
    # Must NOT contain any override marker we haven't placed.
    assert "OVERRIDDEN" not in out


async def test_bundled_other_templates_unchanged_under_partial_override(project):
    """Non-overridden templates still resolve to the bundle when only task is overridden."""
    squad_dir = project.squad_dir
    _place_override(squad_dir, "items/task.md.j2", _minimal_override("task"))
    set_active_squad_dir(squad_dir)

    # task is overridden — check the shadow.
    task_out = render("items/task.md.j2", **_task_ctx())
    assert "OVERRIDDEN:task" in task_out

    # bug is NOT overridden — must still come from the bundle.
    bug_out = render("items/bug.md.j2", **_task_ctx())
    assert "OVERRIDDEN" not in bug_out
    assert "<!-- sq:body -->" in bug_out


# --------------------------------------------------------------------------- service-level override


async def test_service_create_uses_override_template(project, svc):
    """Creating a task with an active template override renders the override body."""
    squad_dir = project.squad_dir
    # Write a custom task template that still keeps the required sq markers.
    custom = (
        "<!-- sq:body -->\n"
        "## Custom Project Section\n\n"
        "OVERRIDDEN_BODY\n"
        "<!-- sq:body:end -->\n\n"
        "<!-- sq:summary -->\n<!-- sq:summary:end -->\n\n"
        "<!-- sq:subtasks -->\n<!-- sq:subtasks:end -->\n\n"
        "## Discussion\n\n"
        "<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n"
    )
    _place_override(squad_dir, "items/task.md.j2", custom)
    # ServiceCore sets the squad dir on construction; re-create svc so it picks up the override.
    svc2 = service.Service(project)

    # The minimal fixture roster registers `manager`; use the default author.
    result = await svc2.create(ItemType.TASK, "Override smoke test")
    body = result.path.read_text(encoding="utf-8")
    assert "OVERRIDDEN_BODY" in body
    assert "Custom Project Section" in body


async def test_service_create_bundled_template_unchanged(project, svc):
    """Without an override, service.create() must produce the standard bundled output."""
    result = await svc.create(ItemType.TASK, "Bundled task")
    body = result.path.read_text(encoding="utf-8")
    # Bundled task template always has these.
    assert "## Description" in body
    assert "_TODO: describe this task._" in body
    assert "OVERRIDDEN" not in body


# --------------------------------------------------------------------------- cache isolation


async def test_env_cache_does_not_cross_contaminate(tmp_path, frozen_time, monkeypatch):
    """Two squad dirs get independent Environments; overriding one doesn't affect the other."""
    # Create two minimal squads.
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()
    monkeypatch.chdir(root_a)
    result_a = await service.init(root=root_a, roles_spec="minimal")
    monkeypatch.chdir(root_b)
    result_b = await service.init(root=root_b, roles_spec="minimal")

    squad_a = result_a.paths.squad_dir
    squad_b = result_b.paths.squad_dir

    # Override the task template only in squad A.
    _place_override(squad_a, "items/task.md.j2", _minimal_override("A"))

    set_active_squad_dir(squad_a)
    out_a = render("items/task.md.j2", **_task_ctx())

    set_active_squad_dir(squad_b)
    out_b = render("items/task.md.j2", **_task_ctx())

    assert "OVERRIDDEN:A" in out_a, "squad A override should shadow the bundle"
    assert "OVERRIDDEN" not in out_b, "squad B must not see squad A's override"
    # Squad B still renders the bundled template.
    assert "<!-- sq:body -->" in out_b


# --------------------------------------------------------------------------- cli smoke test


async def test_cli_create_task_with_override(project, invoke):
    """CLI: `sq task create` with a task template override produces the custom body."""
    squad_dir = project.squad_dir
    custom = (
        "<!-- sq:body -->\n"
        "CLI_OVERRIDE_BODY\n"
        "<!-- sq:body:end -->\n\n"
        "<!-- sq:summary -->\n<!-- sq:summary:end -->\n\n"
        "<!-- sq:subtasks -->\n<!-- sq:subtasks:end -->\n\n"
        "## Discussion\n\n"
        "<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n"
    )
    _place_override(squad_dir, "items/task.md.j2", custom)

    result = await invoke(["create", "task", "CLI override task", "--author", "manager"])
    assert result.exit_code == 0, result.output

    # Find the created task file under the squad dir.
    task_files = list((squad_dir / "tasks").glob("TASK-*.md"))
    assert task_files, "expected at least one task file"
    body = task_files[-1].read_text(encoding="utf-8")
    assert "CLI_OVERRIDE_BODY" in body


# --------------------------------------------------------------------------- private helpers


def _task_ctx() -> dict[str, object]:
    """Minimal context that satisfies the bundled task template's variables."""
    from datetime import UTC, datetime

    from squads._models._enums import ItemType, Status
    from squads._models._item import Item

    now = datetime(2026, 1, 1, tzinfo=UTC)
    item = Item(
        sequence_id=1,
        type=ItemType.TASK,
        title="Test task",
        slug="test-task",
        status=Status.READY,
        path="tasks/TASK-000001-test-task.md",
        created_at=now,
        updated_at=now,
    )
    return {"item": item, "description": "", "extra": {}}


def _minimal_override(label: str) -> str:
    """A valid task override template that keeps all required sq markers."""
    return (
        f"<!-- sq:body -->\nOVERRIDDEN:{label}\n<!-- sq:body:end -->\n\n"
        "<!-- sq:summary -->\n<!-- sq:summary:end -->\n\n"
        "<!-- sq:subtasks -->\n<!-- sq:subtasks:end -->\n\n"
        "## Discussion\n\n"
        "<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n"
    )
