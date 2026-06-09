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


def test_author_required_and_must_be_registered(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    # missing --author → Typer rejects it
    missing = runner.invoke(app, ["create", "task", "T"])
    assert missing.exit_code != 0 and "author" in missing.output.lower()
    # unregistered author → SquadsError
    ghost = runner.invoke(app, ["create", "task", "T", "--author", "ghost"])
    assert ghost.exit_code == 1 and "not a registered agent" in ghost.output
    # registered author → recorded on the item + frontmatter
    ok = runner.invoke(app, ["create", "task", "T", "--author", "manager"])
    assert ok.exit_code == 0, ok.output
    md = next((tmp_path / "squads" / "tasks").glob("TASK-*.md")).read_text(encoding="utf-8")
    assert "author: manager" in md
    shown = runner.invoke(app, ["task", "2", "show"])
    assert "author" in shown.output and "manager" in shown.output


def test_update_sets_global_and_per_type_metadata(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "review", "R", "--author", "manager"])  # REV-000002
    # global fields: status (validated) + a per-type extra via --set
    out = runner.invoke(
        app, ["review", "2", "update", "--status", "InReview", "--set", "target_ref=TASK-9"]
    )
    assert out.exit_code == 0, out.output
    md = next((tmp_path / "squads" / "reviews").glob("REV-*.md")).read_text(encoding="utf-8")
    assert "status: InReview" in md and "target_ref: TASK-9" in md
    # an unknown / global key via --set is rejected with the valid list
    bad = runner.invoke(app, ["review", "2", "update", "--set", "bogus=x"])
    assert bad.exit_code == 1 and "not a settable field" in bad.output
    flagged = runner.invoke(app, ["review", "2", "update", "--set", "author=manager"])
    assert flagged.exit_code == 1 and "--<flag>" in flagged.output
    # --unset removes it
    runner.invoke(app, ["review", "2", "update", "--unset", "target_ref"])
    md = next((tmp_path / "squads" / "reviews").glob("REV-*.md")).read_text(encoding="utf-8")
    assert "target_ref" not in md


def test_update_author_and_parent(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "feature", "F", "--author", "manager"])  # FEAT-000002
    runner.invoke(app, ["create", "task", "T", "--author", "manager", "--parent", "FEAT-000002"])
    # change author (must be registered) and clear the parent
    assert runner.invoke(app, ["task", "3", "update", "--author", "ghost"]).exit_code == 1
    ok = runner.invoke(app, ["task", "3", "update", "--author", "manager", "--no-parent"])
    assert ok.exit_code == 0, ok.output
    md = next((tmp_path / "squads" / "tasks").glob("TASK-*.md")).read_text(encoding="utf-8")
    assert "author: manager" in md and "parent:" not in md
    # --parent and --no-parent together is rejected
    clash = runner.invoke(app, ["task", "3", "update", "--parent", "FEAT-000002", "--no-parent"])
    assert clash.exit_code == 1 and "not both" in clash.output


def test_subtask_assignee_cli(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["dev", "add", "--tech", "python"])  # registers python-dev (ROLE-000002)
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])  # TASK-000003
    add = runner.invoke(app, ["task", "3", "add-subtask", "Wire API", "--assignee", "python-dev"])
    assert add.exit_code == 0, add.output
    listed = runner.invoke(app, ["task", "3", "subtasks"])
    assert "Assignee" in listed.output and "python-dev" in listed.output
    # reassign via `update --assignee`; an unregistered slug is rejected
    up = runner.invoke(app, ["task", "3", "subtask", "1", "update", "--assignee", "manager"])
    assert up.exit_code == 0, up.output
    bad = runner.invoke(app, ["task", "3", "subtask", "1", "update", "--assignee", "ghost"])
    assert bad.exit_code == 1 and "not a registered agent" in bad.output
    # --clear-assignee unassigns; with --assignee together it's rejected
    assert (
        runner.invoke(app, ["task", "3", "subtask", "1", "update", "--clear-assignee"]).exit_code
        == 0
    )
    md = next((tmp_path / "squads" / "tasks").glob("TASK-*.md")).read_text(encoding="utf-8")
    assert "assignee:" not in md
    clash = runner.invoke(
        app, ["task", "3", "subtask", "1", "update", "--assignee", "manager", "--clear-assignee"]
    )
    assert clash.exit_code == 1 and "not both" in clash.output


def test_subtask_update_cli(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "feature", "F", "--author", "manager"])  # FEAT-000002
    runner.invoke(app, ["feature", "2", "add-story", "Reset"])  # US1
    runner.invoke(app, ["create", "task", "T", "--author", "manager", "--parent", "FEAT-000002"])
    runner.invoke(app, ["task", "3", "add-subtask", "Old name", "--story", "US1"])
    ok = runner.invoke(app, ["task", "3", "subtask", "1", "update", "--title", "New name"])
    assert ok.exit_code == 0, ok.output
    md = next((tmp_path / "squads" / "tasks").glob("TASK-*.md")).read_text(encoding="utf-8")
    assert "title: New name" in md and "### ST1 — New name" in md and "Old name" not in md
    # clear the story mapping
    runner.invoke(app, ["task", "3", "subtask", "1", "update", "--no-story"])
    assert "story:" not in next((tmp_path / "squads" / "tasks").glob("TASK-*.md")).read_text(
        "utf-8"
    )
    # no fields → friendly error; contradictory story flags → error
    empty = runner.invoke(app, ["task", "3", "subtask", "1", "update"])
    assert empty.exit_code == 1 and "at least one field" in empty.output
    clash = runner.invoke(
        app, ["task", "3", "subtask", "1", "update", "--story", "US1", "--no-story"]
    )
    assert clash.exit_code == 1 and "not both" in clash.output


def test_finding_update_severity_cli(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "review", "R", "--author", "manager"])  # REV-000002
    runner.invoke(app, ["review", "2", "add-finding", "Null deref", "--severity", "low"])
    ok = runner.invoke(app, ["review", "2", "finding", "1", "update", "--severity", "critical"])
    assert ok.exit_code == 0, ok.output
    md = next((tmp_path / "squads" / "reviews").glob("REV-*.md")).read_text(encoding="utf-8")
    assert "severity: critical" in md and "🔴 Critical" in md


def test_bug_severity_cli(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "bug", "Crash on logout", "--author", "manager"])  # BUG-000002
    # severity is a validated per-type field, set via `update --set`
    ok = runner.invoke(app, ["bug", "2", "update", "--set", "severity=high"])
    assert ok.exit_code == 0, ok.output
    md = next((tmp_path / "squads" / "bugs").glob("BUG-*.md")).read_text(encoding="utf-8")
    assert "severity: high" in md
    # `show` renders the badge
    shown = runner.invoke(app, ["bug", "2", "show"])
    assert "severity" in shown.output and "🟠" in shown.output
    # an invalid value is rejected with the choices
    bad = runner.invoke(app, ["bug", "2", "update", "--set", "severity=urgent"])
    assert bad.exit_code == 1 and "invalid severity" in bad.output


def test_item_body_cli(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    # body set at create time via -m, plus a separate --desc summary
    runner.invoke(
        app,
        ["create", "task", "Auth", "--author", "manager", "--desc", "Token check", "-m", "First."],
    )
    md = next((tmp_path / "squads" / "tasks").glob("TASK-*.md")).read_text(encoding="utf-8")
    assert "First." in md and "description: Token check" in md
    # `task <n> body` replaces; `show` reads it back
    r = runner.invoke(app, ["task", "2", "body", "-m", "## Description", "-m", "Rewritten."])
    assert r.exit_code == 0, r.output
    shown = runner.invoke(app, ["task", "2", "show"])
    assert "Rewritten." in shown.output and "Token check" in shown.output
    # --file - reads stdin; --append keeps prior body
    runner.invoke(app, ["task", "2", "body", "--file", "-"], input="From stdin.")
    runner.invoke(app, ["task", "2", "body", "-m", "Added.", "--append"])
    body_out = runner.invoke(app, ["task", "2", "show"]).output
    assert "From stdin." in body_out and "Added." in body_out


def test_subtask_body_cli(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])  # TASK-000002
    runner.invoke(app, ["task", "2", "add-subtask", "Validate"])  # ST1
    # -m sets the body; show reads it back
    r = runner.invoke(app, ["task", "2", "subtask", "1", "body", "-m", "First.", "-m", "Second."])
    assert r.exit_code == 0, r.output
    shown = runner.invoke(app, ["task", "2", "subtask", "1", "show"])
    assert "First." in shown.output and "Second." in shown.output
    # --file replaces, --file - reads stdin
    bf = tmp_path / "body.md"
    bf.write_text("From a file.", encoding="utf-8")
    assert (
        runner.invoke(app, ["task", "2", "subtask", "1", "body", "--file", str(bf)]).exit_code == 0
    )
    piped = runner.invoke(app, ["task", "2", "subtask", "1", "body", "--file", "-"], input="Piped.")
    assert piped.exit_code == 0
    # --append keeps the prior body
    runner.invoke(app, ["task", "2", "subtask", "1", "body", "-m", "More.", "--append"])
    out = runner.invoke(app, ["task", "2", "subtask", "1", "show"]).output
    assert "Piped." in out and "More." in out
    # -m together with --file is rejected
    clash = runner.invoke(app, ["task", "2", "subtask", "1", "body", "-m", "x", "--file", str(bf)])
    assert clash.exit_code == 1 and "not both" in clash.output
    # body can be set at add time via --file
    bf2 = tmp_path / "b2.md"
    bf2.write_text("Born with a body.", encoding="utf-8")
    runner.invoke(app, ["task", "2", "add-subtask", "Second", "--file", str(bf2)])  # ST2
    assert "Born with a body." in runner.invoke(app, ["task", "2", "subtask", "2", "show"]).output


def test_resolve_item_id():
    from squads._cli._common import resolve_item_id  # pyright: ignore[reportPrivateUsage]
    from squads._errors import SquadsError
    from squads._models._enums import ItemType

    assert resolve_item_id("35", ItemType.TASK) == "TASK-000035"
    assert resolve_item_id("000035", ItemType.TASK) == "TASK-000035"
    assert resolve_item_id("TASK-000035", ItemType.TASK) == "TASK-000035"
    assert resolve_item_id("task-35", ItemType.TASK) == "TASK-000035"  # case-insensitive prefix
    with pytest.raises(SquadsError, match="not a task"):
        resolve_item_id("REV-000002", ItemType.TASK)
    with pytest.raises(SquadsError, match="invalid task id"):
        resolve_item_id("abc", ItemType.TASK)


def test_item_grammar_refs_and_finding(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "feature", "F", "--author", "manager"])  # FEAT-000002
    runner.invoke(app, ["create", "review", "R", "--author", "manager"])  # REV-000003
    # findings: add → list (severity badge) → transition
    assert (
        runner.invoke(
            app, ["review", "3", "add-finding", "Null deref", "--severity", "high"]
        ).exit_code
        == 0
    )
    assert "🟠 high" in runner.invoke(app, ["review", "3", "findings"]).output
    assert (
        runner.invoke(app, ["review", "3", "finding", "1", "update", "--status", "Fixed"]).exit_code
        == 0
    )
    # refs: feature 2 → review 3, listed both directions
    assert (
        runner.invoke(
            app, ["feature", "2", "ref", "add", "REV-000003", "--kind", "blocks"]
        ).exit_code
        == 0
    )
    out = runner.invoke(app, ["feature", "2", "refs", "--all"]).output
    assert "REV-000003" in out and "blocks" in out
    # a type-mismatched full id is a clean error, not a traceback
    bad = runner.invoke(app, ["task", "ROLE-000001", "show"])
    assert bad.exit_code == 1 and "not a task" in bad.output


def test_hoist_global_options():
    from squads._cli import _hoist_global_options as h  # pyright: ignore[reportPrivateUsage]

    # already-leading globals are untouched
    assert h(["--at", "2024-01-01", "create", "task", "X"]) == [
        "--at",
        "2024-01-01",
        "create",
        "task",
        "X",
    ]
    # trailing --at / --dir (and =value form) are pulled to the front
    assert h(["create", "task", "X", "--at", "2024-01-01"]) == [
        "--at",
        "2024-01-01",
        "create",
        "task",
        "X",
    ]
    assert h(["list", "--dir=/s", "--at=2024-01-01"]) == ["--dir=/s", "--at=2024-01-01", "list"]
    # a dangling --at (no value) is left for Click to report
    assert h(["create", "task", "X", "--at"]) == ["create", "task", "X", "--at"]
    # nothing to hoist → unchanged
    assert h(["create", "task", "X"]) == ["create", "task", "X"]


def test_at_after_subcommand_works(tmp_path, monkeypatch):
    # the entry-point hoist makes `--at` work after the subcommand (real path: python -m squads)
    monkeypatch.chdir(tmp_path)
    run = lambda *a: subprocess.run(  # noqa: E731
        [sys.executable, "-m", "squads", *a], capture_output=True, text=True, cwd=tmp_path
    )
    assert run("init", "--roles", "minimal").returncode == 0
    r = run("create", "task", "Old work", "--author", "manager", "--at", "2020-05-06")
    assert r.returncode == 0, r.stderr
    md = next((tmp_path / "squads" / "tasks").glob("TASK-*.md")).read_text(encoding="utf-8")
    assert "created_at: '2020-05-06T00:00:00Z'" in md


def test_migrate_up_noop_when_current(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    r = runner.invoke(app, ["migrate", "up"])
    assert r.exit_code == 0, r.output
    assert "already at schema v0.3" in r.output


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
    assert "manual steps" in c.output and "add-finding" in c.output
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
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])  # TASK-000002
    runner.invoke(app, ["create", "guide", "G", "--author", "manager"])  # GUIDE-000003

    # forge the pre-0.2 on-disk shape: schema 0.1 in config + bare ref + a ref_kinds map
    cfg = tmp_path / ".squads.toml"
    cfg.write_text(
        cfg.read_text(encoding="utf-8").replace('schema_version = "0.3"', 'schema_version = "0.1"'),
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
    assert "sq migrate up" in " ".join(blocked.output.split())  # tolerate Rich line-wrapping

    # migrate is exempt from the gate and upgrades the squad
    done = runner.invoke(app, ["migrate", "up"])
    assert done.exit_code == 0, done.output
    assert "migrated" in done.output and "v0.3" in done.output

    # config bumped, file folded inline, gate now passes
    assert 'schema_version = "0.3"' in cfg.read_text(encoding="utf-8")
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

    r = runner.invoke(
        app, ["create", "task", "Fix login", "--author", "manager", "--desc", "loops"]
    )
    assert r.exit_code == 0, r.output
    assert "TASK-000002" in r.output
    assert (tmp_path / "squads" / "tasks" / "TASK-000002-fix-login.md").exists()


def test_status_transitions_via_cli(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "t", "--author", "manager"])
    bad = runner.invoke(app, ["task", "2", "status", "Done"])
    assert bad.exit_code == 1
    assert "cannot move" in bad.output
    ok = runner.invoke(app, ["task", "2", "status", "InProgress"])
    assert ok.exit_code == 0
    assert "InProgress" in ok.output


def test_list_json(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "feature", "f", "--author", "manager"])
    r = runner.invoke(app, ["list", "--type", "feature", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data[0]["id"] == "FEAT-000002"


def test_collab_commands_via_cli(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "core"])
    runner.invoke(app, ["create", "feature", "Login", "--author", "manager"])
    runner.invoke(
        app, ["create", "task", "Tokens", "--author", "manager", "--parent", "FEAT-000005"]
    )
    assert runner.invoke(app, ["feature", "5", "add-story", "As an admin, I want X"]).exit_code == 0
    assert runner.invoke(app, ["task", "6", "add-subtask", "expiry"]).exit_code == 0
    c = runner.invoke(app, ["task", "6", "comment", "--as", "architect", "-m", "@qa verify"])
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
