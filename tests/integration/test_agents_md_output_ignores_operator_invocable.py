"""``AGENTS.md`` has no slash menu and no per-skill entry: a stored ``operator_invocable`` on any
skill changes none of its bytes and draws no warning, with either backend set active."""

import pytest

from squads._services import _service as service

pytestmark = pytest.mark.anyio

SKILLS = ["squads", "sq-memory", "greeting", "sq-task"]


@pytest.mark.parametrize("backends", [["agents_md"], ["claude_code", "agents_md"]])
@pytest.mark.parametrize("choice", ["yes", "no"])
async def test_agents_md_is_byte_identical_with_and_without_stored_values(
    backends, choice, tmp_path, monkeypatch, invoke
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = (await service.init(root=tmp_path, backend=backends, roles_spec="minimal")).paths
    svc = service.Service(paths)
    assert (await invoke(["sync"])).exit_code == 0
    before = (tmp_path / "AGENTS.md").read_bytes()

    await svc.add_skill("onboarding", operator_invocable=choice)
    for slug in SKILLS:  # the bundled skills exist only where a backend seeds them
        item = await svc.roster_item("skill", slug)
        if item is not None:
            await svc.update(item.id, operator_invocable=choice)
    r = await invoke(["sync"])

    assert r.exit_code == 0, r.output
    assert "operator" not in r.output.lower()
    assert (tmp_path / "AGENTS.md").read_bytes() == before
    assert b"invocable" not in before
