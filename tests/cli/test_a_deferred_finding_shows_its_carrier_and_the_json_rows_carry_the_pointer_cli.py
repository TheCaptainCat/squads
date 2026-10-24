"""`finding <k> update --status Deferred --deferred-to <n>` stores the pointer; the finding's
display line names the carrier and its title, and every sub-entity JSON row carries
`deferred_to`, `null` when absent.
"""

import json

import pytest

pytestmark = pytest.mark.anyio


async def _deferred_finding(invoke) -> None:
    """A review (number 2) with two findings, and a task (number 3) to carry the work."""
    await invoke(["create", "review", "R", "--author", "manager"])
    await invoke(["create", "task", "Carry the work", "--author", "manager"])
    await invoke(["review", "2", "add-finding", "one"])
    await invoke(["review", "2", "add-finding", "two"])


async def test_update_stores_the_pointer_given_as_a_bare_number(project, invoke) -> None:
    await _deferred_finding(invoke)
    done = await invoke(
        ["review", "2", "finding", "1", "update", "--status", "Deferred", "--deferred-to", "3"]
    )
    assert done.exit_code == 0, done.output
    row = json.loads((await invoke(["review", "2", "finding", "1", "show", "--json"])).output)
    assert (row["status"], row["deferred_to"]) == ("Deferred", "TASK-3")


async def test_the_display_line_names_the_carrier_and_its_title(project, invoke) -> None:
    await _deferred_finding(invoke)
    await invoke(
        ["review", "2", "finding", "1", "update", "--status", "Deferred", "--deferred-to", "3"]
    )
    shown = await invoke(["review", "2", "show", "--full"])
    assert "Deferred to TASK-3 — Carry the work" in shown.output
    single = await invoke(["review", "2", "finding", "1", "show"])
    assert "deferred to: TASK-3 — Carry the work" in single.output


async def test_every_json_row_carries_the_pointer_and_null_when_absent(project, invoke) -> None:
    await _deferred_finding(invoke)
    await invoke(
        ["review", "2", "finding", "1", "update", "--status", "Deferred", "--deferred-to", "3"]
    )
    listed = json.loads((await invoke(["review", "2", "findings", "--json"])).output)
    assert [row["deferred_to"] for row in listed] == ["TASK-3", None]
    shown = [
        json.loads((await invoke(["review", "2", "finding", k, "show", "--json"])).output)
        for k in ("1", "2")
    ]
    assert [row["deferred_to"] for row in shown] == ["TASK-3", None]
    whole = json.loads((await invoke(["review", "2", "show", "--json"])).output)
    assert [row["deferred_to"] for row in whole["subentities"]] == ["TASK-3", None]
