"""``sq migrate up`` exits non-zero, bare, and migrates nothing when an item file cannot be
read, and exits 0 on a clean squad."""

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from _helpers import make_unreadable_by_the_os
from squads._cli import app

_CORPUS_DIR = Path(__file__).parent.parent / "fixtures" / "corpus"
#: The installed `sq` console script, so a bare-exit-code check exercises the real entry point.
_SQ_BIN = Path(sys.executable).parent / "sq"


def test_migrate_up_refuses_bare_when_an_item_file_cannot_be_read(tmp_path: Path) -> None:
    """Checked bare through a real subprocess, never through a pipeline that masks ``$?``: the
    run stops before any migration, names the file with its cause, leaves the schema stamp and
    the item files as they were, and points only at ``sq migrate up``."""
    dst = tmp_path / "v0_11"
    shutil.copytree(_CORPUS_DIR / "v0_11", dst)
    bad_path = dst / "tasks" / "TASK-000003-implement-auth.md"
    undo = make_unreadable_by_the_os(bad_path)
    stamp_before = (dst / ".squads.toml").read_bytes()
    others = {p: p.read_bytes() for p in sorted(dst.rglob("*.md")) if p.is_file()}

    proc = subprocess.run(
        [str(_SQ_BIN), "migrate", "up"],
        cwd=dst,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 1, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    assert bad_path.name in proc.stderr
    assert "could not be read" in proc.stderr
    assert "no migration has run" in proc.stderr
    assert "carried forward" not in proc.stderr
    refusal = proc.stderr
    assert re.findall(r"`sq [^`]*`", refusal) == ["`sq migrate up`"]
    assert (dst / ".squads.toml").read_bytes() == stamp_before
    undo()
    assert {p: p.read_bytes() for p in others} == others


def test_a_clean_migration_prints_no_skip_lines_and_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A clean migration with nothing marker-shaped reports no skip and exits 0."""
    dst = tmp_path / "v0_11"
    shutil.copytree(_CORPUS_DIR / "v0_11", dst)
    monkeypatch.chdir(dst)

    result = CliRunner().invoke(app, ["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert "this region was left untouched" not in result.output


def test_a_clean_migration_exits_zero_bare(tmp_path: Path) -> None:
    """A clean migration exits 0 bare, checked through a real subprocess."""
    dst = tmp_path / "v0_11"
    shutil.copytree(_CORPUS_DIR / "v0_11", dst)

    proc = subprocess.run(
        [str(_SQ_BIN), "migrate", "up"],
        cwd=dst,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"


def test_an_already_current_squad_still_exits_zero(tmp_path: Path) -> None:
    """A squad already at the current schema takes the early return and stays exit 0."""
    dst = tmp_path / "v0_11"
    shutil.copytree(_CORPUS_DIR / "v0_11", dst)
    first = subprocess.run(
        [str(_SQ_BIN), "migrate", "up"],
        cwd=dst,
        capture_output=True,
        text=True,
    )
    assert first.returncode == 0, first.stdout

    second = subprocess.run(
        [str(_SQ_BIN), "migrate", "up"],
        cwd=dst,
        capture_output=True,
        text=True,
    )

    assert second.returncode == 0, second.stdout
    assert "nothing to migrate" in second.stdout
