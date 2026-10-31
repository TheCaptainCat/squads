"""What a command says about where and under which session it runs: the paths its messages spell
come from the directory it started in, and the reflog records the session lineage the environment
declares. In remote mode both reach the daemon only as headers, so dropping one fails these."""

import json
from pathlib import Path

import pytest

from squads._paths import SquadPaths
from tests._profile import selected

P = selected()

pytestmark = pytest.mark.anyio


@pytest.mark.covers("role activate", "slug")
@pytest.mark.bundled_only("the role command group is the bundled squad's")
async def test_a_remedy_path_is_spelled_from_the_directory_the_command_started_in(
    project: SquadPaths, invoke, monkeypatch
) -> None:
    ghost = project.squad_dir / ".overrides" / "roles" / "ghost.toml"
    ghost.parent.mkdir(parents=True)
    ghost.write_text('name = "Ghost"\n', encoding="utf-8")
    monkeypatch.chdir(project.squad_dir)
    result = await invoke(["role", "activate", "ghost"])
    assert (result.exit_code, result.output) == (
        1,
        "error: role 'ghost' is declared only by .overrides/roles/ghost.toml, which layers over "
        "a role and does not define one; create the role with `sq role add ghost --file "
        f"{Path('.overrides', 'roles', 'ghost.toml')!s}`\n",
    )


@pytest.mark.covers("reflog", "--json")
async def test_the_reflog_records_the_session_lineage_the_environment_declares(
    project: SquadPaths, invoke, monkeypatch
) -> None:
    monkeypatch.setenv("SQUADS_SESSION_ID", "session-under-test")
    monkeypatch.setenv("SQUADS_PARENT_SESSION_ID", "parent-under-test")
    created = await invoke(["create", P.ref, "Seen", "--author", "manager"])
    assert created.exit_code == 0, created.output
    reflog = await invoke(["reflog", "--json", "--op", "create"])
    last = json.loads(reflog.output)[-1]
    assert (last["session_id"], last["parent_session_id"]) == (
        "session-under-test",
        "parent-under-test",
    )
