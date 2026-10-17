"""``sq -C X init`` and ``sq -C X adopt`` create the project at X, file for file what
``cd X && sq init`` and ``cd X && sq adopt`` create, and leave the directory they were run from
alone. ``-C`` never creates a directory.
"""

import hashlib
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from squads._cli import app
from squads._models._config import SquadsConfig


def _run(args: list[str], cwd: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(sys, "argv", ["sq", *args])
    return CliRunner().invoke(app, args)


def _tree(root: Path) -> dict[str, str]:
    """Relative path -> content digest for every file under *root* (a directory maps to '')."""
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        if p.is_file()
        else ""
        for p in sorted(root.rglob("*"))
    }


def _adoptable(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Leave only squads-native markdown at *root*: a squad that was never indexed or configured."""
    made = _run(
        ["init", "--default-names", "--backend", "none", "--roles", "minimal"], root, monkeypatch
    )
    assert made.exit_code == 0, made.output
    task = _run(["create", "task", "Adoptable", "--author", "manager"], root, monkeypatch)
    assert task.exit_code == 0, task.output
    (root / ".squads.toml").unlink()
    (root / "squads" / ".squads.json").unlink()


def _preplace_names(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = SquadsConfig(
        squad_dir="squads", active_backends=[], init_names={"manager": "Grace Hopper"}
    )
    (root / ".squads.toml").write_text(config.to_toml(), encoding="utf-8")


def _nothing(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    return None


#: row -> (arguments after the command name, how to prepare the target before the run)
_ROWS = {
    "init, no backend": (
        ["init", "--default-names", "--backend", "none", "--roles", "minimal"],
        _nothing,
    ),
    "init, a named squad folder": (
        [
            "init",
            "--default-names",
            "--backend",
            "none",
            "--roles",
            "minimal",
            "--squad-dir",
            "team",
        ],
        _nothing,
    ),
    "init, names pre-placed in the config": (
        ["init", "--default-names", "--backend", "none", "--roles", "manager,architect", "--force"],
        _preplace_names,
    ),
    "adopt over squads-native markdown": (
        ["adopt", "--backend", "none", "--roles", "minimal"],
        _adoptable,
    ),
}


@pytest.mark.parametrize("row", _ROWS)
def test_c_creates_exactly_what_running_from_the_directory_creates(
    row: str, tmp_path: Path, frozen_time, monkeypatch: pytest.MonkeyPatch
) -> None:
    args, prepare = _ROWS[row]
    via_c, via_cd, sibling = tmp_path / "x", tmp_path / "x2", tmp_path / "sibling"
    for folder in (via_c, via_cd, sibling):
        folder.mkdir()
    prepare(via_c, monkeypatch)
    # an identical copy of the prepared target, so both runs start from the same files
    for src in sorted(via_c.rglob("*")):
        dest = via_cd / src.relative_to(via_c)
        dest.mkdir(exist_ok=True) if src.is_dir() else dest.write_bytes(src.read_bytes())

    outside = _run(["-C", str(via_c), *args], sibling, monkeypatch)
    inside = _run(args, via_cd, monkeypatch)

    assert outside.exit_code == inside.exit_code == 0, outside.output + inside.output
    assert _tree(via_c) == _tree(via_cd)
    assert ".squads.toml" in _tree(via_c)
    assert list(sibling.iterdir()) == []


def test_c_init_applies_the_names_pre_placed_at_the_target(
    tmp_path: Path, frozen_time, monkeypatch: pytest.MonkeyPatch
) -> None:
    target, sibling = tmp_path / "x", tmp_path / "sibling"
    target.mkdir()
    sibling.mkdir()
    _preplace_names(target, monkeypatch)

    result = _run(
        [
            "-C",
            str(target),
            "init",
            "--default-names",
            "--backend",
            "none",
            "--roles",
            "manager",
            "--force",
        ],
        sibling,
        monkeypatch,
    )

    assert result.exit_code == 0, result.output
    assert any("Grace Hopper" in p.read_text(encoding="utf-8") for p in target.rglob("ROLE-*.md"))


def test_c_init_into_a_new_subfolder_leaves_the_working_directory_with_only_that_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    work = tmp_path / "work"
    work.mkdir()
    (work / "sub").mkdir()

    result = _run(["-C", "sub", "init", "--default-names", "--backend", "none"], work, monkeypatch)

    assert result.exit_code == 0, result.output
    assert (work / "sub" / ".squads.toml").is_file()
    assert (work / "sub" / "squads").is_dir()
    assert [p.name for p in work.iterdir()] == ["sub"]


@pytest.mark.parametrize("command", ["init", "adopt"])
def test_c_naming_a_missing_directory_exits_2_and_creates_nothing(
    command: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    work = tmp_path / "work"
    work.mkdir()

    result = _run(["-C", "missing", command, "--backend", "none"], work, monkeypatch)

    assert result.exit_code == 2, result.output
    assert list(work.iterdir()) == []
