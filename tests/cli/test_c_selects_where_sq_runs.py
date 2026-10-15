"""``sq -C <path> <command>`` runs as if sq had been started in ``<path>``: the squad is found by
the usual walk-up from there, a path that is not a directory is refused before anything else
runs, ``-C`` is only read before the command, and the root help documents it.
"""

import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from squads._cli import app

_HELP = "Run as if sq was started in PATH (repeatable; relative to the previous -C)."


def _run(args: list[str], cwd: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(sys, "argv", ["sq", *args])
    return CliRunner().invoke(app, args)


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """A project with a squad in ``squads/``, a subfolder, a plain file, and three unrelated
    directories: one to run from, one in no squad, one that does not exist."""
    project = tmp_path / "project"
    (project / "docs").mkdir(parents=True)
    result = _run(
        ["init", "--default-names", "--backend", "none", "--roles", "minimal"], project, monkeypatch
    )
    assert result.exit_code == 0, result.output
    here = tmp_path / "here"
    bare = tmp_path / "bare"
    here.mkdir()
    bare.mkdir()
    file = tmp_path / "plain.txt"
    file.write_text("x", encoding="utf-8")
    return {
        "project": project,
        "squad": project / "squads",
        "docs": project / "docs",
        "here": here,
        "bare": bare,
        "file": file,
        "missing": tmp_path / "missing",
    }


def _flat(output: str) -> str:
    return " ".join(output.replace("│", " ").split())


@pytest.mark.parametrize("target", ["project", "squad", "docs"])
def test_c_lists_the_same_as_running_from_the_folder(
    target: str, world: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    inside = _run(["list"], world[target], monkeypatch)
    outside = _run(["-C", str(world[target]), "list"], world["here"], monkeypatch)

    assert inside.exit_code == outside.exit_code == 0, outside.output
    assert "ROLE-1" in outside.output
    assert outside.output == inside.output


_REFUSED = {
    "a directory that does not exist": (["-C", "{missing}", "list"], "{missing}"),
    "a regular file": (["-C", "{file}", "list"], "{file}"),
    "an unknown command after a missing directory": (["-C", "{missing}", "widget"], "{missing}"),
    "a missing directory in a chain": (["-C", "{project}", "-C", "nope", "list"], "nope"),
}


@pytest.mark.parametrize("row", _REFUSED)
def test_c_naming_no_directory_exits_2_on_its_own_message(
    row: str, world: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    args, named = _REFUSED[row]
    paths = {k: str(v) for k, v in world.items()}
    before = sorted(p.name for p in world["here"].iterdir())

    result = _run([a.format(**paths) for a in args], world["here"], monkeypatch)

    assert result.exit_code == 2, result.output
    assert named.format(**paths) in _flat(result.output)
    assert "No such command" not in result.output
    assert sorted(p.name for p in world["here"].iterdir()) == before


def test_a_directory_in_no_squad_is_not_initialised_and_is_named(
    world: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _run(["-C", str(world["bare"]), "list"], world["here"], monkeypatch)

    assert result.exit_code == 1, result.output
    assert f"no .squads.toml found in {world['bare']} or any parent directory" in _flat(
        result.output
    )


def test_without_c_the_not_initialised_message_does_not_name_a_directory(
    world: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _run(["list"], world["bare"], monkeypatch)

    assert result.exit_code == 1, result.output
    assert "no .squads.toml found in this or any parent directory — run `sq init`" in _flat(
        result.output
    )


def test_c_after_the_command_is_clicks_own_unknown_option(
    world: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _run(["list", "-C", str(world["project"])], world["here"], monkeypatch)

    assert result.exit_code == 2, result.output
    assert "No such option" in result.output


def test_c_as_the_value_of_another_option_is_text_not_the_flag(
    world: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    created = _run(["create", "task", "T", "--author", "manager"], world["project"], monkeypatch)
    assert created.exit_code == 0, created.output
    number = created.output.split("TASK-")[1].split()[0].split("]")[0].lstrip("0")

    commented = _run(
        ["task", number, "comment", "--as", "manager", "-m", "-C"], world["project"], monkeypatch
    )
    shown = _run(["task", number, "show", "--comments"], world["project"], monkeypatch)

    assert commented.exit_code == 0, commented.output
    assert "\n- -C" in shown.output


def test_the_root_help_documents_c_without_a_long_form(
    world: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _run(["--help"], world["here"], monkeypatch)

    flat = _flat(result.output)
    assert result.exit_code == 0
    assert "-C PATH" in flat
    assert _HELP in flat
    assert "--change-dir" not in flat
