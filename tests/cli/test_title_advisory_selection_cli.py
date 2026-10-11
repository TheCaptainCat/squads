"""The create-time title advisory at the CLI: `add-<kind>` prints it, and carries it in
`--json`, exactly when the type selects `subentity_title_max` and the title is longer than the
selected number; the exit code is 0 either way, even when the selection makes `sq check` fail.
The shape families are driven through the service in
tests/service/test_title_advisory_follows_the_selection.py.
"""

import json

import pytest

from _helpers import create_item
from _selection_table import HOSTING_ROWS, TITLE_SHAPES, override_toml, service_with

pytestmark = pytest.mark.anyio

#: Hosting rows whose type holds no title check unless it names one.
UNSELECTED_IDS = {"records-hosting-a-kind"}


@pytest.mark.parametrize("shape", TITLE_SHAPES)
@pytest.mark.parametrize("row", HOSTING_ROWS, ids=lambda r: r.id)
async def test_add_prints_the_advisory_and_exits_0_only_for_a_selecting_type(
    project, invoke, row, shape
) -> None:
    entries, threshold, level = TITLE_SHAPES[shape]
    if threshold is None and row.id not in UNSELECTED_IDS:
        pytest.skip(
            "this hosting type runs the check without a selection until the bundle drops it"
        )
    svc = service_with(project.squad_dir, override_toml(row, entries))
    parent = (await create_item(svc, row.type, "parent")).item
    number = threshold if threshold is not None else 120
    base = [row.type, str(parent.sequence_id), f"add-{row.kind}"]

    for length in (number - 1, number, number + 1):
        title = "x" * length
        fires = threshold is not None and length > threshold

        text = await invoke([*base, title])
        assert text.exit_code == 0, text.output
        assert ("one-line handle" in text.output) is fires, (length, text.output)

        as_json = await invoke([*base, title, "--json"])
        assert as_json.exit_code == 0, as_json.output
        assert (json.loads(as_json.output).get("title_advisory") is not None) is fires

    checked = await invoke(["check"])
    assert checked.exit_code == (3 if level == "error" else 0), checked.output
    assert ("threshold:" in checked.output) is (threshold is not None)
