"""The status-banner selection at the CLI: with the type's `validators` list naming the check,
`sq check` and `sq check --json` carry the finding at the declared level (bare exit code 0 at
warn, 3 at error); with nothing selected they carry nothing and exit 0. The shape families
themselves are driven through the service in
tests/service/test_status_banner_runs_only_where_a_type_selects_it.py.
"""

import json

import pytest

from _selection_table import BUNDLED_ROWS, override_toml, plant_banner_items, write_override
from squads._services import _service as service

pytestmark = pytest.mark.anyio

#: Selection shape -> (entries, exit code of ``sq check``, findings expected).
SHAPES = {
    "unselected": ((), 0, False),
    "bare": (("no_status_banner",), 0, True),
    "warn": (("no_status_banner@warn",), 0, True),
    "error": (("no_status_banner@error",), 3, True),
}


@pytest.mark.parametrize("shape", SHAPES)
@pytest.mark.parametrize("row", BUNDLED_ROWS, ids=lambda r: r.id)
async def test_check_reports_the_banner_only_where_selected_and_exits_by_level(
    project, invoke, row, shape
) -> None:
    entries, exit_code, reports = SHAPES[shape]
    write_override(project.squad_dir, override_toml(row, entries))
    await plant_banner_items(service.open_service(), row)

    text = await invoke(["check"])
    assert text.exit_code == exit_code, text.output
    assert ("status/lifecycle banner" in text.output) is reports

    as_json = await invoke(["check", "--json"])
    assert as_json.exit_code == exit_code, as_json.output
    found = [i for i in json.loads(as_json.output) if "status/lifecycle banner" in i["message"]]
    assert bool(found) is reports
    if reports:
        expected_level = "error" if shape == "error" else "warn"
        assert {i["level"] for i in found} == {expected_level}
