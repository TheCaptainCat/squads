"""Small CLI plumbing facts with no other home: `--dir` targets a squad from an unrelated cwd,
`ref add --help` points an agent at `sq workflow`, and the CLI survives a legacy cp1252 console
encoding (the reason it forces UTF-8 stdio) — a Windows-only fact, always skipped elsewhere.
"""

import os
import subprocess
import sys

import pytest

from squads._cli import app


def test_dir_override_targets_a_squad_from_an_unrelated_cwd(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--squad-dir", "alt", "--roles", "minimal"])

    other = tmp_path / "sub"
    other.mkdir()
    monkeypatch.chdir(other)

    result = runner.invoke(app, ["--dir", str(tmp_path / "alt"), "list"])
    assert result.exit_code == 0, result.output
    assert "ROLE-1" in result.output


def test_ref_add_help_mentions_the_workflow_command(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])

    result = runner.invoke(app, ["task", "2", "ref", "add", "--help"])
    assert result.exit_code == 0, result.output
    assert "sq workflow" in result.output


@pytest.mark.skipif(sys.platform != "win32", reason="cp1252 console encoding is Windows-specific")
def test_workflow_survives_a_cp1252_console(tmp_path):
    # On a legacy Windows code page, printing arrows/bullets must not crash: the CLI forces
    # UTF-8 stdio. (Skipped off Windows, where the CLI deliberately does not reconfigure stdio.)
    result = subprocess.run(
        [sys.executable, "-m", "squads", "workflow"],
        capture_output=True,
        cwd=tmp_path,
        env={**os.environ, "PYTHONIOENCODING": "cp1252"},
    )
    assert result.returncode == 0, result.stderr.decode("cp1252", "replace")
