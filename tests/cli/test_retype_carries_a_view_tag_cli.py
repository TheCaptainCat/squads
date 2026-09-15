"""``sq <type> <n> retype <new_type>`` carries a placed ``sq:view:<name>`` tag verbatim to the
new type, end to end through the CLI, and ``sq check`` stays clean afterwards — a view is not
type-scoped, so the name still resolves under the new type.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.anyio

_BUNDLED_VIEW = "milestone_rollup"


def _bug_file(project) -> Path:
    return next(iter((project.squad_dir / "bugs").glob("BUG-*.md")))


async def test_retype_carries_the_view_tag_and_check_stays_clean(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    placed = await invoke(["task", "2", "view", "add", _BUNDLED_VIEW])
    assert placed.exit_code == 0, placed.output

    result = await invoke(["task", "2", "retype", "bug"])
    assert result.exit_code == 0, result.output

    text = _bug_file(project).read_text(encoding="utf-8")
    assert f"<!-- sq:view:{_BUNDLED_VIEW} -->" in text

    check = await invoke(["check"])
    assert check.exit_code == 0, check.output
