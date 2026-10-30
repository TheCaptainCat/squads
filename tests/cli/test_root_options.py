"""The root callback's options: where `sq` runs (`-C`), the time it records (`--at`), the version
line, and the refused `--dir`."""

import json
import shutil

import pytest

from squads import __version__
from tests._profile import selected

P = selected()

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
        ["--at", "2020-01-02T03:04:05Z", "create", P.ref, "Stamped", "--author", "manager"]
    )
    assert created.exit_code == 0, created.output
    shown = await invoke([P.ref, "2", "show", "--json"])
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


@pytest.mark.covers("", "-C")
@pytest.mark.bundled_only("the case shapes a squad from the bundled aliases and types")
async def test_c_help_of_one_squad_does_not_change_the_next_squads_verbs(
    project, invoke, outside, tmp_path_factory, fresh_command_tree
) -> None:
    overridden = tmp_path_factory.mktemp("overridden") / "squad"
    shutil.copytree(project.root, overridden)
    overrides = overridden / "squads" / ".overrides"
    overrides.mkdir()
    (overrides / "workflow.toml").write_text(
        f'# squads:override-base:0.18.0\n[items.bug]\nsubentity_kind = "{P.third_kind}"\n',
        encoding="utf-8",
    )

    await invoke(["-C", str(overridden), P.ref, "1", "show", "--help"])
    result = await invoke(["-C", str(project.root), "bug", "1", f"add-{P.third_kind}", "x"])
    assert (result.exit_code, result.output) == (
        2,
        "Usage: sq bug [OPTIONS] {N} COMMAND [ARGS]...\n"
        "Try 'sq bug --help' for help.\n"
        "╭─ Error ──────────────────────────────────────────────────────────────────────╮\n"
        f"│ No such command 'add-{P.third_kind}'.                                               │\n"
        "╰──────────────────────────────────────────────────────────────────────────────╯\n",
    )


@pytest.mark.covers("<type> show")
async def test_an_alias_of_a_dropped_type_runs_the_type_that_now_declares_it(
    override_project, invoke
) -> None:
    result = await invoke(["f", "8", "show"])
    assert result.exit_code == 0, result.output
    assert "INI-8  (initiative)" in result.output


@pytest.mark.covers("workflow lint", "--json")
@pytest.mark.bundled_only("the case shapes a squad from the bundled aliases and types")
async def test_an_alias_of_a_kept_type_cannot_be_given_to_another_type(project, invoke) -> None:
    overrides = project.squad_dir / ".overrides"
    overrides.mkdir()
    (overrides / "workflow.toml").write_text("[items.bug]\naliases = ['f']\n", encoding="utf-8")
    result = await invoke(["workflow", "lint", "--json"])
    assert result.exit_code == 1, result.output
    messages = [e["message"] for e in json.loads(result.output)["errors"]]
    assert f"duplicate alias 'f': used by '{P.host}' and 'bug'" in "\n".join(messages)
