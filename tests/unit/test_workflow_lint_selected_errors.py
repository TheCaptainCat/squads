"""One table: every ``[selected]`` error of a workflow override is listed in one lint run, whatever
the order or mix of sections, while loading the spec still refuses on the first."""

from pathlib import Path

import pytest

from squads._errors import SquadsError
from squads._workflow._loader import lint_workflow_spec, load_workflow_spec

#: ``[selected]`` body -> the error locations one lint run lists, in order.
_ROWS = {
    "squad then unknown section": (
        'squad = ["x"]\nbogus = ["y"]',
        ["selected.squad", "selected.bogus"],
    ),
    "unknown section then squad": (
        'bogus = ["y"]\nsquad = ["x"]',
        ["selected.squad", "selected.bogus"],
    ),
    "unknown section then unknown item key": (
        'bogus = ["y"]\nitems = ["nonesuch"]',
        ["selected.bogus", "selected.items.nonesuch"],
    ),
    "squad then unknown item key": (
        'squad = ["x"]\nitems = ["nonesuch"]',
        ["selected.squad", "selected.items.nonesuch"],
    ),
    "squad, unknown section and unknown item key": (
        'squad = ["x"]\nbogus = ["y"]\nitems = ["nonesuch"]',
        ["selected.squad", "selected.bogus", "selected.items.nonesuch"],
    ),
    "list shape then unknown item key": (
        'items = ["task"]\nstatuses = "Draft"\nlifecycles = ["nonesuch"]',
        ["selected.statuses", "selected.lifecycles.nonesuch"],
    ),
    "unknown section then non-string entry": (
        'bogus = ["y"]\nstatuses = [1]',
        ["selected.bogus", "selected.statuses"],
    ),
    "repeated unknown item key": (
        'items = ["nonesuch", "nonesuch"]',
        ["selected.items.nonesuch"],
    ),
    "unknown item key alone": ('items = ["nonesuch"]', ["selected.items.nonesuch"]),
    "squad alone": ('squad = ["x"]', ["selected.squad"]),
    "unknown section alone": ('bogus = ["y"]', ["selected.bogus"]),
}


def _override(squad_dir: Path, selected: str, before: str = "") -> None:
    override = squad_dir / ".overrides" / "workflow.toml"
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text(f"{before}[selected]\n{selected}\n", encoding="utf-8")


@pytest.mark.parametrize("row", list(_ROWS))
def test_one_lint_run_lists_every_selected_error(tmp_path: Path, row: str) -> None:
    selected, locations = _ROWS[row]
    _override(tmp_path, selected)

    findings = [f for f in lint_workflow_spec(tmp_path) if f[1].startswith("selected")]

    assert [f[1] for f in findings] == locations


@pytest.mark.parametrize("row", list(_ROWS))
def test_loading_the_spec_refuses_on_the_first_selected_error(tmp_path: Path, row: str) -> None:
    selected, locations = _ROWS[row]
    _override(tmp_path, selected)

    with pytest.raises(SquadsError) as refused:
        load_workflow_spec(squad_dir=tmp_path)

    message = str(refused.value)
    assert locations[0] in message
    assert [location for location in locations[1:] if location in message] == []


_RETIRED = '[items.task]\nviews = ["x"]\n\n'


@pytest.mark.parametrize("row", list(_ROWS))
def test_a_retired_key_does_not_hide_a_selected_error(tmp_path: Path, row: str) -> None:
    selected, locations = _ROWS[row]
    _override(tmp_path, selected, before=_RETIRED)

    paths = [f[1] for f in lint_workflow_spec(tmp_path) if f[0] == "error"]

    assert "items.task.views" in paths
    assert [path for path in paths if path.startswith("selected")] == locations
