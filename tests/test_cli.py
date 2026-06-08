import json
import os
import subprocess
import sys

import pytest

from squads._cli import app


@pytest.mark.skipif(sys.platform != "win32", reason="cp1252 console encoding is Windows-specific")
def test_workflow_survives_cp1252_console(tmp_path):
    # On a legacy Windows code page, printing → / • / — must not crash: the CLI forces UTF-8 stdio.
    # (Skipped off Windows, where the CLI deliberately does not reconfigure stdio.)
    result = subprocess.run(
        [sys.executable, "-m", "squads", "workflow"],
        capture_output=True,
        cwd=tmp_path,
        env={**os.environ, "PYTHONIOENCODING": "cp1252"},
    )
    assert result.returncode == 0, result.stderr.decode("cp1252", "replace")


def test_init_and_create_flow(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    r = runner.invoke(app, ["init", "--roles", "minimal"])
    assert r.exit_code == 0, r.output
    assert (tmp_path / ".squads.toml").exists()
    assert (tmp_path / "squads" / ".squads.json").exists()
    assert (tmp_path / ".claude" / "skills" / "squads" / "SKILL.md").exists()

    r = runner.invoke(app, ["create", "task", "Fix login", "--desc", "loops"])
    assert r.exit_code == 0, r.output
    assert "TASK-000002" in r.output
    assert (tmp_path / "squads" / "tasks" / "TASK-000002-fix-login.md").exists()


def test_status_transitions_via_cli(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "t"])
    bad = runner.invoke(app, ["status", "TASK-000002", "Done"])
    assert bad.exit_code == 1
    assert "cannot move" in bad.output
    ok = runner.invoke(app, ["status", "TASK-000002", "InProgress"])
    assert ok.exit_code == 0
    assert "InProgress" in ok.output


def test_list_json(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "feature", "f"])
    r = runner.invoke(app, ["list", "--type", "feature", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data[0]["id"] == "FEAT-000002"


def test_collab_commands_via_cli(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "core"])
    runner.invoke(app, ["create", "feature", "Login"])
    runner.invoke(app, ["create", "task", "Tokens", "--parent", "FEAT-000005"])
    assert (
        runner.invoke(app, ["story", "add", "FEAT-000005", "As an admin, I want X"]).exit_code == 0
    )
    assert runner.invoke(app, ["subtask", "add", "TASK-000006", "expiry"]).exit_code == 0
    c = runner.invoke(app, ["comment", "TASK-000006", "--as", "architect", "-m", "@qa verify"])
    assert c.exit_code == 0, c.output
    box = runner.invoke(app, ["inbox", "qa"])
    assert "TASK-000006" in box.output
    chk = runner.invoke(app, ["check"])
    assert chk.exit_code == 0, chk.output
    assert "no issues" in chk.output


def test_dir_override(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--squad-dir", "alt", "--roles", "minimal"])
    # from an unrelated cwd, target the squad via --dir
    other = tmp_path / "sub"
    other.mkdir()
    monkeypatch.chdir(other)
    r = runner.invoke(app, ["--dir", str(tmp_path / "alt"), "list"])
    assert r.exit_code == 0, r.output
    assert "ROLE-000001" in r.output
