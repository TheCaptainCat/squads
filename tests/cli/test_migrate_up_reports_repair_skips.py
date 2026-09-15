"""``sq migrate up`` must report the ``skipped`` channel its own trailing repair collects —
the same body-tag-convergence refusal ``sq repair`` already reports at error level — rather
than reading only the strip notice and leaving a refused region unmentioned. And it must exit
non-zero on that same condition, matching ``sq repair``'s own posture for the identical partial
rebuild: ``_cli/_main.py``'s ``repair`` command raises ``typer.Exit(1)`` on
``result.unreadable or result.skipped``, and this command runs that same rebuild as its
trailing step, so a caller gating on ``$?`` must see the same answer from either route.

Before this fix ``_cli/_migrate.py``'s ``up`` command read ``run.repair.strip_notice()`` and
nothing else off the same ``RepairResult``, so a role or system-skill body the convergence
guard declined to overwrite during a migration's trailing sweep was printed nowhere *and* the
command exited 0 — the identical partial-answer condition that fails a plain ``sq repair`` run.
This is the one route a squad behind the current schema takes and the one place an operator
never typed `repair`, so it is where the unreported, wrongly-clean skip was least likely ever
to be noticed.

Driven through the real CLI (``CliRunner`` for output assertions, a real subprocess for the
bare exit code — never through a pipeline, which reports its own status rather than the
command's), on copies of the committed schema-0.11 migration fixture — never the fixture
itself, per the corpus README.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from squads._cli import app
from squads._models import _markers as markers
from squads._sections import replace_section

_CORPUS_DIR = Path(__file__).parent.parent / "fixtures" / "corpus"
#: The installed `sq` console script alongside the current interpreter — the same venv pytest
#: itself is running under, so a bare-exit-code check exercises the real entry point rather
#: than `python -m squads._cli`, which isn't a runnable form (`_cli` is a package with no
#: `__main__`, and `squads._cli:main` is the actual console-script target).
_SQ_BIN = Path(sys.executable).parent / "sq"


def _seed_marker_shaped_skill_body(dst: Path) -> None:
    """Give the bundled ``squads`` system skill's ``sq:body`` region marker-shaped content the
    convergence guard has no model for — left alone by the 0.11→0.14 migration itself (which
    touches no skill body), so it survives untouched until the trailing repair sweep's own
    body-tag classifier reaches it."""
    skill_path = dst / "agents" / "skills" / "SKILL-000008-squads.md"
    text = replace_section(
        skill_path.read_text(encoding="utf-8"),
        markers.BODY,
        f"stray content {markers.open_marker('something-unexpected')}",
    )
    skill_path.write_text(text, encoding="utf-8")


def test_migrate_up_prints_the_skip_and_exits_non_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dst = tmp_path / "v0_11"
    shutil.copytree(_CORPUS_DIR / "v0_11", dst)
    _seed_marker_shaped_skill_body(dst)
    monkeypatch.chdir(dst)

    result = CliRunner().invoke(app, ["migrate", "up"])

    assert "SKILL-8" in result.output, (
        f"the body-tag convergence skip went unreported:\n{result.output}"
    )
    assert "this region was left untouched" in result.output
    assert result.exit_code == 1, (
        f"a skip must exit non-zero, matching sq repair's own posture:\n{result.output}"
    )


def test_migrate_up_exits_non_zero_bare_on_a_skip(tmp_path: Path) -> None:
    """The same case as above, run as a real subprocess and checked bare
    (``proc.returncode``, never through a shell pipeline) — the exact methodology the project
    has been burned by getting wrong before."""
    dst = tmp_path / "v0_11"
    shutil.copytree(_CORPUS_DIR / "v0_11", dst)
    _seed_marker_shaped_skill_body(dst)

    proc = subprocess.run(
        [str(_SQ_BIN), "migrate", "up"],
        cwd=dst,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 1, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    assert "this region was left untouched" in proc.stdout


def test_a_clean_migration_prints_no_skip_lines_and_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Control: the same corpus with nothing marker-shaped reports no skip at all and stays
    exit 0 — the new exit check is conditional on an actual skip/unreadable file, not a general
    regression of a clean migration's own success."""
    dst = tmp_path / "v0_11"
    shutil.copytree(_CORPUS_DIR / "v0_11", dst)
    monkeypatch.chdir(dst)

    result = CliRunner().invoke(app, ["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert "this region was left untouched" not in result.output


def test_a_clean_migration_exits_zero_bare(tmp_path: Path) -> None:
    """The clean-run control, checked bare through a real subprocess — the sibling of the
    skip case above, so a fix that made every exit code 1 (rather than only the partial one)
    would still be caught here."""
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
    """A squad already at the current schema takes the early ``nothing to migrate`` return,
    before ``run.repair`` even exists — the exit check must not reach for an attribute that
    isn't there, and this route must stay exit 0 regardless of the fix above."""
    dst = tmp_path / "v0_11"
    shutil.copytree(_CORPUS_DIR / "v0_11", dst)
    # First run brings it to the current schema; the second is the "nothing to migrate" case.
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
