"""The per-squad rendering-env cache never cross-contaminates: overriding a template in one
squad must not leak into another squad's render. A real module-level-cache-keyed-wrong bug
class, kept as its own explicit test. Bundled/override precedence itself lives in
tests/integration/test_template_override_precedence.py.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from squads._models._item import Item
from squads._rendering._engine import invalidate_squad_dir, render, set_active_squad_dir
from squads._services import _service as service
from squads._workflow import bundled_spec

pytestmark = pytest.mark.anyio


def _place_override(squad_dir: Path, template_name: str, label: str) -> None:
    target = squad_dir / ".overrides" / "templates" / template_name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        f"<!-- sq:body -->\nOVERRIDDEN:{label}\n<!-- sq:body:end -->\n\n"
        "<!-- sq:summary -->\n<!-- sq:summary:end -->\n\n"
        "<!-- sq:subtasks -->\n<!-- sq:subtasks:end -->\n\n"
        "## Discussion\n\n<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n",
        encoding="utf-8",
    )
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


async def test_overriding_one_squads_template_does_not_leak_into_a_second_squad(
    tmp_path, frozen_time, monkeypatch
) -> None:
    root_a, root_b = tmp_path / "a", tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()
    monkeypatch.chdir(root_a)
    result_a = await service.init(root=root_a, roles_spec="minimal")
    monkeypatch.chdir(root_b)
    result_b = await service.init(root=root_b, roles_spec="minimal")

    squad_a, squad_b = result_a.paths.squad_dir, result_b.paths.squad_dir
    _place_override(squad_a, "items/task.md.j2", "A")

    set_active_squad_dir(squad_a)
    out_a = render("items/task.md.j2", **_task_ctx())
    set_active_squad_dir(squad_b)
    out_b = render("items/task.md.j2", **_task_ctx())

    assert "OVERRIDDEN:A" in out_a
    assert "OVERRIDDEN" not in out_b
    assert "<!-- sq:body -->" in out_b
