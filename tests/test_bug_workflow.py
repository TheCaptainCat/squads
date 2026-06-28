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
from squads._models._enums import ItemType, Status

# --------------------------------------------------------------------------- workflow unit tests


def test_bug_initial_status_is_open():
    assert workflow.initial_status(ItemType.BUG) == Status.OPEN


def test_bug_workflow_states():
    states = workflow.workflow_for(ItemType.BUG).states
    expected = {
        Status.OPEN,
        Status.IN_PROGRESS,
        Status.FIXED,
        Status.VERIFIED,
        Status.BLOCKED,
        Status.WONT_FIX,
        Status.CANCELLED,
    }
    assert states == expected


def test_bug_workflow_excludes_work_states():
    """Draft, Ready, InReview, Done, Todo are not bug states."""
    states = workflow.workflow_for(ItemType.BUG).states
    for invalid in (
        Status.DRAFT,
        Status.READY,
        Status.IN_REVIEW,
        Status.DONE,
        Status.TODO,
    ):
        assert invalid not in states


def test_bug_valid_transitions():
    wf = workflow.workflow_for(ItemType.BUG)
    assert wf.can_transition(Status.OPEN, Status.IN_PROGRESS)
    assert wf.can_transition(Status.OPEN, Status.WONT_FIX)
    assert wf.can_transition(Status.OPEN, Status.CANCELLED)
    assert wf.can_transition(Status.IN_PROGRESS, Status.FIXED)
    assert wf.can_transition(Status.IN_PROGRESS, Status.BLOCKED)
    assert wf.can_transition(Status.IN_PROGRESS, Status.WONT_FIX)
    assert wf.can_transition(Status.IN_PROGRESS, Status.CANCELLED)
    assert wf.can_transition(Status.FIXED, Status.VERIFIED)
    assert wf.can_transition(Status.FIXED, Status.IN_PROGRESS)  # reopen on failed verify
    assert wf.can_transition(Status.VERIFIED, Status.IN_PROGRESS)  # reopen on regression
    assert wf.can_transition(Status.BLOCKED, Status.IN_PROGRESS)
    assert wf.can_transition(Status.BLOCKED, Status.WONT_FIX)
    assert wf.can_transition(Status.BLOCKED, Status.CANCELLED)
    assert wf.can_transition(Status.WONT_FIX, Status.OPEN)
    assert wf.can_transition(Status.CANCELLED, Status.OPEN)


def test_bug_invalid_transitions():
    wf = workflow.workflow_for(ItemType.BUG)
    assert not wf.can_transition(Status.OPEN, Status.VERIFIED)
    assert not wf.can_transition(Status.OPEN, Status.FIXED)
    assert not wf.can_transition(Status.VERIFIED, Status.FIXED)
    assert not wf.can_transition(Status.VERIFIED, Status.OPEN)


def test_bug_terminals_in_terminal_set():
    """Verified, WontFix, Cancelled must all be in TERMINAL."""
    for s in (Status.VERIFIED, Status.WONT_FIX, Status.CANCELLED):
        assert s in workflow.TERMINAL, f"{s.value} not in TERMINAL"


# --------------------------------------------------------------------------- set-time validation


async def test_set_status_rejects_out_of_workflow_vocabulary(svc):
    """StatusNotInWorkflowError raised at set-time for a status not in the bug workflow."""
    bug = (await svc.create(ItemType.BUG, "crash on login")).item
    assert bug.status == Status.OPEN

    with pytest.raises(StatusNotInWorkflowError, match="'Done' is not a valid status for bug"):
        await svc.set_status(bug.id, Status.DONE)


async def test_force_does_not_bypass_vocabulary_check(svc):
    """--force only relaxes transition edges, never the vocabulary check."""
    bug = (await svc.create(ItemType.BUG, "crash")).item

    with pytest.raises(StatusNotInWorkflowError, match="not a valid status for bug"):
        await svc.set_status(bug.id, Status.DONE, force=True)


async def test_force_bypasses_transition_edge_within_bug_vocabulary(svc):
    """--force lets you skip an edge (Open→Verified) when the target is in the bug vocabulary."""
    bug = (await svc.create(ItemType.BUG, "crash")).item
    # Open→Verified is not a legal edge, but Verified is a valid bug state
    # Without force this raises InvalidTransitionError (not StatusNotInWorkflowError)
    with pytest.raises(InvalidTransitionError):
        await svc.set_status(bug.id, Status.VERIFIED)
    # With force it succeeds
    result = await svc.set_status(bug.id, Status.VERIFIED, force=True)
    assert result.status == Status.VERIFIED


async def test_set_status_rejects_multiple_invalid_statuses(svc):
    """All work-item-only statuses are rejected for bugs."""
    bug = (await svc.create(ItemType.BUG, "crash")).item
    for invalid in (Status.DRAFT, Status.READY, Status.IN_REVIEW, Status.DONE):
        with pytest.raises(StatusNotInWorkflowError):
            await svc.set_status(bug.id, invalid, force=True)


async def test_bug_happy_path_lifecycle(svc):
    """Full Open → InProgress → Fixed → Verified lifecycle works."""
    bug = (await svc.create(ItemType.BUG, "null pointer")).item
    assert bug.status == Status.OPEN

    bug = await svc.set_status(bug.id, Status.IN_PROGRESS)
    assert bug.status == Status.IN_PROGRESS

    bug = await svc.set_status(bug.id, Status.FIXED)
    assert bug.status == Status.FIXED

    bug = await svc.set_status(bug.id, Status.VERIFIED)
    assert bug.status == Status.VERIFIED


async def test_bug_wontfix_and_reopen(svc):
    """Open → WontFix → Open reopen works."""
    bug = (await svc.create(ItemType.BUG, "by design")).item
    bug = await svc.set_status(bug.id, Status.WONT_FIX)
    assert bug.status == Status.WONT_FIX
    bug = await svc.set_status(bug.id, Status.OPEN)
    assert bug.status == Status.OPEN


async def test_bug_regression_reopen(svc):
    """Verified → InProgress reopens a regressed bug."""
    bug = (await svc.create(ItemType.BUG, "flicker")).item
    await svc.set_status(bug.id, Status.IN_PROGRESS)
    await svc.set_status(bug.id, Status.FIXED)
    await svc.set_status(bug.id, Status.VERIFIED)
    bug = await svc.set_status(bug.id, Status.IN_PROGRESS)
    assert bug.status == Status.IN_PROGRESS


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
