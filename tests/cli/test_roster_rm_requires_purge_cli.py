"""`rm` on a role, skill or operator refuses without `--purge` and names the command to run;
with `--purge` it deletes the file and leaves `sq check` clean."""

import pytest

pytestmark = pytest.mark.anyio


async def _make(invoke, kind: str) -> str:
    if kind == "role":
        await invoke(["role", "activate", "qa"])
        return "ROLE-000002"
    if kind == "skill":
        await invoke(["skill", "add", "temp-skill"])
        return "SKILL-000002"
    await invoke(["operator", "add", "Temp User"])
    return "OP-000002"


@pytest.mark.parametrize("kind", ["role", "skill", "operator"])
@pytest.mark.parametrize("purge", [False, True])
async def test_roster_rm_refuses_without_purge_and_deletes_with_it(project, invoke, kind, purge):
    item_id = await _make(invoke, kind)
    files = list(project.squad_dir.rglob(f"*{item_id}*.md"))
    assert len(files) == 1

    args = [kind, item_id, "rm"] + (["--purge"] if purge else [])
    result = await invoke(args)

    if purge:
        assert result.exit_code == 0, result.output
        assert not files[0].exists()
    else:
        assert result.exit_code == 1, result.output
        flat = " ".join(result.output.split())
        item_id = item_id.replace("-00000", "-")
        assert f"sq {kind} {item_id} rm --purge" in flat
        assert f"sq {kind} {item_id} status Archived" in flat
        assert files[0].exists()
    check = await invoke(["check"])
    assert check.exit_code == 0, check.output
