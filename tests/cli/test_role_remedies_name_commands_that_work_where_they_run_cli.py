"""The commands a role message tells the user to run work from where the user runs them, and a
role override is refused for a slug no role holds."""

import json
import re
from pathlib import Path

import pytest

from squads import __version__
from squads._models._participants import ROLE_GROUP_VERBS

pytestmark = pytest.mark.anyio


def _ghost_file(project) -> Path:
    path = project.squad_dir / ".overrides" / "roles" / "ghost.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'# squads:override-base:{__version__}\nfull_name = "Gwen"\n', encoding="utf-8")
    return path


def _named_file(text: str) -> str:
    return re.search(r"--file (\S+?)`", " ".join(text.split())).group(1)  # type: ignore[union-attr]


@pytest.mark.parametrize("where", ["project-root", "squad-dir", "elsewhere-with-C"])
@pytest.mark.parametrize("surface", ["activate-refusal", "check-finding"])
async def test_the_file_a_remedy_names_exists_from_where_the_command_runs(
    project, invoke, monkeypatch, tmp_path_factory, where: str, surface: str
) -> None:
    file = _ghost_file(project)
    args = ["-C", str(project.root)] if where == "elsewhere-with-C" else []
    if where == "squad-dir":
        monkeypatch.chdir(project.squad_dir)
    elif where == "elsewhere-with-C":
        monkeypatch.chdir(tmp_path_factory.mktemp("elsewhere"))

    if surface == "activate-refusal":
        result = await invoke([*args, "role", "activate", "ghost"])
        assert result.exit_code == 1, result.output
        named = _named_file(result.output)
    else:
        result = await invoke([*args, "check", "--json"])
        found = [f for f in json.loads(result.output) if f["rule"] == "override_loads"]
        assert found, result.output
        named = _named_file(found[0]["message"])

    assert (Path.cwd() / named).resolve() == file.resolve()


async def test_scaffolding_an_override_for_a_slug_no_role_holds_is_refused_and_writes_nothing(
    project, invoke
) -> None:
    result = await invoke(["override", "scaffold", "--role", "ghost"])

    flat = " ".join(result.output.split())
    assert result.exit_code == 1, result.output
    assert "sq role add ghost" in flat and "sq role activate ghost" in flat
    assert not (project.squad_dir / ".overrides" / "roles" / "ghost.toml").exists()


async def test_the_role_help_epilog_lists_every_group_verb(project, invoke) -> None:
    result = await invoke(["role", "--help"])

    assert ", ".join(sorted(ROLE_GROUP_VERBS)) in " ".join(result.output.split())
