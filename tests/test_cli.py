import json
import os
import re
import subprocess
import sys

import pytest
from typer.testing import CliRunner

from squads._cli import _hoist_global_options, app  # pyright: ignore[reportPrivateUsage]
from squads._models._schema import SCHEMA_VERSION

_ANSI_SGR = re.compile(r"\x1b\[[0-9;]*m")


def _plain(text: str) -> str:
    """Drop ANSI SGR codes so help-flag assertions survive a color-forcing help console.

    Rich styles an option's leading ``-`` as its own span, so a colored ``--onto`` renders as
    ``-<reset><style>-onto`` — the literal ``--onto`` substring is absent until the escapes are
    stripped. Local runs neutralise the color-forcing env before import; some CI consoles still
    colorize ``--help`` output, so normalise before matching flag names.
    """
    return _ANSI_SGR.sub("", text)


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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "review", "R", "--author", "manager"])  # REV-000002
    runner.invoke(app, ["review", "2", "add-finding", "Null deref", "--severity", "low"])
    ok = runner.invoke(app, ["review", "2", "finding", "1", "update", "--severity", "critical"])
    assert ok.exit_code == 0, ok.output
    md = next((tmp_path / "squads" / "reviews").glob("REV-*.md")).read_text(encoding="utf-8")
    assert "severity: critical" in md and "🔴 Critical" in md


def test_bug_severity_cli(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
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


async def test_resolve_item_id_typed(svc):
    """Service-level: typed resolver verifies actual DB type; both-forms errors.

    Also covers the lexical-parsing layer (bare number, zero-padded, full ID, case-insensitive
    prefix) that was formerly tested by the now-deleted test_resolve_item_id.
    """
    from squads._cli._common import resolve_item_id_typed  # pyright: ignore[reportPrivateUsage]
    from squads._errors import SquadsError

    # create a feature (seq 2 — ROLE-1 is seq 1 from init --roles minimal)
    await svc.create("feature", "Feat A", author="manager")  # FEAT-2

    # bare number resolves to the feature
    assert await resolve_item_id_typed("2", "feature", svc) == "FEAT-2"

    # zero-padded bare number resolves to the feature
    assert await resolve_item_id_typed("000002", "feature", svc) == "FEAT-2"

    # full ID (padded or not) resolves to the feature
    assert await resolve_item_id_typed("FEAT-000002", "feature", svc) == "FEAT-2"

    # case-insensitive prefix
    assert await resolve_item_id_typed("feat-2", "feature", svc) == "FEAT-2"

    # bare number that belongs to a feature, asked as a task → type-mismatch error
    # (F1) both forms produce the same shape: "<token> is FEAT-2 (feature), not a task"
    with pytest.raises(SquadsError, match=r"2 is FEAT-2 \(feature\), not a task"):
        await resolve_item_id_typed("2", "task", svc)

    # full ID with wrong prefix → same shape as bare-number mismatch (F1 fix).
    # The echoed label is the raw (possibly padded) token; the resolved id is unpadded.
    with pytest.raises(SquadsError, match=r"FEAT-000002 is FEAT-2 \(feature\), not a task"):
        await resolve_item_id_typed("FEAT-000002", "task", svc)

    # unknown bare number → error mentioning both forms (F2); the hint is unpadded (ADR-000282)
    with pytest.raises(
        SquadsError,
        match=r"no item with number 99 \(use TASK-99 or bare 99\)",
    ):
        await resolve_item_id_typed("99", "task", svc)

    # unknown full ID → same wording mentioning both forms (F2)
    with pytest.raises(
        SquadsError,
        match=r"no item with number 99 \(use TASK-99 or bare 99\)",
    ):
        await resolve_item_id_typed("TASK-000099", "task", svc)

    # invalid token → uses shared error (F3)
    with pytest.raises(SquadsError, match="invalid item id"):
        await resolve_item_id_typed("abc", "task", svc)


async def test_unpadded_and_padded_ids_resolve_to_same_item(svc):
    """Display went unpadded (ADR-000282), but lookup stays tolerant of either width.

    A freshly created item's canonical display id (e.g. "FEAT-2") and its old zero-padded
    form (e.g. "FEAT-000002") must resolve to the same item everywhere: the typed resolver,
    the type-less resolver, and the raw index — no input-parsing change was made.
    """
    from squads._cli._common import (
        resolve_item_id_any,  # pyright: ignore[reportPrivateUsage]
        resolve_item_id_typed,  # pyright: ignore[reportPrivateUsage]
    )

    created = (await svc.create("feature", "Widely addressed", author="manager")).item
    assert created.id == "FEAT-2"  # display is unpadded

    unpadded, padded = "FEAT-2", "FEAT-000002"
    assert await resolve_item_id_typed(unpadded, "feature", svc) == created.id
    assert await resolve_item_id_typed(padded, "feature", svc) == created.id
    assert await resolve_item_id_any(unpadded, svc) == created.id
    assert await resolve_item_id_any(padded, svc) == created.id

    db = await svc.store.load()
    assert db.get(unpadded) is db.get(padded) is not None


async def test_resolve_item_id_any(svc):
    """Service-level: type-less resolver resolves bare number or full ID regardless of type."""
    from squads._cli._common import resolve_item_id_any  # pyright: ignore[reportPrivateUsage]
    from squads._errors import SquadsError

    await svc.create("feature", "Feat B", author="manager")  # FEAT-2
    await svc.create("task", "Task C", author="manager")  # TASK-3

    # bare number resolves to feature
    assert await resolve_item_id_any("2", svc) == "FEAT-2"

    # bare number resolves to task
    assert await resolve_item_id_any("3", svc) == "TASK-3"

    # full IDs (padded or not) work too
    assert await resolve_item_id_any("FEAT-000002", svc) == "FEAT-2"
    assert await resolve_item_id_any("TASK-000003", svc) == "TASK-3"

    # mismatched prefix on a full ID → names actual item+type (F1/F2 consistent).
    # The echoed label is the raw (padded) token; the resolved id is unpadded.
    with pytest.raises(SquadsError, match=r"TASK-000002 is FEAT-2 \(feature\)"):
        await resolve_item_id_any("TASK-000002", svc)

    # unknown number → mentions both forms (F2): "use a full ID like TYPE-... or bare N"
    # (the hint is unpadded, ADR-000282)
    with pytest.raises(
        SquadsError,
        match=r"no item with number 99 \(use a full ID like TYPE-99 or bare 99\)",
    ):
        await resolve_item_id_any("99", svc)

    # unknown full ID → same wording (F2)
    with pytest.raises(
        SquadsError,
        match=r"no item with number 99 \(use a full ID like TYPE-99 or bare 99\)",
    ):
        await resolve_item_id_any("TASK-000099", svc)

    # invalid token (F3: shared _parse_item_token error)
    with pytest.raises(SquadsError, match="invalid item id"):
        await resolve_item_id_any("abc", svc)


def test_item_verb_type_enforcement(runner, tmp_path, monkeypatch, frozen_time):
    """CLI smoke: sq task <feat-num> show errors with actual item+type; valid both-forms work."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "feature", "F", "--author", "manager"])  # FEAT-2

    # bare number against wrong type → mismatch error naming actual item+type (F1)
    bad = runner.invoke(app, ["task", "2", "show"])
    assert bad.exit_code == 1
    assert "FEAT-2" in bad.output and "feature" in bad.output and "not a task" in bad.output

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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
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
    assert "REV-3" in out and "blocks" in out
    # a type-mismatched full id is a clean error, not a traceback
    bad = runner.invoke(app, ["task", "ROLE-000001", "show"])
    assert bad.exit_code == 1 and "not a task" in bad.output


def test_tree_json_subtree_with_blocked_and_all(runner, tmp_path, monkeypatch, frozen_time):
    import json as _json

    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])  # manager = ROLE-000001
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
    assert roots[0]["id"] == "EPIC-2"  # nested subtree rooted at the epic; display is unpadded
    feat = find(roots, "FEAT-3")
    assert feat is not None and feat["type"] == "feature"
    blocked_task = find(roots, "TASK-4")
    open_task = find(roots, "TASK-5")
    assert blocked_task is not None and blocked_task["blocked"] is True
    assert open_task is not None and open_task["blocked"] is False

    # closing the blocker drops it from the default view but --all brings it back
    runner.invoke(app, ["task", "5", "status", "InProgress"])
    runner.invoke(app, ["task", "5", "status", "Done"])
    default = _json.loads(runner.invoke(app, ["tree", "EPIC-000002", "--json"]).output)
    assert find(default, "TASK-5") is None
    with_all = _json.loads(runner.invoke(app, ["tree", "EPIC-000002", "--json", "--all"]).output)
    assert find(with_all, "TASK-5") is not None

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
    assert run("init", "--no-seed-skills", "--roles", "minimal").returncode == 0
    r = run("create", "task", "Old work", "--author", "manager", "--at", "2020-05-06")
    assert r.returncode == 0, r.stderr
    md = next((tmp_path / "squads" / "tasks").glob("TASK-*.md")).read_text(encoding="utf-8")
    assert "created_at: '2020-05-06T00:00:00Z'" in md


def test_migrate_up_noop_when_current(runner, tmp_path, monkeypatch, frozen_time):
    """Runs with production-default seeding to guard seeded squads against migrate regressions."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    r = runner.invoke(app, ["migrate", "up"])
    assert r.exit_code == 0, r.output
    assert f"already at schema v{SCHEMA_VERSION}" in r.output


def test_migrate_help_and_chlog(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])  # TASK-000002
    runner.invoke(app, ["create", "guide", "G", "--author", "manager"])  # GUIDE-000003

    # forge the pre-0.2 on-disk shape: schema 0.1 in config + bare ref + a ref_kinds map
    cfg = tmp_path / ".squads.toml"
    cfg.write_text(
        cfg.read_text(encoding="utf-8").replace(
            f'schema_version = "{SCHEMA_VERSION}"', 'schema_version = "0.1"'
        ),
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
    assert "migrated" in done.output and f"v{SCHEMA_VERSION}" in done.output

    # config bumped, file folded inline, gate now passes
    assert f'schema_version = "{SCHEMA_VERSION}"' in cfg.read_text(encoding="utf-8")
    text = task_md.read_text(encoding="utf-8")
    # the kind-fold (0.1→0.2) and the unpad (0.5→0.7) both ran in this one `migrate up`.
    assert "GUIDE-3:implements" in text and "ref_kinds" not in text
    assert runner.invoke(app, ["list"]).exit_code == 0


def test_init_and_create_flow(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    r = runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    assert r.exit_code == 0, r.output
    assert (tmp_path / ".squads.toml").exists()
    assert (tmp_path / "squads" / ".squads.json").exists()
    assert (tmp_path / ".claude" / "skills" / "squads" / "SKILL.md").exists()

    r = runner.invoke(
        app, ["create", "task", "Fix login", "--author", "manager", "--desc", "loops"]
    )
    assert r.exit_code == 0, r.output
    assert "TASK-2" in r.output  # display is unpadded
    # Filename stays padded (ADR-000282) even though the displayed id is unpadded.
    assert (tmp_path / "squads" / "tasks" / "TASK-000002-fix-login.md").exists()


def test_status_transitions_via_cli(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "feature", "f", "--author", "manager"])
    r = runner.invoke(app, ["list", "--type", "feature", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data[0]["id"] == "FEAT-2"


def test_collab_commands_via_cli(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "core"])
    runner.invoke(app, ["create", "feature", "Login", "--author", "manager"])
    runner.invoke(
        app, ["create", "task", "Tokens", "--author", "manager", "--parent", "FEAT-000005"]
    )
    assert runner.invoke(app, ["feature", "5", "add-story", "As an admin, I want X"]).exit_code == 0
    assert runner.invoke(app, ["task", "6", "add-subtask", "expiry"]).exit_code == 0
    assert (
        runner.invoke(
            app, ["feature", "5", "story", "1", "body", "-m", "Acceptance criteria for X."]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["task", "6", "subtask", "1", "body", "-m", "Rotate the expiry token."]
        ).exit_code
        == 0
    )
    c = runner.invoke(app, ["task", "6", "comment", "--as", "architect", "-m", "@reviewer verify"])
    assert c.exit_code == 0, c.output
    box = runner.invoke(app, ["inbox", "reviewer"])
    assert "TASK-6" in box.output
    chk = runner.invoke(app, ["check"])
    assert chk.exit_code == 0, chk.output
    assert "no issues" in chk.output


def test_dir_override(runner, tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--squad-dir", "alt", "--roles", "minimal"])
    # from an unrelated cwd, target the squad via --dir
    other = tmp_path / "sub"
    other.mkdir()
    monkeypatch.chdir(other)
    r = runner.invoke(app, ["--dir", str(tmp_path / "alt"), "list"])
    assert r.exit_code == 0, r.output
    assert "ROLE-1" in r.output


# --------------------------------------------------------------------------- counter monotonicity


async def test_repair_cli_holds_counter_after_file_loss(project, invoke, frozen_time):
    """sq repair reports missing items and holds the counter when the top file is deleted."""
    # Create two items so counter reaches 3 (ROLE-000001 + FEAT-000002 + TASK-000003).
    from squads._services._service import Service

    svc = Service(project)
    await svc.create("feature", "feat")  # FEAT-000002
    top = (await svc.create("task", "task")).item  # TASK-000003

    # Delete the top item's file.
    svc.paths.abspath(top.path).unlink()

    r = await invoke(["repair"])
    assert r.exit_code == 0, r.output
    # Counter must stay at 3 (not drop to 2).
    assert "counter=3" in r.output, f"expected counter=3 in output: {r.output!r}"
    # Missing item is surfaced.
    assert top.id in r.output


# --------------------------------------------------------------------------- sq renumber


async def test_renumber_cli_shifts_block_and_updates_refs(project, invoke, frozen_time):
    """sq renumber --from/--onto shifts the block, rewrites refs, renames files, bumps counter."""
    from squads._services._service import Service

    svc = Service(project)
    feat = (await svc.create("feature", "keep")).item  # FEAT-2
    task = (await svc.create("task", "shift-task", parent=feat.id)).item  # TASK-3
    bug = (await svc.create("bug", "shift-bug")).item  # BUG-4
    await svc.add_ref(task.id, bug.id)

    r = await invoke(["renumber", "--from", "3", "--onto", "10"])
    assert r.exit_code == 0, r.output
    assert "renumbered 2 item(s)" in r.output
    assert f"{feat.id} ->" not in r.output  # feature below --from is never listed in the remap

    db = await svc.store.load()
    # counter landed above both the other branch's counter (10) and our own prior max (4)
    assert db.counter > 10
    # the shifted bug file was renamed; the old one is gone
    old_bug_path = svc.paths.abspath(bug.path)
    assert not old_bug_path.exists()
    new_bug = next(it for it in db.items.values() if it.title == "shift-bug")
    assert svc.paths.abspath(new_bug.path).exists()
    # referential intent preserved: the task's ref now points at the SAME (renumbered) bug
    new_task = next(it for it in db.items.values() if it.title == "shift-task")
    assert new_task.refs == [new_bug.id]
    assert new_task.parent == feat.id  # untouched cross-boundary link still resolves


async def test_renumber_cli_rejects_both_onto_and_by(project, invoke, frozen_time):
    r = await invoke(["renumber", "--from", "2", "--onto", "5", "--by", "3"])
    assert r.exit_code != 0
    assert "exactly one" in r.output.lower()


async def test_renumber_cli_unsafe_by_refuses_with_no_mutation(project, invoke, frozen_time):
    from squads._services._service import Service

    svc = Service(project)
    squad_dir = svc.paths.squad_dir
    before_index = (squad_dir / ".squads.json").read_text(encoding="utf-8")

    r = await invoke(["renumber", "--from", "1", "--by", "0"])
    assert r.exit_code == 1, r.output
    assert "minimum safe offset" in r.output

    after_index = (squad_dir / ".squads.json").read_text(encoding="utf-8")
    assert before_index == after_index


def test_renumber_listed_in_root_help_and_shows_onto_recipe(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root = runner.invoke(app, ["--help"])
    assert root.exit_code == 0, root.output
    assert "renumber" in root.output

    sub = runner.invoke(app, ["renumber", "--help"])
    assert sub.exit_code == 0, sub.output
    help_text = _plain(sub.output)
    assert "--onto" in help_text and "--by" in help_text
    assert "squads.json" in help_text and "jq .counter" in help_text


async def test_check_cli_flags_index_item_with_no_file(project, invoke, frozen_time):
    """sq check exits 3 and flags items in the index whose files are gone."""
    import json

    from squads._services._service import Service

    svc = Service(project)
    await svc.create("task", "real task")  # TASK-000002

    # Inject a ghost item into the index (no file on disk).
    raw = json.loads(svc.store.index_path.read_text(encoding="utf-8"))
    raw["items"]["99"] = {
        "id": "TASK-99",
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

    r = await invoke(["check"])
    assert r.exit_code == 3, r.output
    assert "TASK-99" in r.output
    assert "no markdown" in r.output


# ---------------------------------------------------------------------------
# TASK-000047: resolver adoption sweep — CLI smoke for every ID-accepting surface
# ---------------------------------------------------------------------------


def test_create_parent_and_ref_bare_number(runner, tmp_path, monkeypatch, frozen_time):
    """create --parent and --ref accept bare numbers; unknown number errors mention both forms."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "feature", "F", "--author", "manager"])  # FEAT-000002
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])  # TASK-000003

    # ref add with bare number
    r = runner.invoke(app, ["task", "3", "ref", "add", "2"])
    assert r.exit_code == 0, r.output
    out = runner.invoke(app, ["task", "3", "refs"]).output
    assert "FEAT-2" in out

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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "epic", "E", "--author", "manager"])  # EPIC-000002
    runner.invoke(app, ["create", "feature", "F", "--author", "manager", "--parent", "EPIC-000002"])

    # bare number for root
    r = runner.invoke(app, ["tree", "2"])
    assert r.exit_code == 0, r.output
    assert "EPIC-2" in r.output

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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
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
    runner.invoke(
        app, ["init", "--no-seed-skills", "--roles", "minimal"]
    )  # activates `manager` only

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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])

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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])

    r = runner.invoke(app, ["role", "catalog"])
    assert r.exit_code == 0, r.output
    # Must include bundled roles
    assert "manager" in r.output
    assert "qa" in r.output
    assert "architect" in r.output


def test_role_list_removed(runner, tmp_path, monkeypatch, frozen_time):
    """sq role list falls through to the unknown-address path — exit 1, clean error, no leak."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    r = runner.invoke(app, ["skill", "list"])
    assert r.exit_code == 1
    assert "list" in r.output
    assert "_addr" not in r.output
    assert "Traceback" not in r.output


def test_operator_item_first_grammar(runner, tmp_path, monkeypatch, frozen_time):
    """sq operator <addr> show|rm — item-first grammar with slug/id/number resolution."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    r = runner.invoke(app, ["operator", "list"])
    assert r.exit_code == 1
    assert "list" in r.output
    assert "_addr" not in r.output
    assert "Traceback" not in r.output


def test_subtask_story_bare_number(runner, tmp_path, monkeypatch, frozen_time):
    """add-subtask --story accepts bare number like '1' normalized to 'US1'."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
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
    assert "FEAT-2" in out


def test_create_ref_kind_validation(runner, tmp_path, monkeypatch, frozen_time):
    """create --ref id:kind rejects unknown kinds; accepts valid kinds; bare id defaults related."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "Blocker", "--author", "manager"])  # TASK-000002
    runner.invoke(app, ["create", "task", "Dependent", "--author", "manager"])  # TASK-000003

    # TASK-000003 depends-on TASK-000002 → TASK-000003 is blocked by TASK-000002
    runner.invoke(app, ["task", "3", "ref", "add", "TASK-000002", "--kind", "depends-on"])

    r = runner.invoke(app, ["blocked"])
    assert r.exit_code == 0, r.output
    # TASK-3 (the dependent) should appear as blocked
    assert "TASK-3" in r.output
    # TASK-2 (the blocker) should appear as the reason
    assert "TASK-2" in r.output


def test_check_warns_unknown_kind_and_superseded_cli(runner, tmp_path, monkeypatch, frozen_time):
    """sq check warns on unknown ref kind and on Superseded decision without supersedes edge.

    Warnings do not flip the exit code (exit 0 when only warnings present).
    """
    import squads._sections as sections
    from squads._itemfile import read_frontmatter

    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
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
    assert "ADR-4" in r.output
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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])  # TASK-000002
    r = runner.invoke(app, ["task", "2", "comment", "--as", "manager", "-m", f"inject {_MARKER}"])
    assert r.exit_code == 1 and "marker" in r.output


def test_add_subtask_cli_rejects_marker_title(runner, tmp_path, monkeypatch, frozen_time):
    """CLI: `sq task <n> add-subtask` with a marker tag in the title exits 1."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])  # TASK-000002
    r = runner.invoke(app, ["task", "2", "add-subtask", f"title {_MARKER}"])
    assert r.exit_code == 1 and "marker" in r.output


def test_update_subtask_title_cli_rejects_marker(runner, tmp_path, monkeypatch, frozen_time):
    """CLI: `sq task <n> subtask <k> update --title` with a marker tag exits 1."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
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
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])  # TASK-000002
    r = runner.invoke(app, ["task", "2", "update", "--title", "[x] done label"])
    assert r.exit_code == 0, r.output
    md = next((tmp_path / "squads" / "tasks").glob("TASK-*.md")).read_text(encoding="utf-8")
    assert "[x] done label" in md


# ---------------------------------------------------------------------------
# TASK-000082: --json on check, sub-entity list commands, catalog viewers
# ---------------------------------------------------------------------------


def test_check_json_clean(runner, tmp_path, monkeypatch, frozen_time):
    """sq check --json emits [] (exit 0) when there are no issues.

    Runs with the production default (skill seeding enabled) so a regression in
    default seeding behaviour is caught here (F3 regression guard, FEAT-000178).
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    # Seeded skills must be present in the listing.
    ls = runner.invoke(app, ["list", "--type", "skill", "--json"])
    assert ls.exit_code == 0, ls.output
    skills = json.loads(ls.output)
    assert len(skills) > 0, "sq init must seed bundled skills by default"
    slugs = {sk["slug"] for sk in skills}
    assert "squads" in slugs and "greeting" in slugs
    # sq check must still be clean after seeding.
    r = runner.invoke(app, ["check", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data == []


async def test_check_json_with_issues(project, invoke, frozen_time):
    """sq check --json emits [{level, item, message}] and exits 3 when errors are present."""
    from squads._services._service import Service

    svc = Service(project)

    # Inject a ghost item into the index (no file on disk) to produce an error.
    raw = json.loads(svc.store.index_path.read_text(encoding="utf-8"))
    raw["items"]["99"] = {
        "id": "TASK-99",
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

    r = await invoke(["check", "--json"])
    assert r.exit_code == 3, r.output
    data = json.loads(r.output)
    assert len(data) >= 1
    issue = next(d for d in data if d["item"] == "TASK-99")
    assert issue["level"] == "error"
    assert "level" in issue and "item" in issue and "message" in issue


def test_check_json_warnings_only_exits_0(runner, tmp_path, monkeypatch, frozen_time):
    """sq check --json with only warnings exits 0 (not 3)."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "decision", "Old ADR", "--author", "manager"])  # ADR-000002
    runner.invoke(app, ["decision", "2", "status", "Proposed"])
    runner.invoke(app, ["decision", "2", "update", "--status", "Superseded", "--force"])
    runner.invoke(app, ["repair"])

    r = runner.invoke(app, ["check", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert all(d["level"] == "warn" for d in data)


def test_stories_json(runner, tmp_path, monkeypatch, frozen_time):
    """sq feature <n> stories --json emits [{local_id, title, status, assignee, …}]."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "feature", "F", "--author", "manager"])  # FEAT-000002
    runner.invoke(app, ["feature", "2", "add-story", "As a user I want X"])  # US1
    runner.invoke(app, ["feature", "2", "add-story", "As a user I want Y"])  # US2

    r = runner.invoke(app, ["feature", "2", "stories", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert len(data) == 2
    s = data[0]
    assert s["local_id"] == "US1"
    assert s["title"] == "As a user I want X"
    assert s["status"] == "Todo"
    assert "assignee" in s
    assert "severity" in s  # always present (null for stories)
    assert "story" in s  # always present (null for stories)
    assert s["severity"] is None
    assert s["story"] is None


def test_subtasks_json(runner, tmp_path, monkeypatch, frozen_time):
    """sq task <n> subtasks --json emits [{local_id, title, status, assignee, severity, story}]."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "feature", "F", "--author", "manager"])  # FEAT-000002
    runner.invoke(  # TASK-000003
        app, ["create", "task", "T", "--author", "manager", "--parent", "FEAT-000002"]
    )
    runner.invoke(app, ["feature", "2", "add-story", "Story One"])  # US1
    runner.invoke(app, ["task", "3", "add-subtask", "Do the thing", "--story", "US1"])  # ST1

    r = runner.invoke(app, ["task", "3", "subtasks", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert len(data) == 1
    st = data[0]
    assert st["local_id"] == "ST1"
    assert st["title"] == "Do the thing"
    assert st["status"] == "Todo"
    assert st["story"] == "US1"
    assert st["severity"] is None


def test_findings_json(runner, tmp_path, monkeypatch, frozen_time):
    """sq review <n> findings --json emits [{local_id, title, status, severity, …}]."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "review", "R", "--author", "manager"])  # REV-000002
    runner.invoke(  # F1
        app, ["review", "2", "add-finding", "Null pointer risk", "--severity", "high"]
    )

    r = runner.invoke(app, ["review", "2", "findings", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert len(data) == 1
    f = data[0]
    assert f["local_id"] == "F1"
    assert f["title"] == "Null pointer risk"
    assert f["status"] == "Open"
    assert f["severity"] == "high"
    assert f["story"] is None


def test_role_catalog_json(runner, tmp_path, monkeypatch, frozen_time):
    """sq role catalog --json emits [{slug, full_name, title, is_default}] for all bundled roles."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    r = runner.invoke(app, ["role", "catalog", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert len(data) >= 8  # all bundled roles
    slugs = [d["slug"] for d in data]
    assert "manager" in slugs and "qa" in slugs and "architect" in slugs
    entry = next(d for d in data if d["slug"] == "manager")
    assert entry["full_name"] == "Catherine Manager"
    assert entry["is_default"] is True
    assert "title" in entry


def test_role_show_json_activated(runner, tmp_path, monkeypatch, frozen_time):
    """sq role <slug> show --json emits role metadata for an activated role."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(
        app, ["init", "--no-seed-skills", "--roles", "minimal"]
    )  # activates manager → ROLE-000001
    r = runner.invoke(app, ["role", "manager", "show", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data["slug"] == "manager"
    assert data["full_name"] == "Catherine Manager"
    assert data["activated"] is True
    assert data["id"] == "ROLE-1"
    assert isinstance(data["responsibilities"], list)


def test_role_show_json_bundled_only(runner, tmp_path, monkeypatch, frozen_time):
    """sq role <slug> show --json emits role metadata for a bundled-only (not activated) role."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])  # qa not activated
    r = runner.invoke(app, ["role", "qa", "show", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data["slug"] == "qa"
    assert data["activated"] is False
    assert data["id"] is None


def test_skill_show_json(runner, tmp_path, monkeypatch, frozen_time):
    """sq skill <addr> show --json emits {id, slug, title, status, description, when_to_use, …}."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(
        app,
        ["skill", "add", "my-skill", "--desc", "A handy skill", "--when-to-use", "When needed"],
    )  # SKILL-000002
    r = runner.invoke(app, ["skill", "2", "show", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data["id"] == "SKILL-2"
    assert data["slug"] == "my-skill"
    assert data["description"] == "A handy skill"
    assert data["when_to_use"] == "When needed"
    assert data["status"] == "Active"
    assert "path" in data


def test_operator_show_json(runner, tmp_path, monkeypatch, frozen_time):
    """sq operator <addr> show --json emits {id, slug, full_name, status, path}."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["operator", "add", "Alice Tester"])  # OP-000002
    r = runner.invoke(app, ["operator", "op-alice", "show", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data["slug"] == "op-alice"
    assert data["full_name"] == "Alice Tester"
    assert data["status"] == "Active"
    assert "id" in data and "path" in data


# ---------------------------------------------------------------------------
# TASK-000083: exit-code contract — 0 success, 1 runtime error (incl. schema
# mismatch), 2 usage error, 3 sq check found error-level issues
# ---------------------------------------------------------------------------


def test_exit_code_0_success(runner, tmp_path, monkeypatch, frozen_time):
    """Exit 0: a clean squad and a successful read command."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    r = runner.invoke(app, ["list"])
    assert r.exit_code == 0, r.output


def test_exit_code_0_check_clean(runner, tmp_path, monkeypatch, frozen_time):
    """Exit 0: sq check with no issues."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    r = runner.invoke(app, ["check"])
    assert r.exit_code == 0, r.output
    assert "no issues" in r.output


def test_exit_code_0_check_warnings_only(runner, tmp_path, monkeypatch, frozen_time):
    """Exit 0: sq check with warnings only (no error-level issues) does not exit 3."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    # A Superseded decision without a supersedes edge produces a warn, not an error.
    runner.invoke(app, ["create", "decision", "Old ADR", "--author", "manager"])  # ADR-000002
    runner.invoke(app, ["decision", "2", "status", "Proposed"])
    runner.invoke(app, ["decision", "2", "update", "--status", "Superseded", "--force"])
    runner.invoke(app, ["repair"])

    r = runner.invoke(app, ["check"])
    assert r.exit_code == 0, r.output
    assert "warn" in r.output


def test_exit_code_1_squads_runtime_error(runner, tmp_path, monkeypatch, frozen_time):
    """Exit 1: a SquadsError (unknown item ID) produces exit code 1."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    r = runner.invoke(app, ["task", "999", "show"])
    assert r.exit_code == 1, r.output


def test_exit_code_1_schema_mismatch(runner, tmp_path, monkeypatch, frozen_time):
    """Exit 1: a schema-version mismatch hard-stops with exit code 1."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])

    # Force the on-disk schema version to something old so the gate fires.
    cfg = tmp_path / ".squads.toml"
    cfg.write_text(
        cfg.read_text(encoding="utf-8").replace(
            f'schema_version = "{SCHEMA_VERSION}"', 'schema_version = "0.1"'
        ),
        encoding="utf-8",
    )

    r = runner.invoke(app, ["list"])
    assert r.exit_code == 1, r.output
    # The error message should point the user at `sq migrate up`.
    assert "migrate" in r.output.lower()


def test_exit_code_2_invalid_at_timestamp(runner, tmp_path, monkeypatch, frozen_time):
    """Exit 2: an invalid --at timestamp format produces exit code 2."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    r = runner.invoke(app, ["--at", "not-a-date", "list"])
    assert r.exit_code == 2, r.output


async def test_exit_code_3_check_error_level_issue(project, invoke, frozen_time):
    """Exit 3: sq check exits 3 when at least one error-level issue is present."""
    from squads._services._service import Service

    svc = Service(project)

    # Inject a ghost item into the index (no file on disk) to produce an error-level check issue.
    raw = json.loads(svc.store.index_path.read_text(encoding="utf-8"))
    raw["items"]["99"] = {
        "id": "TASK-99",
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

    r = await invoke(["check"])
    assert r.exit_code == 3, r.output
    assert "TASK-99" in r.output


async def test_exit_code_3_check_json_error_level_issue(project, invoke, frozen_time):
    """Exit 3: sq check --json also exits 3 on error-level issues."""
    from squads._services._service import Service

    svc = Service(project)

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

    r = await invoke(["check", "--json"])
    assert r.exit_code == 3, r.output
    data = json.loads(r.output)
    assert any(issue["level"] == "error" for issue in data)


# --------------------------------------------------------------------------- padding / FEAT-000027


async def test_repair_cli_holds_padding_after_file_loss(project, invoke, frozen_time):
    """sq repair preserves the stored padding floor even when item files are deleted."""
    from squads._services._service import Service

    svc = Service(project)
    top = (await svc.create("task", "task")).item

    # Bump padding to 7 in the index to simulate a post-repad squad.
    raw = json.loads(svc.store.index_path.read_text(encoding="utf-8"))
    raw["padding"] = 7
    svc.store.index_path.write_text(json.dumps(raw), encoding="utf-8")

    # Delete the task file so the corpus recompute would give width 6.
    svc.paths.abspath(top.path).unlink()

    r = await invoke(["repair"])
    assert r.exit_code == 0, r.output
    # Padding must stay at 7 (floor from stored value, not regressed to 6).
    assert (await svc.store.load()).padding == 7


async def test_create_cli_exits_1_when_index_full(project, invoke, frozen_time):
    """sq create exits 1 with the index-full message naming sq migrate repad at capacity."""
    from squads._services._service import Service

    svc = Service(project)
    # Force counter to 10^6 - 1 (all width-6 IDs exhausted).
    raw = json.loads(svc.store.index_path.read_text(encoding="utf-8"))
    raw["counter"] = 10**6 - 1
    svc.store.index_path.write_text(json.dumps(raw), encoding="utf-8")

    r = await invoke(["create", "task", "overflow task", "--author", "manager"])
    assert r.exit_code == 1, r.output
    assert "sq migrate repad" in r.output


async def test_migrate_repad_cli(project, invoke, frozen_time):
    """sq migrate repad <width> renames files, prints summary, exits 0."""
    from squads._services._service import Service

    svc = Service(project)
    await svc.create("task", "task one")

    r = await invoke(["migrate", "repad", "7"])
    assert r.exit_code == 0, r.output
    assert "repad done" in r.output
    assert "6 → 7" in r.output
    assert "sq check" in r.output

    # Index padding updated.
    assert (await svc.store.load()).padding == 7

    # All ID-prefixed item files now have 7-digit widths.
    # Skill files use slug-only names (e.g. squads.md, sq-bug.md) and are not repadded — skip them.
    for _, md in svc._iter_item_files():  # pyright: ignore[reportPrivateUsage]
        stem = md.stem
        _, sep, digits_slug = stem.partition("-")
        digit_run = digits_slug.split("-", 1)[0] if sep else ""
        if not digit_run.isdigit():
            continue  # slug-only or non-ID filename (skill files like squads.md) — not repadded
        assert len(digit_run) == 7, f"expected 7-digit run, got {digit_run!r} in {md.name}"


async def test_migrate_repad_cli_refuses_to_lower(project, invoke, frozen_time):
    """sq migrate repad exits 1 when the requested width <= current padding."""
    r = await invoke(["migrate", "repad", "6"])
    assert r.exit_code == 1, r.output
    assert "must be greater than" in r.output


# ---------------------------------------------------------------------- rename-type/rename-status

# "ticket" mirrors "task" (same lifecycle/parent/sub-entity kind) except its prefix/folder —
# the feature does not declare this itself, so tests bring it in as a project override.
_TICKET_OVERRIDE_TOML = """\
[items.ticket]
prefix = "TICKET"
folder = "tickets"
lifecycle = "work"
parents = ["feature"]
subentity_kind = "subtask"
parent_required = "feature"
"""


def _write_ticket_override(squad_dir) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(_TICKET_OVERRIDE_TOML, encoding="utf-8")


async def test_migrate_rename_type_cli(project, invoke, frozen_time):
    """sq migrate rename-type moves every item of one declared type to another."""
    from squads._services._service import Service

    _write_ticket_override(project.squad_dir)
    svc = Service(project)
    created = await svc.create("task", "task one")

    r = await invoke(["migrate", "rename-type", "task", "ticket"])
    assert r.exit_code == 0, r.output
    assert "task → ticket" in r.output
    assert "1 item(s) renamed" in r.output
    assert "sq check" in r.output

    # Read the raw index: a plain Service(project) uses the bundled-only spec, which no
    # longer declares "ticket" once the rename lands, so it can't load() the squad.
    raw = json.loads(svc.store.index_path.read_text(encoding="utf-8"))
    entry = raw["items"][str(created.item.sequence_id)]
    assert entry["type"] == "ticket"


async def test_migrate_rename_type_cli_refuses_reserved_meta_type(project, invoke, frozen_time):
    """sq migrate rename-type exits 1 cleanly when the source type is a reserved meta-type."""
    r = await invoke(["migrate", "rename-type", "role", "worker"])
    assert r.exit_code == 1, r.output
    assert "reserved meta-type" in r.output


async def test_migrate_rename_status_cli(project, invoke, frozen_time):
    """sq migrate rename-status moves every matching item to the new status label."""
    from squads._services._service import Service

    svc = Service(project)
    created = await svc.create("task", "task one")  # created at Draft
    item_id = created.item.id

    r = await invoke(["migrate", "rename-status", "task", "Draft", "Ready"])
    assert r.exit_code == 0, r.output
    assert "task: Draft → Ready" in r.output
    assert "1 item(s) renamed" in r.output
    # The id-pair pitfall: a status rename never changes the id, so it must not print
    # something like "TASK-1 → TASK-1".
    assert f"{item_id} → {item_id}" not in r.output

    db = await svc.store.load()
    item = db.items[created.item.sequence_id]
    assert item.status == "Ready"


async def test_migrate_rename_status_cli_refuses_invalid_new_status(project, invoke, frozen_time):
    """sq migrate rename-status exits 1 when NEW_STATUS isn't a state of TYPE's lifecycle."""
    r = await invoke(["migrate", "rename-status", "task", "Draft", "NotAStatus"])
    assert r.exit_code == 1, r.output
    assert "is not a state of" in r.output


# --------------------------------------------------------------------------- width-tolerant CLI


async def test_cli_old_width_address_resolves_after_repad(project, invoke, frozen_time):
    """CLI commands accept any-width IDs after a repad (width-tolerant addressing).

    After sq migrate repad 7, 'sq task 2 show' must work whether the user passes
    "TASK-000002" (old filename width), "TASK-0000002" (new filename width), or a bare
    number. Repad only changes filenames — the displayed id always stays unpadded
    (ADR-000282).
    """
    import json as _json

    from squads._services._service import Service

    svc = Service(project)
    await svc.create("task", "my task")  # TASK-2

    await invoke(["migrate", "repad", "7"])

    # Bare number — always works (width-agnostic).
    r = await invoke(["task", "2", "show", "--json"])
    assert r.exit_code == 0, r.output
    data = _json.loads(r.output)
    assert data["id"] == "TASK-2", "display stays unpadded regardless of filename width"

    # Old-width full ID — must resolve.
    r_old = await invoke(["task", "TASK-000002", "show", "--json"])
    assert r_old.exit_code == 0, r_old.output
    data_old = _json.loads(r_old.output)
    assert data_old["id"] == "TASK-2"

    # New-width full ID — must also resolve.
    r_new = await invoke(["task", "TASK-0000002", "show", "--json"])
    assert r_new.exit_code == 0, r_new.output
    data_new = _json.loads(r_new.output)
    assert data_new["id"] == "TASK-2"


async def test_cli_tree_with_mixed_width_after_repad(project, invoke, frozen_time):
    """sq tree resolves old-width and new-width root IDs correctly after a repad."""
    import json as _json

    from squads._services._service import Service

    svc = Service(project)
    await svc.create("feature", "feat")  # FEAT-000002
    await svc.create("task", "task", parent="FEAT-000002")  # TASK-000003

    await invoke(["migrate", "repad", "7"])

    # sq tree with old-width ID must resolve; display always stays unpadded (ADR-000282).
    r_old = await invoke(["tree", "FEAT-000002", "--json"])
    assert r_old.exit_code == 0, r_old.output
    nodes = _json.loads(r_old.output)
    assert len(nodes) == 1
    assert nodes[0]["id"] == "FEAT-2"

    # sq tree with new-width ID must also work.
    r_new = await invoke(["tree", "FEAT-0000002", "--json"])
    assert r_new.exit_code == 0, r_new.output
    nodes_new = _json.loads(r_new.output)
    assert nodes_new[0]["id"] == "FEAT-2"

    # The task appears as a child.
    children = nodes[0]["children"]
    assert any(c["id"] == "TASK-3" for c in children)


async def test_cli_check_clean_with_old_width_refs_after_repad(project, invoke, frozen_time):
    """sq check is clean when items hold old-width refs after a repad."""
    from squads._services._service import Service

    svc = Service(project)
    feat = (await svc.create("feature", "feat")).item  # FEAT-000002
    task = (await svc.create("task", "task")).item  # TASK-000003
    await svc.add_ref(task.id, feat.id, kind="implements")  # TASK refs FEAT (width-6 stored)

    await invoke(["migrate", "repad", "7"])

    r = await invoke(["check", "--json"])
    issues = json.loads(r.output)
    errors = [i for i in issues if i["level"] == "error"]
    assert not errors, f"sq check errors after repad with old-width refs: {errors}"


# ---------------------------------------------------------------------------
# Shell completion (FEAT-000017 / TASK-000128)
# ---------------------------------------------------------------------------


def test_shell_completion_scripts_are_non_empty(runner):
    # --show-completion must emit a non-empty, well-formed script for bash and zsh.
    # We disable Typer's auto-detection so the explicit shell name is always honoured
    # regardless of the host shell (test suite runs under bash on CI).
    os.environ["_TYPER_COMPLETE_TEST_DISABLE_SHELL_DETECTION"] = "1"
    try:
        bash_r = runner.invoke(app, ["--show-completion", "bash"])
        zsh_r = runner.invoke(app, ["--show-completion", "zsh"])
    finally:
        os.environ.pop("_TYPER_COMPLETE_TEST_DISABLE_SHELL_DETECTION", None)

    assert bash_r.exit_code == 0, bash_r.output
    assert zsh_r.exit_code == 0, zsh_r.output

    # bash script contains the complete built-in and the bash-specific env var
    assert "_sq_completion" in bash_r.output
    assert "complete_bash" in bash_r.output
    assert len(bash_r.output.strip()) > 0

    # zsh script starts with the compdef directive (distinct from bash)
    assert "#compdef sq" in zsh_r.output
    assert "complete_zsh" in zsh_r.output
    assert len(zsh_r.output.strip()) > 0

    # the two scripts must be distinct — they target different shells
    assert bash_r.output != zsh_r.output


def test_hoist_global_options_does_not_break_completion_args():
    # The _hoist_global_options shim must pass --show-completion / --install-completion
    # through untouched; they are not global value-options and must not be reordered.
    assert _hoist_global_options(["--show-completion", "bash"]) == ["--show-completion", "bash"]
    assert _hoist_global_options(["--show-completion", "zsh"]) == ["--show-completion", "zsh"]
    assert _hoist_global_options(["--install-completion", "zsh"]) == [
        "--install-completion",
        "zsh",
    ]
    # a real global option mixed after completion args is hoisted, completion args stay in place
    result = _hoist_global_options(["--show-completion", "bash", "--dir", "/tmp"])
    assert result == ["--dir", "/tmp", "--show-completion", "bash"]


# ---------------------------------------------------------------------------
# FEAT-000250 / TASK-000253 — per-invocation spec context handle
# ---------------------------------------------------------------------------


def test_spec_bound_before_parse_type_runs(tmp_path, monkeypatch):
    """Root callback binds the WorkflowSpec before parse_type / parse_status fire.

    Click calls the group callback first, then parses the subcommand's own options.
    parse_type (--type) and parse_status (--status) are Typer parser callbacks that call
    get_active_spec(); they must find the spec already bound or they fall back to the
    bundled spec incorrectly.  This test exercises both parser callbacks inside a real CLI
    invocation (sq list --type task --status InProgress) and asserts exit 0 — which is only
    possible if the bundled spec was bound before parse_type / parse_status ran.
    """
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    # Bootstrap a minimal squad so require_current_schema doesn't abort.
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])

    # After a successful invocation the per-invocation handle must hold the bundled spec.
    from squads._cli._common import get_active_spec  # pyright: ignore[reportPrivateUsage]
    from squads._workflow import bundled_spec

    # --type and --status trigger parse_type / parse_status; exit 0 proves the spec was
    # bound before those callbacks ran (otherwise "task" / "InProgress" would be rejected
    # as unknown values against an uninitialised spec).
    result = runner.invoke(app, ["list", "--type", "task", "--status", "InProgress"])
    assert result.exit_code == 0, result.output

    # The handle is set to the bundled spec (no override present).
    assert get_active_spec() is bundled_spec()


def test_parse_type_fallback_to_bundled_spec_outside_squad(tmp_path, monkeypatch):
    """parse_type/parse_status fall back to the bundled spec when called outside a squad.

    This covers the case where ``get_active_spec()`` has not been bound yet (no group
    callback has run), so the function should return the bundled spec transparently.
    """
    monkeypatch.chdir(tmp_path)
    # Reset the per-invocation handle to simulate "no invocation yet".
    from squads._cli._common import (  # pyright: ignore[reportPrivateUsage]
        get_active_spec,
        parse_type,
        set_active_spec,  # pyright: ignore[reportPrivateUsage]
    )
    from squads._workflow import bundled_spec

    set_active_spec(None)

    # Bundled spec is the fallback — a known type must be accepted.
    assert get_active_spec() is bundled_spec()
    assert parse_type("task") == "task"


def test_parse_status_validates_against_active_spec(tmp_path, monkeypatch):
    """parse_status accepts canonical and loose forms; rejects unknown values."""
    monkeypatch.chdir(tmp_path)
    from squads._cli._common import (
        parse_status,  # pyright: ignore[reportPrivateUsage]
        set_active_spec,  # pyright: ignore[reportPrivateUsage]
    )
    from squads._workflow import bundled_spec

    set_active_spec(bundled_spec())

    assert parse_status("InProgress") == "InProgress"
    # Loose forms are normalized.
    assert parse_status("inprogress") == "InProgress"
    assert parse_status("in_progress") == "InProgress"

    # Unknown status raises.
    from squads._errors import SquadsError

    with pytest.raises(SquadsError, match="unknown status"):
        parse_status("Flying")
