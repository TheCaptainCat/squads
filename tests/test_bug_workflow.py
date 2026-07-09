"""Tests for the bug-specific workflow (_BUG) and the set-time status vocabulary check.

Covers:
- Bug workflow initial state, valid transitions, terminal membership.
- StatusNotInWorkflowError raised at set-time for out-of-workflow statuses (e.g. Done on a bug).
- --force does NOT bypass the vocabulary check (only the transition-edge check).
"""

import pytest

from squads import _workflow as workflow
from squads._cli import app
from squads._errors import InvalidTransitionError, StatusNotInWorkflowError

# --------------------------------------------------------------------------- workflow unit tests


def test_bug_initial_status_is_open():
    assert workflow.initial_status("bug") == "Open"


def test_bug_workflow_states():
    states = workflow.workflow_for("bug").states
    expected = {
        "Open",
        "InProgress",
        "Fixed",
        "Verified",
        "Blocked",
        "WontFix",
        "Cancelled",
    }
    assert states == expected


def test_bug_workflow_excludes_work_states():
    """Draft, Ready, InReview, Done, Todo are not bug states."""
    states = workflow.workflow_for("bug").states
    for invalid in (
        "Draft",
        "Ready",
        "InReview",
        "Done",
        "Todo",
    ):
        assert invalid not in states


def test_bug_valid_transitions():
    wf = workflow.workflow_for("bug")
    assert wf.can_transition("Open", "InProgress")
    assert wf.can_transition("Open", "WontFix")
    assert wf.can_transition("Open", "Cancelled")
    assert wf.can_transition("InProgress", "Fixed")
    assert wf.can_transition("InProgress", "Blocked")
    assert wf.can_transition("InProgress", "WontFix")
    assert wf.can_transition("InProgress", "Cancelled")
    assert wf.can_transition("Fixed", "Verified")
    assert wf.can_transition("Fixed", "InProgress")  # reopen on failed verify
    assert wf.can_transition("Verified", "InProgress")  # reopen on regression
    assert wf.can_transition("Blocked", "InProgress")
    assert wf.can_transition("Blocked", "WontFix")
    assert wf.can_transition("Blocked", "Cancelled")
    assert wf.can_transition("WontFix", "Open")
    assert wf.can_transition("Cancelled", "Open")


def test_bug_invalid_transitions():
    wf = workflow.workflow_for("bug")
    assert not wf.can_transition("Open", "Verified")
    assert not wf.can_transition("Open", "Fixed")
    assert not wf.can_transition("Verified", "Fixed")
    assert not wf.can_transition("Verified", "Open")


def test_bug_terminals_in_terminal_set():
    """Verified, WontFix, Cancelled must all be in TERMINAL."""
    for s in ("Verified", "WontFix", "Cancelled"):
        assert s in workflow.TERMINAL, f"{s} not in TERMINAL"


# --------------------------------------------------------------------------- set-time validation


async def test_set_status_rejects_out_of_workflow_vocabulary(svc):
    """StatusNotInWorkflowError raised at set-time for a status not in the bug workflow."""
    bug = (await svc.create("bug", "crash on login")).item
    assert bug.status == "Open"

    with pytest.raises(StatusNotInWorkflowError, match="'Done' is not a valid status for bug"):
        await svc.set_status(bug.id, "Done")


async def test_force_does_not_bypass_vocabulary_check(svc):
    """--force only relaxes transition edges, never the vocabulary check."""
    bug = (await svc.create("bug", "crash")).item

    with pytest.raises(StatusNotInWorkflowError, match="not a valid status for bug"):
        await svc.set_status(bug.id, "Done", force=True)


async def test_force_bypasses_transition_edge_within_bug_vocabulary(svc):
    """--force lets you skip an edge (Open→Verified) when the target is in the bug vocabulary."""
    bug = (await svc.create("bug", "crash")).item
    # Open→Verified is not a legal edge, but Verified is a valid bug state
    # Without force this raises InvalidTransitionError (not StatusNotInWorkflowError)
    with pytest.raises(InvalidTransitionError):
        await svc.set_status(bug.id, "Verified")
    # With force it succeeds
    result = await svc.set_status(bug.id, "Verified", force=True)
    assert result.status == "Verified"


async def test_set_status_rejects_multiple_invalid_statuses(svc):
    """All work-item-only statuses are rejected for bugs."""
    bug = (await svc.create("bug", "crash")).item
    for invalid in ("Draft", "Ready", "InReview", "Done"):
        with pytest.raises(StatusNotInWorkflowError):
            await svc.set_status(bug.id, invalid, force=True)


async def test_bug_happy_path_lifecycle(svc):
    """Full Open → InProgress → Fixed → Verified lifecycle works."""
    bug = (await svc.create("bug", "null pointer")).item
    assert bug.status == "Open"

    bug = await svc.set_status(bug.id, "InProgress")
    assert bug.status == "InProgress"

    bug = await svc.set_status(bug.id, "Fixed")
    assert bug.status == "Fixed"

    bug = await svc.set_status(bug.id, "Verified")
    assert bug.status == "Verified"


async def test_bug_wontfix_and_reopen(svc):
    """Open → WontFix → Open reopen works."""
    bug = (await svc.create("bug", "by design")).item
    bug = await svc.set_status(bug.id, "WontFix")
    assert bug.status == "WontFix"
    bug = await svc.set_status(bug.id, "Open")
    assert bug.status == "Open"


async def test_bug_regression_reopen(svc):
    """Verified → InProgress reopens a regressed bug."""
    bug = (await svc.create("bug", "flicker")).item
    await svc.set_status(bug.id, "InProgress")
    await svc.set_status(bug.id, "Fixed")
    await svc.set_status(bug.id, "Verified")
    bug = await svc.set_status(bug.id, "InProgress")
    assert bug.status == "InProgress"


# --------------------------------------------------------------------------- CLI smoke tests


def test_cli_bug_status_rejects_done(runner, tmp_path, monkeypatch, frozen_time):
    """CLI: `sq bug N status Done` is rejected at set-time with a clear error."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "bug", "Crash", "--author", "manager"])

    r = runner.invoke(app, ["bug", "2", "status", "Done"])
    assert r.exit_code == 1
    assert "not a valid status for bug" in r.output


def test_cli_bug_status_force_no_vocabulary_bypass(runner, tmp_path, monkeypatch, frozen_time):
    """CLI: `sq bug N status Done --force` is still rejected (vocabulary, not edge)."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "bug", "Crash", "--author", "manager"])

    r = runner.invoke(app, ["bug", "2", "status", "Done", "--force"])
    assert r.exit_code == 1
    assert "not a valid status for bug" in r.output


def test_cli_bug_full_lifecycle(runner, tmp_path, monkeypatch, frozen_time):
    """CLI: complete bug lifecycle from Open to Verified."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "bug", "Null pointer", "--author", "manager"])

    r = runner.invoke(app, ["bug", "2", "status", "InProgress"])
    assert r.exit_code == 0 and "InProgress" in r.output

    r = runner.invoke(app, ["bug", "2", "status", "Fixed"])
    assert r.exit_code == 0 and "Fixed" in r.output

    r = runner.invoke(app, ["bug", "2", "status", "Verified"])
    assert r.exit_code == 0 and "Verified" in r.output
