"""``sq -C <folder> <command>`` run from an unrelated directory equals ``cd <folder> && sq
<command>``: same exit code, same stdout, same stderr, same bytes under the whole scratch root.

This is the property that makes the schema gate sound. The gate resolves the squad from the
directory the command runs in, so it sees the configuration a plain run in that folder would see,
whatever the layout: a squad at the project root, nested, renamed, outside its project tree, under
another squad's folder, behind a symbolic link.
"""

import shutil
import sys
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest
from typer.testing import CliRunner

from _gate_layouts import (
    ENCLOSED,
    LAYOUTS,
    OUTSIDE,
    digest,
    lay_out,
    squad,
)
from squads._cli import app
from squads._models._schema import SCHEMA_VERSION


@dataclass(frozen=True)
class _Built:
    """A laid-out scratch root and the three places ``-C`` is pointed at."""

    world: Path
    folder: Path
    project: Path
    sub: Path


def _inner_under(outer_direction: str) -> Callable[[Path, str], _Built]:
    def build(world: Path, direction: str) -> _Built:
        outer = squad(world / "outer", outer_direction, "none")
        outer_folder = lay_out(outer, "nested")
        inner = squad(world / "inner-src", direction, "none")
        target = outer_folder / "inner"
        shutil.move(inner, target)
        return _Built(world, target, target, target / "tasks")

    return build


def _through_a_symlinked_path(world: Path, direction: str) -> _Built:
    real = squad(world / "real-parent", direction, "none")
    link = world / "link-to-project"
    link.symlink_to(real, target_is_directory=True)
    return _Built(world, link, link, link / "tasks")


def _a_subfolder_of_the_squad(world: Path) -> Path:
    return sorted(world.rglob("tasks"))[0]


def _plain(layout: str) -> Callable[[Path, str], _Built]:
    def build(world: Path, direction: str) -> _Built:
        root = squad(world / "p", direction, "none")
        folder = lay_out(root, layout)
        return _Built(world, folder, root, _a_subfolder_of_the_squad(world))

    return build


_LAYOUT_BUILDERS: dict[str, Callable[[Path, str], _Built]] = {
    **{layout: _plain(layout) for layout in [*LAYOUTS, *ENCLOSED, *OUTSIDE]},
    "inner-squad-under-a-behind-outer-squad": _inner_under("behind"),
    "inner-squad-under-an-ahead-outer-squad": _inner_under("ahead"),
    "project-reached-through-a-symlinked-path": _through_a_symlinked_path,
}

_COMMANDS: dict[str, list[str]] = {
    "list": ["list"],
    "repair": ["repair"],
    "migrate repad": ["migrate", "repad", "7"],
    "migrate up": ["migrate", "up"],
}


def _snapshot(src: Path, dest: Path) -> None:
    shutil.copytree(src, dest, symlinks=True)


def _restore(snapshot: Path, world: Path) -> None:
    shutil.rmtree(world)
    shutil.copytree(snapshot, world, symlinks=True)


def _outcome(args: list[str], cwd: Path, world: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(sys, "argv", ["sq", *args])
    result = CliRunner().invoke(app, args)
    return result.exit_code, result.stdout, result.stderr, digest(world)


@pytest.mark.parametrize("direction", ["behind", "ahead", "equal"])
@pytest.mark.parametrize("command", _COMMANDS)
@pytest.mark.parametrize("target", ["folder", "project", "sub"])
@pytest.mark.parametrize("layout", _LAYOUT_BUILDERS)
def test_c_runs_exactly_as_cd_into_the_folder_would(
    layout: str,
    target: str,
    command: str,
    direction: str,
    tmp_path: Path,
    frozen_time,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = tmp_path / "world"
    world.mkdir()
    built = _LAYOUT_BUILDERS[layout](world, direction)
    where = getattr(built, target)
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    saved = tmp_path / "saved"
    _snapshot(world, saved)

    code_c, out_c, err_c, files_c = _outcome(
        ["-C", str(where), *_COMMANDS[command]], unrelated, world, monkeypatch
    )
    _restore(saved, world)
    code_cd, out_cd, err_cd, files_cd = _outcome(_COMMANDS[command], where, world, monkeypatch)

    # The one deliberate difference: with -C the not-initialised error names the directory.
    err_c = err_c.replace(f"found in {where} or any", "found in this or any")
    assert (code_c, out_c, err_c, files_c) == (code_cd, out_cd, err_cd, files_cd)
    assert list(unrelated.iterdir()) == []


# --- the gate, at each place -C can point -------------------------------------------------------

_GATED = ["list", "repair"]


@pytest.mark.parametrize("target", ["folder", "project", "sub"])
@pytest.mark.parametrize("command", _GATED)
def test_c_at_each_place_refuses_a_behind_squad_and_writes_nothing(
    target: str, command: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = tmp_path / "world"
    world.mkdir()
    built = _plain("nested")(world, "behind")
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    before = digest(world)

    code, _, err, after = _outcome(
        ["-C", str(getattr(built, target)), *_COMMANDS[command]], unrelated, world, monkeypatch
    )

    assert code == 1
    assert "Run sq migrate up to upgrade it" in err
    assert after == before


@pytest.mark.parametrize("target", ["folder", "project", "sub"])
def test_c_at_each_place_lets_migrate_up_migrate_a_behind_squad(
    target: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = tmp_path / "world"
    world.mkdir()
    built = _plain("nested")(world, "behind")
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()

    code, out, _, _ = _outcome(
        ["-C", str(getattr(built, target)), "migrate", "up"], unrelated, world, monkeypatch
    )

    stamped = tomllib.loads((built.project / ".squads.toml").read_text(encoding="utf-8"))
    assert code == 0, out
    assert stamped["schema_version"] == SCHEMA_VERSION
