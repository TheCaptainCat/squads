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


def test_docs_lists_and_prints(runner):
    # `sq docs` needs no squad: it reads bundled docs, not project state.
    r = runner.invoke(app, ["docs"])
    assert r.exit_code == 0, r.output
    assert "internals" in r.output and "workflow" in r.output

    r = runner.invoke(app, ["docs", "internals"])
    assert r.exit_code == 0, r.output
    assert "# squads internals" in r.output  # raw markdown, heading verbatim

    r = runner.invoke(app, ["docs", "internals", "--rich"])
    assert r.exit_code == 0, r.output

    r = runner.invoke(app, ["docs", "nope"])
    assert r.exit_code == 1
    assert "unknown doc" in r.output


def test_migrate_up_noop_when_current(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    r = runner.invoke(app, ["migrate", "up"])
    assert r.exit_code == 0, r.output
    assert "already at schema v2" in r.output


def test_migrate_help_and_chlog(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    # help: the changelog index lists the shipped migration(s)
    h = runner.invoke(app, ["migrate", "help"])
    assert h.exit_code == 0, h.output
    assert "0.2.0" in h.output and "changelog" in h.output
    # chlog: a range that includes 0.2.0 prints its manual steps
    c = runner.invoke(app, ["migrate", "chlog", "v0.1.1..v0.2.0"])
    assert c.exit_code == 0, c.output
    assert "manual steps" in c.output and "sq finding add" in c.output
    # a range that excludes 0.2.0 has none
    none = runner.invoke(app, ["migrate", "chlog", "v0.2.0..v0.2.0"])
    assert none.exit_code == 0 and "no manual steps" in none.output
    # a malformed range errors cleanly
    bad = runner.invoke(app, ["migrate", "chlog", "0.2.0"])
    assert bad.exit_code == 1 and "range" in bad.output


def test_schema_gate_blocks_until_migrate(runner, tmp_path, monkeypatch, frozen_time):
    from squads import _sections as sections

    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T"])  # TASK-000002
    runner.invoke(app, ["create", "guide", "G"])  # GUIDE-000003

    # forge the pre-2 on-disk shape: schema 1 in config + bare ref + a ref_kinds map
    cfg = tmp_path / ".squads.toml"
    cfg.write_text(
        cfg.read_text(encoding="utf-8").replace("schema_version = 2", "schema_version = 1"),
        encoding="utf-8",
    )
    task_md = next((tmp_path / "squads" / "tasks").glob("TASK-000002-*.md"))
    fm, _ = sections.split_frontmatter(task_md.read_text(encoding="utf-8"))
    fm["refs"] = ["GUIDE-000003"]
    fm["extra"] = {"ref_kinds": {"GUIDE-000003": "implements"}}
    task_md.write_text(
        sections.replace_frontmatter(task_md.read_text(encoding="utf-8"), fm), encoding="utf-8"
    )

    # gate: an ordinary command refuses and points at `sq migrate up`
    blocked = runner.invoke(app, ["list"])
    assert blocked.exit_code == 1
    assert "sq migrate up" in blocked.output

    # migrate is exempt from the gate and upgrades the squad
    done = runner.invoke(app, ["migrate", "up"])
    assert done.exit_code == 0, done.output
    assert "migrated" in done.output and "v2" in done.output

    # config bumped, file folded inline, gate now passes
    assert "schema_version = 2" in cfg.read_text(encoding="utf-8")
    text = task_md.read_text(encoding="utf-8")
    assert "GUIDE-000003:implements" in text and "ref_kinds" not in text
    assert runner.invoke(app, ["list"]).exit_code == 0


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
