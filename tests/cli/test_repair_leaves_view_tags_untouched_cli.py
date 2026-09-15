"""``sq repair`` leaves a body carrying a ``sq:view:<name>`` tag byte-identical, end to end
through the CLI -- the retired-region sweep needs no change for this family.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.anyio

_BUNDLED_VIEW = "milestone_rollup"


def _task_file(project) -> Path:
    return next(iter((project.squad_dir / "tasks").glob("TASK-*.md")))


async def test_repair_leaves_a_view_tag_bearing_body_byte_identical(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    placed = await invoke(["task", "2", "view", "add", _BUNDLED_VIEW])
    assert placed.exit_code == 0, placed.output
    before = _task_file(project).read_bytes()

    result = await invoke(["repair"])
    assert result.exit_code == 0, result.output

    assert _task_file(project).read_bytes() == before
