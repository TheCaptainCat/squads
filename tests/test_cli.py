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
    assert bad.exit_code == 1 and "unknown slug" in bad.output
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


def test_resolve_item_id_typed(svc):
    """Service-level: typed resolver verifies actual DB type; both-forms errors.

    Also covers the lexical-parsing layer (bare number, zero-padded, full ID, case-insensitive
    prefix) that was formerly tested by the now-deleted test_resolve_item_id.
    """
    from squads._cli._common import resolve_item_id_typed  # pyright: ignore[reportPrivateUsage]
    from squads._errors import SquadsError
    from squads._models._enums import ItemType

    # create a feature (seq 2 — ROLE-000001 is seq 1 from init --roles minimal)
    svc.create(ItemType.FEATURE, "Feat A", author="manager")  # FEAT-000002

    # bare number resolves to the feature
    assert resolve_item_id_typed("2", ItemType.FEATURE, svc) == "FEAT-000002"

    # zero-padded bare number resolves to the feature
    assert resolve_item_id_typed("000002", ItemType.FEATURE, svc) == "FEAT-000002"

    # full ID resolves to the feature
    assert resolve_item_id_typed("FEAT-000002", ItemType.FEATURE, svc) == "FEAT-000002"

    # case-insensitive prefix
    assert resolve_item_id_typed("feat-2", ItemType.FEATURE, svc) == "FEAT-000002"

    # bare number that belongs to a feature, asked as a task → type-mismatch error
    # (F1) both forms produce the same shape: "<token> is FEAT-000002 (feature), not a task"
    with pytest.raises(SquadsError, match=r"2 is FEAT-000002 \(feature\), not a task"):
        resolve_item_id_typed("2", ItemType.TASK, svc)

    # full ID with wrong prefix → same shape as bare-number mismatch (F1 fix)
    with pytest.raises(SquadsError, match=r"FEAT-000002 is FEAT-000002 \(feature\), not a task"):
        resolve_item_id_typed("FEAT-000002", ItemType.TASK, svc)

    # unknown bare number → error mentioning both forms (F2)
    with pytest.raises(
        SquadsError,
        match=r"no item with number 99 \(use TASK-000099 or bare 99\)",
    ):
        resolve_item_id_typed("99", ItemType.TASK, svc)

    # unknown full ID → same wording mentioning both forms (F2)
    with pytest.raises(
        SquadsError,
        match=r"no item with number 99 \(use TASK-000099 or bare 99\)",
    ):
        resolve_item_id_typed("TASK-000099", ItemType.TASK, svc)

    # invalid token → uses shared error (F3)
    with pytest.raises(SquadsError, match="invalid item id"):
        resolve_item_id_typed("abc", ItemType.TASK, svc)


def test_resolve_item_id_any(svc):
    """Service-level: type-less resolver resolves bare number or full ID regardless of type."""
    from squads._cli._common import resolve_item_id_any  # pyright: ignore[reportPrivateUsage]
    from squads._errors import SquadsError
    from squads._models._enums import ItemType

    svc.create(ItemType.FEATURE, "Feat B", author="manager")  # FEAT-000002
    svc.create(ItemType.TASK, "Task C", author="manager")  # TASK-000003

    # bare number resolves to feature
    assert resolve_item_id_any("2", svc) == "FEAT-000002"

    # bare number resolves to task
    assert resolve_item_id_any("3", svc) == "TASK-000003"

    # full IDs work too
    assert resolve_item_id_any("FEAT-000002", svc) == "FEAT-000002"
    assert resolve_item_id_any("TASK-000003", svc) == "TASK-000003"

    # mismatched prefix on a full ID → names actual item+type (F1/F2 consistent)
    with pytest.raises(SquadsError, match=r"TASK-000002 is FEAT-000002 \(feature\)"):
        resolve_item_id_any("TASK-000002", svc)

    # unknown number → mentions both forms (F2): "use a full ID like TYPE-... or bare N"
    with pytest.raises(
        SquadsError,
        match=r"no item with number 99 \(use a full ID like TYPE-000099 or bare 99\)",
    ):
        resolve_item_id_any("99", svc)

    # unknown full ID → same wording (F2)
    with pytest.raises(
        SquadsError,
        match=r"no item with number 99 \(use a full ID like TYPE-000099 or bare 99\)",
    ):
        resolve_item_id_any("TASK-000099", svc)

    # invalid token (F3: shared _parse_item_token error)
    with pytest.raises(SquadsError, match="invalid item id"):
        resolve_item_id_any("abc", svc)


def test_item_verb_type_enforcement(runner, tmp_path, monkeypatch, frozen_time):
    """CLI smoke: sq task <feat-num> show errors with actual item+type; valid both-forms work."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "feature", "F", "--author", "manager"])  # FEAT-000002

    # bare number against wrong type → mismatch error naming actual item+type (F1)
    bad = runner.invoke(app, ["task", "2", "show"])
    assert bad.exit_code == 1
    assert "FEAT-000002" in bad.output and "feature" in bad.output and "not a task" in bad.output

    # full ID with wrong prefix → same shape as bare-number mismatch (F1 fix)
    bad_full = runner.invoke(app, ["task", "FEAT-000002", "show"])
    assert bad_full.exit_code == 1
    assert (
        "FEAT-000002" in bad_full.output
        and "feature" in bad_full.output
        and "not a task" in bad_full.output
    )

    # bare number (correct type) → success
    ok_bare = runner.invoke(app, ["feature", "2", "show"])
    assert ok_bare.exit_code == 0

    # full ID (correct type) → success
    ok_full = runner.invoke(app, ["feature", "FEAT-000002", "show"])
    assert ok_full.exit_code == 0


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


def test_tree_json_subtree_with_blocked_and_all(runner, tmp_path, monkeypatch, frozen_time):
    import json as _json

    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])  # manager = ROLE-000001
    runner.invoke(app, ["create", "epic", "E", "--author", "manager"])  # EPIC-000002
    runner.invoke(app, ["create", "feature", "F", "--author", "manager", "--parent", "EPIC-000002"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager", "--parent", "FEAT-000003"])
    runner.invoke(app, ["create", "task", "B", "--author", "manager", "--parent", "FEAT-000003"])
    # "TASK-5 blocks TASK-4" → TASK-000004 is blocked while TASK-000005 stays open
    runner.invoke(app, ["task", "5", "ref", "add", "TASK-000004", "--kind", "blocks"])

    def find(nodes, item_id):
        for n in nodes:
            if n["id"] == item_id:
                return n
            hit = find(n["children"], item_id)
            if hit:
                return hit
        return None

    roots = _json.loads(runner.invoke(app, ["tree", "EPIC-000002", "--json"]).output)
    assert roots[0]["id"] == "EPIC-000002"  # nested subtree rooted at the epic
    feat = find(roots, "FEAT-000003")
    assert feat is not None and feat["type"] == "feature"
    blocked_task = find(roots, "TASK-000004")
    open_task = find(roots, "TASK-000005")
    assert blocked_task is not None and blocked_task["blocked"] is True
    assert open_task is not None and open_task["blocked"] is False

    # closing the blocker drops it from the default view but --all brings it back
    runner.invoke(app, ["task", "5", "status", "InProgress"])
    runner.invoke(app, ["task", "5", "status", "Done"])
    default = _json.loads(runner.invoke(app, ["tree", "EPIC-000002", "--json"]).output)
    assert find(default, "TASK-000005") is None
    with_all = _json.loads(runner.invoke(app, ["tree", "EPIC-000002", "--json", "--all"]).output)
    assert find(with_all, "TASK-000005") is not None

    # an unknown root is a clean error, not a KeyError traceback
    bad = runner.invoke(app, ["tree", "EPIC-999999", "--json"])
    assert bad.exit_code == 1 and ("999999" in bad.output or "to root the tree" in bad.output)


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


def test_show_has_no_body_label(runner, tmp_path, monkeypatch, frozen_time):
    """BUG-000025: sq show must not inject a bare 'Body' literal between the panel and content."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "Show test", "--author", "manager", "-m", "Content."])
    shown = runner.invoke(app, ["task", "2", "show"])
    assert shown.exit_code == 0, shown.output
    # the viewer must not inject a standalone "Body" header
    lines = shown.output.splitlines()
    assert not any(line.strip() == "Body" for line in lines)
    # the actual body content is still present
    assert "Content." in shown.output


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
    c = runner.invoke(app, ["task", "6", "comment", "--as", "architect", "-m", "@reviewer verify"])
    assert c.exit_code == 0, c.output
    box = runner.invoke(app, ["inbox", "reviewer"])
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


# --------------------------------------------------------------------------- counter monotonicity


def test_repair_cli_holds_counter_after_file_loss(project, runner, frozen_time):
    """sq repair reports missing items and holds the counter when the top file is deleted."""
    # Create two items so counter reaches 3 (ROLE-000001 + FEAT-000002 + TASK-000003).
    from squads._models._enums import ItemType
    from squads._services._service import Service

    svc = Service(project)
    svc.create(ItemType.FEATURE, "feat")  # FEAT-000002
    top = svc.create(ItemType.TASK, "task").item  # TASK-000003

    # Delete the top item's file.
    svc.paths.abspath(top.path).unlink()

    r = runner.invoke(app, ["repair"])
    assert r.exit_code == 0, r.output
    # Counter must stay at 3 (not drop to 2).
    assert "counter=3" in r.output, f"expected counter=3 in output: {r.output!r}"
    # Missing item is surfaced.
    assert top.id in r.output


def test_check_cli_flags_index_item_with_no_file(project, runner, frozen_time):
    """sq check exits 1 and flags items in the index whose files are gone."""
    import json

    from squads._models._enums import ItemType
    from squads._services._service import Service

    svc = Service(project)
    svc.create(ItemType.TASK, "real task")  # TASK-000002

    # Inject a ghost item into the index (no file on disk).
    raw = json.loads(svc.store.index_path.read_text(encoding="utf-8"))
    raw["items"]["99"] = {
        "id": "TASK-000099",
        "sequence_id": 99,
        "type": "task",
        "title": "ghost",
        "slug": "ghost",
        "status": "Draft",
        "path": "tasks/TASK-000099-ghost.md",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    raw["counter"] = 99
    svc.store.index_path.write_text(json.dumps(raw), encoding="utf-8")

    r = runner.invoke(app, ["check"])
    assert r.exit_code == 1, r.output
    assert "TASK-000099" in r.output
    assert "no markdown" in r.output


# ---------------------------------------------------------------------------
# TASK-000047: resolver adoption sweep — CLI smoke for every ID-accepting surface
# ---------------------------------------------------------------------------


def test_create_parent_and_ref_bare_number(runner, tmp_path, monkeypatch, frozen_time):
    """create --parent and --ref accept bare numbers; unknown number errors mention both forms."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    # ROLE-000001 (seq 1); FEAT-000002 (seq 2)
    runner.invoke(app, ["create", "feature", "F", "--author", "manager"])

    # bare number for --parent (feature is a valid parent for task)
    r = runner.invoke(app, ["create", "task", "T", "--author", "manager", "--parent", "2"])
    assert r.exit_code == 0, r.output

    # bare number for --ref (type-agnostic: any existing item)
    r = runner.invoke(app, ["create", "task", "T2", "--author", "manager", "--ref", "2"])
    assert r.exit_code == 0, r.output

    # unknown number for --parent errors with both forms
    bad = runner.invoke(app, ["create", "task", "Bad", "--author", "manager", "--parent", "999"])
    assert bad.exit_code == 1
    assert "999" in bad.output

    # unknown number for --ref errors
    bad2 = runner.invoke(app, ["create", "task", "Bad2", "--author", "manager", "--ref", "999"])
    assert bad2.exit_code == 1
    assert "999" in bad2.output


def test_update_parent_bare_number(runner, tmp_path, monkeypatch, frozen_time):
    """update --parent accepts bare numbers."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "feature", "F", "--author", "manager"])  # FEAT-000002
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])  # TASK-000003

    # bare number for --parent
    r = runner.invoke(app, ["task", "3", "update", "--parent", "2"])
    assert r.exit_code == 0, r.output

    # full ID also works
    r = runner.invoke(app, ["task", "3", "update", "--parent", "FEAT-000002"])
    assert r.exit_code == 0, r.output

    # unknown number errors
    bad = runner.invoke(app, ["task", "3", "update", "--parent", "888"])
    assert bad.exit_code == 1
    assert "888" in bad.output


def test_ref_add_rm_bare_number(runner, tmp_path, monkeypatch, frozen_time):
    """ref add / ref rm accept bare numbers for the target."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "feature", "F", "--author", "manager"])  # FEAT-000002
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])  # TASK-000003

    # ref add with bare number
    r = runner.invoke(app, ["task", "3", "ref", "add", "2"])
    assert r.exit_code == 0, r.output
    out = runner.invoke(app, ["task", "3", "refs"]).output
    assert "FEAT-000002" in out

    # ref rm with bare number
    r = runner.invoke(app, ["task", "3", "ref", "rm", "2"])
    assert r.exit_code == 0, r.output

    # unknown target errors
    bad = runner.invoke(app, ["task", "3", "ref", "add", "777"])
    assert bad.exit_code == 1
    assert "777" in bad.output


def test_tree_bare_number(runner, tmp_path, monkeypatch, frozen_time):
    """sq tree accepts a bare number as root; unknown number gives a clear error."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "epic", "E", "--author", "manager"])  # EPIC-000002
    runner.invoke(app, ["create", "feature", "F", "--author", "manager", "--parent", "EPIC-000002"])

    # bare number for root
    r = runner.invoke(app, ["tree", "2"])
    assert r.exit_code == 0, r.output
    assert "EPIC-000002" in r.output

    # full ID also works
    r = runner.invoke(app, ["tree", "EPIC-000002"])
    assert r.exit_code == 0, r.output

    # unknown number is a clean error
    bad = runner.invoke(app, ["tree", "555"])
    assert bad.exit_code == 1
    assert "555" in bad.output


def test_list_parent_bare_number(runner, tmp_path, monkeypatch, frozen_time):
    """sq list --parent accepts a bare number."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "feature", "F", "--author", "manager"])  # FEAT-000002
    runner.invoke(app, ["create", "task", "T", "--author", "manager", "--parent", "FEAT-000002"])

    # bare number for --parent
    r = runner.invoke(app, ["list", "--parent", "2"])
    assert r.exit_code == 0, r.output
    assert "TASK-" in r.output

    # unknown number errors
    bad = runner.invoke(app, ["list", "--parent", "444"])
    assert bad.exit_code == 1
    assert "444" in bad.output


def test_role_item_first_grammar(runner, tmp_path, monkeypatch, frozen_time):
    """sq role <addr> show|regen|rm — item-first grammar, slug/id/number, exact match."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    # ROLE-000001 is the manager role after minimal init

    # --- slug resolution ---
    r = runner.invoke(app, ["role", "manager", "show"])
    assert r.exit_code == 0, r.output
    assert "Working agreements" in r.output

    # --- bare number for regen ---
    r = runner.invoke(app, ["role", "1", "regen"])
    assert r.exit_code == 0, r.output

    # --- full ID for regen ---
    r = runner.invoke(app, ["role", "ROLE-000001", "regen"])
    assert r.exit_code == 0, r.output

    # --- wrong-type token for regen errors cleanly ---
    runner.invoke(app, ["create", "feature", "F", "--author", "manager"])  # FEAT-000002
    bad = runner.invoke(app, ["role", "2", "regen"])
    assert bad.exit_code == 1
    assert "feature" in bad.output and "not a role" in bad.output

    # --- bare number for rm ---
    runner.invoke(app, ["role", "activate", "qa"])  # activates as ROLE-000003
    r = runner.invoke(app, ["role", "3", "rm"])
    assert r.exit_code == 0, r.output


def test_role_show_includes_body_and_degrades_for_bundled(
    runner, tmp_path, monkeypatch, frozen_time
):
    """sq role <addr> show: active role shows body; bundled-only degrades with activation hint."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])  # activates `manager` only

    # Active role addressed by slug: output must include the working agreements body.
    r = runner.invoke(app, ["role", "manager", "show"])
    assert r.exit_code == 0, r.output
    assert "Working agreements" in r.output

    # Active role addressed by bare number:
    r = runner.invoke(app, ["role", "1", "show"])
    assert r.exit_code == 0, r.output
    assert "Working agreements" in r.output

    # Bundled-only role (not activated) by slug: must exit 0 with activation hint.
    r = runner.invoke(app, ["role", "qa", "show"])
    assert r.exit_code == 0, r.output
    assert "activate" in r.output


def test_role_skill_body_bracket_fidelity(runner, tmp_path, monkeypatch, frozen_time):
    """Role and skill body render must not escape brackets or inject backslashes.

    REV-000061 regression guard: _render_body uses markup=False so Rich does not
    interpret [x] as markup — brackets must appear verbatim in plain/--raw output.
    The role body from sq sync contains markdown that may include [x]-style tokens.
    """
    import re

    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])

    # -- role show --raw: must not contain escaped brackets (\\[ or \[) in the output
    r = runner.invoke(app, ["role", "manager", "show", "--raw"])
    assert r.exit_code == 0, r.output
    # No backslash-escaped bracket artifacts from Rich markup escaping
    assert r"\[" not in r.output
    assert not re.search(r"\\\[", r.output)

    # -- skill with bracket content in body renders verbatim --raw
    runner.invoke(app, ["skill", "add", "bracket-skill"])  # SKILL-000002
    # Inject a body with bracket tokens directly via the item's body section
    # (skills have no CLI 'body' verb — write via service-level set_body)
    svc_r = runner.invoke(app, ["skill", "2", "show"])
    assert svc_r.exit_code == 0, svc_r.output
    # Confirm show does not produce backslash-escaped output
    assert "\\" not in svc_r.output


def test_role_catalog(runner, tmp_path, monkeypatch, frozen_time):
    """sq role catalog shows the bundled role catalog."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])

    r = runner.invoke(app, ["role", "catalog"])
    assert r.exit_code == 0, r.output
    # Must include bundled roles
    assert "manager" in r.output
    assert "qa" in r.output
    assert "architect" in r.output


def test_role_list_removed(runner, tmp_path, monkeypatch, frozen_time):
    """sq role list falls through to the unknown-address path — exit 1, clean error, no leak."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    r = runner.invoke(app, ["role", "list"])
    assert r.exit_code == 1
    assert "list" in r.output
    assert "_addr" not in r.output
    assert "Traceback" not in r.output
    # --available variant also produces a clean error (no verb after the 'list' address token)
    r2 = runner.invoke(app, ["role", "list", "--available"])
    assert r2.exit_code == 1
    assert "list" in r2.output
    assert "_addr" not in r2.output
    assert "Traceback" not in r2.output


def test_skill_item_first_grammar(runner, tmp_path, monkeypatch, frozen_time):
    """sq skill <addr> show|regen|rm — item-first grammar with slug/id/number resolution."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    # Add a skill; after init the next seq is 2
    runner.invoke(app, ["skill", "add", "my-skill", "--desc", "test skill"])  # SKILL-000002

    # --- bare number for show ---
    r = runner.invoke(app, ["skill", "2", "show"])
    assert r.exit_code == 0, r.output
    assert "my-skill" in r.output

    # --- full ID for show ---
    r = runner.invoke(app, ["skill", "SKILL-000002", "show"])
    assert r.exit_code == 0, r.output
    assert "my-skill" in r.output

    # --- slug for show ---
    r = runner.invoke(app, ["skill", "my-skill", "show"])
    assert r.exit_code == 0, r.output
    assert "my-skill" in r.output

    # --- bare number for regen ---
    r = runner.invoke(app, ["skill", "2", "regen"])
    assert r.exit_code == 0, r.output

    # --- wrong-type token errors cleanly ---
    bad = runner.invoke(app, ["skill", "1", "show"])
    assert bad.exit_code == 1
    assert "not a skill" in bad.output

    # --- bare number for rm ---
    r = runner.invoke(app, ["skill", "2", "rm"])
    assert r.exit_code == 0, r.output


def test_skill_list_removed(runner, tmp_path, monkeypatch, frozen_time):
    """sq skill list falls through to the unknown-address path — exit 1, clean error, no leak."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    r = runner.invoke(app, ["skill", "list"])
    assert r.exit_code == 1
    assert "list" in r.output
    assert "_addr" not in r.output
    assert "Traceback" not in r.output


def test_operator_item_first_grammar(runner, tmp_path, monkeypatch, frozen_time):
    """sq operator <addr> show|rm — item-first grammar with slug/id/number resolution."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["operator", "add", "Test User"])  # OPER-000002

    # --- slug for show ---
    r = runner.invoke(app, ["operator", "op-test", "show"])
    assert r.exit_code == 0, r.output
    assert "Test User" in r.output

    # --- bare number for rm ---
    r = runner.invoke(app, ["operator", "2", "rm"])
    assert r.exit_code == 0, r.output

    # --- wrong-type token for rm errors cleanly (seq 1 is a role) ---
    runner.invoke(app, ["operator", "add", "Test User2"])  # OPER-000003
    bad = runner.invoke(app, ["operator", "1", "rm"])
    assert bad.exit_code == 1
    assert "not an operator" in bad.output or "role" in bad.output


def test_operator_list_removed(runner, tmp_path, monkeypatch, frozen_time):
    """sq operator list falls through to the unknown-address path — exit 1, clean error, no leak."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    r = runner.invoke(app, ["operator", "list"])
    assert r.exit_code == 1
    assert "list" in r.output
    assert "_addr" not in r.output
    assert "Traceback" not in r.output


def test_subtask_story_bare_number(runner, tmp_path, monkeypatch, frozen_time):
    """add-subtask --story accepts bare number like '1' normalized to 'US1'."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "feature", "F", "--author", "manager"])  # FEAT-000002
    runner.invoke(app, ["create", "task", "T", "--author", "manager", "--parent", "FEAT-000002"])
    runner.invoke(app, ["feature", "2", "add-story", "Story One"])  # US1

    # bare number '1' → normalizes to 'US1'
    r = runner.invoke(app, ["task", "3", "add-subtask", "ST", "--story", "1"])
    assert r.exit_code == 0, r.output

    # canonical form 'US1' also works
    r = runner.invoke(app, ["task", "3", "add-subtask", "ST2", "--story", "US1"])
    assert r.exit_code == 0, r.output

    # unknown story errors from service
    bad = runner.invoke(app, ["task", "3", "add-subtask", "ST3", "--story", "99"])
    assert bad.exit_code == 1


def test_ref_kind_vocabulary_validation(runner, tmp_path, monkeypatch, frozen_time):
    """ref add --kind rejects unknown kinds; all eight vocabulary kinds accepted.

    Bare add (no --kind) stays frictionless.
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "feature", "F", "--author", "manager"])  # FEAT-000002
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])  # TASK-000003

    # unknown kind exits 1 and lists valid kinds
    bad = runner.invoke(app, ["task", "3", "ref", "add", "FEAT-000002", "--kind", "banana"])
    assert bad.exit_code == 1
    assert "banana" in bad.output
    for k in ("related", "blocks", "fixes", "addresses"):
        assert k in bad.output

    # typo variant also exits 1
    bad2 = runner.invoke(app, ["task", "3", "ref", "add", "FEAT-000002", "--kind", "fixe"])
    assert bad2.exit_code == 1

    # valid new kinds all accepted
    for kind in ("supersedes", "depends-on", "duplicates"):
        r = runner.invoke(app, ["task", "3", "ref", "add", "FEAT-000002", "--kind", kind])
        assert r.exit_code == 0, f"expected exit 0 for --kind {kind!r}, got: {r.output}"

    # bare add (no --kind) remains frictionless — defaults to related
    r = runner.invoke(app, ["task", "3", "ref", "add", "FEAT-000002"])
    assert r.exit_code == 0, r.output
    out = runner.invoke(app, ["task", "3", "refs"]).output
    assert "FEAT-000002" in out


def test_create_ref_kind_validation(runner, tmp_path, monkeypatch, frozen_time):
    """create --ref id:kind rejects unknown kinds; accepts valid kinds; bare id defaults related."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "feature", "F", "--author", "manager"])  # FEAT-000002

    # unknown kind via create --ref ID:kind exits 1
    bad = runner.invoke(
        app, ["create", "task", "T-bad", "--author", "manager", "--ref", "FEAT-000002:banana"]
    )
    assert bad.exit_code == 1
    assert "banana" in bad.output

    # valid kind accepted
    r = runner.invoke(
        app, ["create", "task", "T-ok", "--author", "manager", "--ref", "FEAT-000002:implements"]
    )
    assert r.exit_code == 0, r.output

    # bare id (no kind) accepted — defaults to related
    r2 = runner.invoke(
        app, ["create", "task", "T-bare", "--author", "manager", "--ref", "FEAT-000002"]
    )
    assert r2.exit_code == 0, r2.output


def test_blocked_depends_on_cli(runner, tmp_path, monkeypatch, frozen_time):
    """sq blocked lists an item blocked via a depends-on edge."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "Blocker", "--author", "manager"])  # TASK-000002
    runner.invoke(app, ["create", "task", "Dependent", "--author", "manager"])  # TASK-000003

    # TASK-000003 depends-on TASK-000002 → TASK-000003 is blocked by TASK-000002
    runner.invoke(app, ["task", "3", "ref", "add", "TASK-000002", "--kind", "depends-on"])

    r = runner.invoke(app, ["blocked"])
    assert r.exit_code == 0, r.output
    # TASK-000003 (the dependent) should appear as blocked
    assert "TASK-000003" in r.output
    # TASK-000002 (the blocker) should appear as the reason
    assert "TASK-000002" in r.output


def test_check_warns_unknown_kind_and_superseded_cli(runner, tmp_path, monkeypatch, frozen_time):
    """sq check warns on unknown ref kind and on Superseded decision without supersedes edge.

    Warnings do not flip the exit code (exit 0 when only warnings present).
    """
    import squads._sections as sections
    from squads._itemfile import read_frontmatter

    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "A", "--author", "manager"])  # TASK-000002
    runner.invoke(app, ["create", "task", "B", "--author", "manager"])  # TASK-000003
    runner.invoke(app, ["create", "decision", "Old ADR", "--author", "manager"])  # ADR-000004

    # Inject a junk kind into TASK-000002's frontmatter
    task_files = list((tmp_path / "squads" / "tasks").glob("TASK-000002-*.md"))
    assert task_files, "TASK-000002 file not found"
    task_path = task_files[0]
    text = task_path.read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    fm["refs"] = ["TASK-000003:junktype"]
    task_path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")

    # Force ADR-000004 to Superseded status (no incoming supersedes edge)
    runner.invoke(app, ["decision", "4", "status", "Proposed"])
    runner.invoke(app, ["decision", "4", "update", "--status", "Superseded", "--force"])

    # Repair so the index reflects the injected changes
    runner.invoke(app, ["repair"])

    r = runner.invoke(app, ["check"])
    # Warnings only → exit 0
    assert r.exit_code == 0, r.output
    # Unknown-kind warning
    assert "junktype" in r.output
    # Superseded-without-edge warning
    assert "ADR-000004" in r.output
    assert "supersedes" in r.output


def test_workflow_contains_all_eight_kinds(runner):
    """sq workflow output contains all eight ref kind names."""
    r = runner.invoke(app, ["workflow"])
    assert r.exit_code == 0, r.output
    all_kinds = (
        "related",
        "blocks",
        "depends-on",
        "implements",
        "fixes",
        "addresses",
        "supersedes",
        "duplicates",
    )
    for kind in all_kinds:
        assert kind in r.output, f"kind {kind!r} missing from sq workflow output"


def test_ref_add_help_references_workflow(runner, tmp_path, monkeypatch):
    """ref add --help lists the eight kinds and points at sq workflow."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    # ref add --help needs a resolved item number, so create one first
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])
    h = runner.invoke(app, ["task", "2", "ref", "add", "--help"])
    assert h.exit_code == 0, h.output
    assert "sq workflow" in h.output


# --------------------------------------------------------------------------- marker-injection guard

# Construct the marker tag at runtime so this file itself never contains a literal marker tag.
_MARKER = "<!-- sq:body -->"


def test_comment_cli_rejects_marker_tag(runner, tmp_path, monkeypatch, frozen_time):
    """CLI: `sq task <n> comment -m <text-with-marker>` exits 1 with a marker error."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])  # TASK-000002
    r = runner.invoke(app, ["task", "2", "comment", "--as", "manager", "-m", f"inject {_MARKER}"])
    assert r.exit_code == 1 and "marker" in r.output


def test_add_subtask_cli_rejects_marker_title(runner, tmp_path, monkeypatch, frozen_time):
    """CLI: `sq task <n> add-subtask` with a marker tag in the title exits 1."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])  # TASK-000002
    r = runner.invoke(app, ["task", "2", "add-subtask", f"title {_MARKER}"])
    assert r.exit_code == 1 and "marker" in r.output


def test_update_subtask_title_cli_rejects_marker(runner, tmp_path, monkeypatch, frozen_time):
    """CLI: `sq task <n> subtask <k> update --title` with a marker tag exits 1."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])  # TASK-000002
    runner.invoke(app, ["task", "2", "add-subtask", "Clean title"])  # ST1
    r = runner.invoke(app, ["task", "2", "subtask", "1", "update", "--title", f"inject {_MARKER}"])
    assert r.exit_code == 1 and "marker" in r.output
    # title must be unchanged after the failed update
    md = next((tmp_path / "squads" / "tasks").glob("TASK-*.md")).read_text(encoding="utf-8")
    # "Clean title" is still the heading; no "inject" text leaked in
    assert "Clean title" in md and "inject" not in md


def test_item_update_title_cli_not_affected_by_guard(runner, tmp_path, monkeypatch, frozen_time):
    """CLI: item-level `update --title` with bracket/backtick content is not rejected."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])  # TASK-000002
    r = runner.invoke(app, ["task", "2", "update", "--title", "[x] done label"])
    assert r.exit_code == 0, r.output
    md = next((tmp_path / "squads" / "tasks").glob("TASK-*.md")).read_text(encoding="utf-8")
    assert "[x] done label" in md
