"""The root callback's options: where `sq` runs (`-C`), the time it records (`--at`), the version
line, and the refused `--dir`."""

import json

import pytest

from squads import __version__

pytestmark = pytest.mark.anyio


@pytest.fixture
def outside(tmp_path_factory, monkeypatch):
    """An empty directory with no squad above it, entered as the working directory."""
    root = tmp_path_factory.mktemp("outside")
    (root / "inner").mkdir()
    monkeypatch.chdir(root)
    return root


@pytest.mark.covers("", "-C")
async def test_c_runs_the_command_in_the_given_directory(project, invoke, outside) -> None:
    result = await invoke(["-C", str(project.root), "list", "--json"])
    assert result.exit_code == 0
    assert [item["id"] for item in json.loads(result.output)] == ["ROLE-1"]


@pytest.mark.covers("", "-C")
async def test_c_values_are_each_relative_to_the_previous_one(project, invoke, outside) -> None:
    result = await invoke(
        ["-C", str(project.root.parent), "-C", project.root.name, "list", "--json"]
    )
    assert result.exit_code == 0
    assert [item["id"] for item in json.loads(result.output)] == ["ROLE-1"]


@pytest.mark.covers("", "-C")
async def test_c_names_the_directory_it_searched_when_it_holds_no_squad(invoke, outside) -> None:
    result = await invoke(["-C", str(outside), "-C", "inner", "list"])
    assert (result.exit_code, result.output) == (
        1,
        f"error: no .squads.toml found in {outside / 'inner'} or any parent directory"
        " — run `sq init`\n",
    )


@pytest.mark.covers("", "-C")
async def test_c_refuses_a_path_that_does_not_exist(invoke, outside) -> None:
    result = await invoke(["-C", "missing", "list"])
    assert (result.exit_code, result.output) == (
        2,
        f"error: -C {outside / 'missing'} does not exist\n",
    )


@pytest.mark.covers("", "--at")
async def test_at_stamps_what_the_command_writes_with_the_given_time(project, invoke) -> None:
    created = await invoke(
        ["--at", "2020-01-02T03:04:05Z", "create", "task", "Stamped", "--author", "manager"]
    )
    assert created.exit_code == 0, created.output
    shown = await invoke(["task", "2", "show", "--json"])
    item = json.loads(shown.output)
    assert (item["created_at"], item["updated_at"]) == ("2020-01-02T03:04:05Z",) * 2


@pytest.mark.covers("", "--at")
async def test_at_refuses_a_time_that_is_not_iso_8601(project, invoke) -> None:
    result = await invoke(["--at", "yesterday", "list"])
    assert (result.exit_code, result.output) == (
        2,
        "error: invalid --at timestamp 'yesterday' "
        "(use ISO 8601, e.g. 2024-01-15 or 2024-01-15T09:30:00Z)\n",
    )


@pytest.mark.covers("", "--version")
async def test_version_prints_the_version_line_and_exits(invoke) -> None:
    result = await invoke(["--version"])
    assert (result.exit_code, result.output) == (0, f"squads {__version__}\n")


@pytest.mark.covers("", "--dir")
async def test_dir_is_refused_naming_c_as_the_replacement(project, invoke) -> None:
    """The option exists only to be refused, so the refusal is the case."""
    result = await invoke(["--dir", str(project.root), "list"])
    assert (result.exit_code, result.output) == (
        2,
        "error: --dir is no longer supported; use -C <path> to run sq as if started in <path> "
        "(the project directory, or any folder inside it)\n",
    )
