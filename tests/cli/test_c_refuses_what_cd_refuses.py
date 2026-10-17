"""``-C`` enters each component the way ``chdir`` does: a component that is missing, not a
directory, or not searchable is refused with its own message even when a later ``..`` would
have stepped back out of it. The refusals stay quiet while the shell is completing, and every
not-initialised error names the directory, ``sq workflow lint`` included.
"""

import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from squads._cli import app
from squads._cli._common import ChangeDirError, effective_dir

pytestmark = pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="permission bits are not enforced for this user or platform",
)


def _run(args: list[str], cwd: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(sys, "argv", ["sq", *args])
    return CliRunner().invoke(app, args)


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, Path]]:
    project = tmp_path / "project"
    (project / "inside").mkdir(parents=True)
    done = _run(
        ["init", "--default-names", "--backend", "none", "--roles", "minimal"], project, monkeypatch
    )
    assert done.exit_code == 0, done.output
    (project / "afile").write_text("x", encoding="utf-8")
    (project / "closed").mkdir()
    (project / "closed" / "inner").mkdir()
    here = tmp_path / "here"
    here.mkdir()
    (tmp_path / "bare").mkdir()
    yield {"project": project, "here": here, "bare": tmp_path / "bare"}
    (project / "closed").chmod(0o755)
    (project / "inside").chmod(0o755)


#: row -> (-C values relative to the project, text the refusal must contain)
_REFUSED = {
    "a missing hop undone by ..": (["nonexist", "..", "."], "nonexist does not exist"),
    "a missing hop undone by .. inside one value": (["nonexist/.."], "nonexist does not exist"),
    "a file hop undone by ..": (["afile", ".."], "afile is not a directory"),
    "a file hop undone by .. inside one value": (["afile/.."], "afile is not a directory"),
    "a folder without the search bit": (["inside"], "inside cannot be entered: permission denied"),
    "a folder below one without the search bit": (
        ["closed/inner"],
        "closed cannot be entered: permission denied",
    ),
}


@pytest.mark.parametrize("row", _REFUSED)
def test_c_refuses_each_component_chdir_would_refuse(
    row: str, world: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    values, expected = _REFUSED[row]
    project = world["project"]
    (project / "inside").chmod(0o644)
    (project / "closed").chmod(0o000)
    # the first value is relative to the process directory; start the chain at the project
    args = ["-C", str(project), *[a for v in values for a in ("-C", v)], "list"]

    result = _run(args, world["here"], monkeypatch)

    assert result.exit_code == 2, result.output
    assert expected in " ".join(result.output.split())


def test_effective_dir_raises_for_what_it_cannot_enter(
    world: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(world["project"])
    with pytest.raises(ChangeDirError, match="nonexist does not exist"):
        effective_dir(["nonexist", ".."])


def test_c_into_a_folder_that_cd_enters_still_works(
    world: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _run(
        ["-C", str(world["project"] / "inside"), "-C", "..", "list"], world["here"], monkeypatch
    )

    assert result.exit_code == 0, result.output


# --- completion ----------------------------------------------------------------------------


def _complete(words: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    sq = Path(sys.executable).parent / "sq"
    env = {
        **os.environ,
        "_SQ_COMPLETE": "complete_bash",
        "COMP_WORDS": words,
        "COMP_CWORD": str(len(words.split()) - 1),
    }
    return subprocess.run([str(sq)], capture_output=True, text=True, cwd=cwd, env=env, check=False)


@pytest.mark.parametrize(
    "words", ["sq -C /nonexistent li", "sq --dir /x li", "sq -C /etc/passwd li"]
)
def test_completion_does_not_print_the_refusals(words: str, tmp_path: Path) -> None:
    done = _complete(words, tmp_path)

    assert done.stderr == ""
    assert "list" in done.stdout


# --- the not-initialised error names the directory ------------------------------------------


def test_workflow_lint_names_the_c_directory_when_it_is_in_no_squad(
    world: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _run(["-C", str(world["bare"]), "workflow", "lint"], world["here"], monkeypatch)

    assert result.exit_code == 1, result.output
    assert f"no .squads.toml found in {world['bare']} or any parent" in " ".join(
        result.output.split()
    )
