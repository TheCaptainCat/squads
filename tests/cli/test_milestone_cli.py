"""CLI smoke test for the milestone type: create, set the target date through the generic
``--set`` door, join a task to it, and read the roll-up the way an operator would — through
``sq milestone <n> show``, not the generic ``sq workflow view`` command.
"""

import pytest

pytestmark = pytest.mark.anyio


def _created_id(output: str) -> str:
    return output.split("→")[0].removeprefix("created").strip()


async def test_create_set_target_date_join_and_show_the_rollup(project, invoke) -> None:
    r = await invoke(["create", "milestone", "Ship 0.14", "--author", "manager"])
    assert r.exit_code == 0, r.output
    mile_id = _created_id(r.output)

    r = await invoke(["milestone", mile_id, "update", "--set", "target_date=2026-12-01"])
    assert r.exit_code == 0, r.output

    r = await invoke(["create", "task", "Do the work", "--author", "manager"])
    assert r.exit_code == 0, r.output
    task_id = _created_id(r.output)

    r = await invoke(["task", task_id, "ref", "add", mile_id, "--kind", "targets"])
    assert r.exit_code == 0, r.output

    r = await invoke(["milestone", mile_id, "show"])
    assert r.exit_code == 0, r.output
    assert "target date" in r.output
    assert "2026-12-01" in r.output
    assert "## Delivered" in r.output
    assert "## Outstanding" in r.output
    assert task_id in r.output

    r = await invoke(["milestone", mile_id, "show", "--json"])
    assert r.exit_code == 0, r.output
    import json

    data = json.loads(r.output)
    assert data["extra"]["target_date"] == "2026-12-01"
    # The roll-up is placed by a body tag now (not a type-attached `views` key): its rendered
    # output is part of the body's own expanded text, the same one plain `show` printed above.
    assert "views" not in data
    assert "## Delivered" in data["body"]
    assert "## Outstanding" in data["body"]
    assert task_id in data["body"]


async def test_an_unparseable_target_date_is_refused_via_the_cli(project, invoke) -> None:
    r = await invoke(["create", "milestone", "Bad date", "--author", "manager"])
    assert r.exit_code == 0, r.output
    mile_id = _created_id(r.output)

    r = await invoke(["milestone", mile_id, "update", "--set", "target_date=not-a-date"])
    assert r.exit_code != 0
    assert "target_date" in r.output
