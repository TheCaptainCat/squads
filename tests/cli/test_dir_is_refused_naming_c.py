"""``--dir`` is refused wherever it is written, with ``-C`` named as the replacement, before it
reaches a command or the schema gate; a ``-C`` folder with no squad above it is not initialised
and nothing is written; and a squad kept outside its project tree is reached with
``-C <project>``.
"""

import sys
import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from _gate_layouts import OUTSIDE, digest, lay_out, squad
from squads._cli import _hoist_global_options, app
from squads._models._schema import SCHEMA_VERSION

_MESSAGE = (
    "--dir is no longer supported; use -C <path> to run sq as if started in <path> "
    "(the project directory, or any folder inside it)"
)


def _invoke(args: list[str], cwd: Path, monkeypatch: pytest.MonkeyPatch, *, hoist: bool = False):
    """Run *args* from *cwd*; with *hoist*, through the same argument reordering ``sq`` applies."""
    argv = _hoist_global_options(args) if hoist else args
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(sys, "argv", ["sq", *argv])
    return CliRunner().invoke(app, argv)


#: Every spelling, in every position, a script might still use. ``{x}`` is the folder.
_SPELLINGS = {
    "before the command": ["--dir", "{x}", "list"],
    "after the command": ["list", "--dir", "{x}"],
    "after an addressed item": ["task", "3", "show", "--dir", "{x}"],
    "equals form before": ["--dir={x}", "list"],
    "equals form after": ["list", "--dir={x}"],
    "on init": ["init", "--dir", "{x}"],
    "on a migrate command": ["migrate", "up", "--dir", "{x}"],
    "with no value": ["list", "--dir"],
}


@pytest.mark.parametrize("direction", ["equal", "behind", "ahead"])
@pytest.mark.parametrize("spelling", _SPELLINGS)
def test_dir_exits_2_naming_c_and_changes_nothing(
    spelling: str, direction: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = squad(tmp_path, direction, "none")
    before = digest(tmp_path)
    args = [a.format(x=root) for a in _SPELLINGS[spelling]]

    result = _invoke(args, root, monkeypatch, hoist=True)

    assert result.exit_code == 2, result.output
    assert _MESSAGE in " ".join(result.output.split())
    assert digest(tmp_path) == before


_COMMANDS = {
    "list": ["list"],
    "check": ["check"],
    "repair": ["repair"],
    "migrate up": ["migrate", "up"],
}


@pytest.mark.parametrize("command", _COMMANDS)
def test_a_mistyped_c_is_not_initialised_and_writes_nothing(
    command: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    squad(tmp_path, "equal", "none")
    lone = tmp_path / "lone"
    lone.mkdir()
    before = digest(tmp_path)

    result = _invoke(["-C", str(lone), *_COMMANDS[command]], tmp_path, monkeypatch)

    assert result.exit_code == 1, result.output
    assert f"no .squads.toml found in {lone}" in " ".join(result.output.split())
    assert digest(tmp_path) == before
    assert not (lone / ".squads.json").exists()


@pytest.mark.parametrize("layout", OUTSIDE)
def test_a_squad_outside_its_project_is_listed_through_c_naming_the_project(
    layout: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = squad(tmp_path, "equal", "none")
    lay_out(root, layout)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    result = _invoke(["-C", str(root), "list"], elsewhere, monkeypatch)

    assert result.exit_code == 0, result.output
    assert "no .squads.toml" not in result.output


@pytest.mark.parametrize("layout", OUTSIDE)
def test_a_behind_squad_outside_its_project_is_migrated_through_c_naming_the_project(
    layout: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = squad(tmp_path, "behind", "none")
    lay_out(root, layout)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    result = _invoke(["-C", str(root), "migrate", "up"], elsewhere, monkeypatch)

    stamped = tomllib.loads((root / ".squads.toml").read_text(encoding="utf-8"))["schema_version"]
    assert result.exit_code == 0, result.output
    assert stamped == SCHEMA_VERSION
