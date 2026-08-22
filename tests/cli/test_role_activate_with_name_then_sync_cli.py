"""``sq role activate <slug> --name "…"`` followed by ``sq sync`` through the actual command
wiring: the operator's name must still be there afterwards, in the printed activation, in
``sq role <slug> show --json``, and in ``sq list``. The service-layer coverage for the
underlying mechanism lives in
tests/service/test_operator_named_roles_survive_sync.py; this is the CLI smoke test.
"""

import json

import pytest

pytestmark = pytest.mark.anyio


async def test_activate_with_name_then_sync_keeps_the_operator_set_name(project, invoke):
    activated = await invoke(["role", "activate", "architect", "--name", "Ada Lovelace"])
    assert activated.exit_code == 0
    assert "Ada Lovelace" in activated.output

    synced = await invoke(["sync"])
    assert synced.exit_code == 0

    shown = await invoke(["role", "architect", "show", "--json"])
    assert shown.exit_code == 0
    payload = json.loads(shown.output)
    assert payload["full_name"] == "Ada Lovelace"

    listed = await invoke(["list", "-t", "role"])
    assert listed.exit_code == 0
    assert "Ada Lovelace" in listed.output
    assert "Robert Architect" not in listed.output

    checked = await invoke(["check"])
    assert checked.exit_code == 0
