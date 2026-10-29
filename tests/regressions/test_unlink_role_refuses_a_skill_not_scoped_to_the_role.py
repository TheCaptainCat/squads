"""`skill unlink-role` on a skill that is not scoped to the role is refused, not reported done."""

import json

import pytest

pytestmark = pytest.mark.anyio


async def test_unlinking_a_role_twice_refuses_the_second_time(project, invoke) -> None:
    await invoke(["skill", "add", "Deploy Notes"])
    await invoke(["skill", "deploy-notes", "link-role", "manager"])
    first = await invoke(["skill", "deploy-notes", "unlink-role", "manager"])
    second = await invoke(["skill", "deploy-notes", "unlink-role", "manager"])
    assert (first.exit_code, first.output) == (0, "SKILL-2 unscoped from ROLE-1 (role resynced)\n")
    assert (second.exit_code, second.output) == (1, "error: SKILL-2 has no scopes ref to ROLE-1\n")
    refs = json.loads((await invoke(["skill", "deploy-notes", "refs", "--json"])).output)
    assert refs["out"] == []
