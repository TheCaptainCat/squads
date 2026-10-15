"""A squad carrying the generated two-check override lints clean, lists the override as current,
and `sq check` exits 0 with both warnings printed; `--json` carries the item ids. Bare exit
codes throughout.
"""

import json

import pytest

from _helpers import create_item
from _selection_table import BODY_WRITTEN, two_check_override, write_override
from squads._services import _service as service

pytestmark = pytest.mark.anyio


async def test_lint_is_clean_and_the_override_is_current(project, invoke) -> None:
    write_override(project.squad_dir, two_check_override())
    linted = await invoke(["workflow", "lint"])
    assert linted.exit_code == 0, linted.output
    assert "no errors or warnings" in linted.output.lower()
    listed = await invoke(["override", "list"])
    assert listed.exit_code == 0, listed.output
    workflow_line = next(ln for ln in listed.output.splitlines() if "workflow" in ln)
    assert "current" in workflow_line


async def test_check_exits_0_and_names_both_offenders(project, invoke) -> None:
    write_override(project.squad_dir, two_check_override())
    svc = service.open_service()
    long_title = (await create_item(svc, "task", "T" * 121, body=BODY_WRITTEN)).item
    unwritten = (await create_item(svc, "feature", "short")).item

    checked = await invoke(["check"])
    assert checked.exit_code == 0, checked.output
    assert "one-line handle" in checked.output
    assert "still the template scaffold" in checked.output
    rows = json.loads((await invoke(["check", "--json"])).output)
    assert sorted((r["item"], r["level"]) for r in rows) == sorted(
        [(long_title.id, "warn"), (unwritten.id, "warn")]
    )
