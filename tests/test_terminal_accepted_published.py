"""Regression and coverage tests for ACCEPTED and PUBLISHED in the TERMINAL set.

BUG-000080: inbox surfaced stale mentions from Accepted decisions and Published guides
because those statuses were missing from TERMINAL.

TASK-000081: adds ACCEPTED and PUBLISHED to the TERMINAL frozenset; this file verifies
every consumer that cares about terminal status is now correct.
"""

import pytest

from squads import _workflow as workflow
from squads._cli import app
from squads._models._enums import ItemType, Status

# --------------------------------------------------------------------------- TERMINAL membership


def test_accepted_and_published_are_terminal():
    assert Status.ACCEPTED in workflow.TERMINAL
    assert Status.PUBLISHED in workflow.TERMINAL


def test_accepted_and_published_are_not_open():
    assert not workflow.is_open(Status.ACCEPTED)
    assert not workflow.is_open(Status.PUBLISHED)


# --------------------------------------------------------------------------- inbox


def test_inbox_excludes_mention_on_accepted_decision(svc):
    """Regression: a mention written when an ADR was Proposed must NOT appear in inbox
    after the ADR transitions to Accepted."""
    adr = svc.create(ItemType.DECISION, "Use CQRS pattern").item
    # a reviewer is asked to accept the proposed ADR
    svc.comment(adr.id, ["@reviewer please accept this ADR"], as_slug="manager")
    # the mention is visible while the ADR is still Proposed
    ids_before = {it.id for it, _ in svc.inbox("reviewer")}
    assert adr.id in ids_before

    # accept the decision
    svc.set_status(adr.id, Status.ACCEPTED)
    ids_after = {it.id for it, _ in svc.inbox("reviewer")}
    assert adr.id not in ids_after


def test_inbox_excludes_mention_on_published_guide(svc):
    """Symmetric regression for guides: a mention in a Draft guide must NOT appear in
    inbox once the guide is Published."""
    guide = svc.create(ItemType.GUIDE, "Onboarding guide").item
    svc.comment(guide.id, ["@qa please review this draft"], as_slug="manager")
    ids_before = {it.id for it, _ in svc.inbox("qa")}
    assert guide.id in ids_before

    svc.set_status(guide.id, Status.PUBLISHED)
    ids_after = {it.id for it, _ in svc.inbox("qa")}
    assert guide.id not in ids_after


# --------------------------------------------------------------------------- outgoing transitions


def test_accepted_can_transition_to_superseded():
    """ACCEPTED → SUPERSEDED is a valid exit even though ACCEPTED is terminal."""
    assert workflow.can_transition(ItemType.DECISION, Status.ACCEPTED, Status.SUPERSEDED)


def test_accepted_can_transition_to_deprecated():
    assert workflow.can_transition(ItemType.DECISION, Status.ACCEPTED, Status.DEPRECATED)


def test_published_can_transition_to_draft():
    """PUBLISHED → DRAFT is a valid exit (guide revision cycle)."""
    assert workflow.can_transition(ItemType.GUIDE, Status.PUBLISHED, Status.DRAFT)


def test_published_can_transition_to_deprecated():
    assert workflow.can_transition(ItemType.GUIDE, Status.PUBLISHED, Status.DEPRECATED)


def test_guide_full_cycle_published_draft_published(svc):
    """A guide can go Draft→Published→Draft→Published: terminal does not block re-opening."""
    guide = svc.create(ItemType.GUIDE, "Cycle guide").item
    svc.set_status(guide.id, Status.PUBLISHED)
    assert svc.get(guide.id).status is Status.PUBLISHED
    svc.set_status(guide.id, Status.DRAFT)
    assert svc.get(guide.id).status is Status.DRAFT
    svc.set_status(guide.id, Status.PUBLISHED)
    assert svc.get(guide.id).status is Status.PUBLISHED


def test_decision_accepted_to_superseded(svc):
    """Accepted decision can be superseded (new ADR takes over)."""
    old_adr = svc.create(ItemType.DECISION, "Old pattern").item
    svc.set_status(old_adr.id, Status.ACCEPTED)
    svc.set_status(old_adr.id, Status.SUPERSEDED)
    assert svc.get(old_adr.id).status is Status.SUPERSEDED


# --------------------------------------------------------------------------- blocked semantics


def test_accepted_decision_unblocks_dependent(svc):
    """A task that depends-on a Proposed ADR is blocked; accepting the ADR unblocks it.
    ACCEPTED is now terminal, so is_open(ACCEPTED) is False — the blocker is gone."""
    adr = svc.create(ItemType.DECISION, "API contract").item
    task = svc.create(ItemType.TASK, "Implement API").item
    # task cannot proceed until ADR is settled
    svc.add_ref(task.id, adr.id, kind="depends-on")

    pairs = svc.blocked()
    blocked_ids = {it.id for it, _ in pairs}
    assert task.id in blocked_ids  # ADR is still Proposed (open) → task is blocked

    svc.set_status(adr.id, Status.ACCEPTED)  # ADR accepted → now terminal → unblocks
    assert svc.blocked() == []


def test_published_guide_unblocks_dependent(svc):
    """Symmetric: a task depending on a Draft guide is unblocked once it's Published."""
    guide = svc.create(ItemType.GUIDE, "Deployment guide").item
    task = svc.create(ItemType.TASK, "Deploy service").item
    svc.add_ref(task.id, guide.id, kind="depends-on")

    pairs = svc.blocked()
    blocked_ids = {it.id for it, _ in pairs}
    assert task.id in blocked_ids  # guide is Draft (open)

    svc.set_status(guide.id, Status.PUBLISHED)
    assert svc.blocked() == []


# --------------------------------------------------------------------------- list and search


def test_accepted_decision_hidden_in_default_list_visible_with_all(svc):
    """An Accepted decision must not appear in the open-only view (terminal) but must be
    visible in the full view and still found by search.

    The service list_items() returns all items; the CLI applies an is_open filter for the
    default view. We replicate that here using is_open directly.
    """
    adr = svc.create(ItemType.DECISION, "ADR: Use PostgreSQL").item
    svc.set_status(adr.id, Status.ACCEPTED)

    all_items = svc.list_items()
    assert adr.id in [i.id for i in all_items]  # list_items() returns everything

    open_items = [i for i in all_items if workflow.is_open(i.status)]
    assert adr.id not in [i.id for i in open_items]  # Accepted is terminal → filtered out

    search_hits = [i.id for i, _ in svc.search("PostgreSQL")]
    assert adr.id in search_hits  # search always looks at all items


def test_published_guide_hidden_in_default_list_visible_with_all(svc):
    """A Published guide is not open (terminal) so it is absent from the is_open-filtered
    view but present in the full list and in search results."""
    guide = svc.create(ItemType.GUIDE, "Squads overview guide").item
    svc.set_status(guide.id, Status.PUBLISHED)

    all_items = svc.list_items()
    assert guide.id in [i.id for i in all_items]

    open_items = [i for i in all_items if workflow.is_open(i.status)]
    assert guide.id not in [i.id for i in open_items]

    search_hits = [i.id for i, _ in svc.search("overview")]
    assert guide.id in search_hits


# --------------------------------------------------------------------------- CLI smoke


def test_cli_accepted_decision_hidden_then_visible(project, runner):
    """sq list hides Accepted decisions by default; --all shows them; sq search finds them."""
    runner.invoke(app, ["create", "decision", "Use Redis", "--author", "manager"])
    runner.invoke(app, ["decision", "2", "status", "Accepted"])

    default = runner.invoke(app, ["list", "--type", "decision"])
    assert "ADR-000002" not in default.output

    with_all = runner.invoke(app, ["list", "--type", "decision", "--all"])
    assert "ADR-000002" in with_all.output

    found = runner.invoke(app, ["search", "Redis"])
    assert "ADR-000002" in found.output


def test_cli_published_guide_hidden_then_visible(project, runner):
    """sq list hides Published guides by default; --all shows them; sq search finds them."""
    runner.invoke(app, ["create", "guide", "Ops runbook", "--author", "manager"])
    runner.invoke(app, ["guide", "2", "status", "Published"])

    default = runner.invoke(app, ["list", "--type", "guide"])
    assert "GUIDE-000002" not in default.output

    with_all = runner.invoke(app, ["list", "--type", "guide", "--all"])
    assert "GUIDE-000002" in with_all.output

    found = runner.invoke(app, ["search", "runbook"])
    assert "GUIDE-000002" in found.output


def test_cli_accepted_adr_unblocks_task(project, runner):
    """sq blocked shows a depends-on task as blocked until the ADR is Accepted."""
    runner.invoke(app, ["create", "decision", "API contract", "--author", "manager"])
    runner.invoke(app, ["create", "task", "Implement API", "--author", "manager"])
    runner.invoke(app, ["task", "3", "ref", "add", "ADR-000002", "--kind", "depends-on"])

    blocked_before = runner.invoke(app, ["blocked"])
    assert "TASK-000003" in blocked_before.output

    runner.invoke(app, ["decision", "2", "status", "Accepted"])

    blocked_after = runner.invoke(app, ["blocked"])
    assert "TASK-000003" not in blocked_after.output


@pytest.mark.parametrize("status_arg", ["Accepted", "Superseded"])
def test_cli_decision_by_status_filter(project, runner, status_arg):
    """sq list --status <S> always returns matching items regardless of is_open."""
    runner.invoke(app, ["create", "decision", "My ADR", "--author", "manager"])
    runner.invoke(app, ["decision", "2", "status", "Accepted"])
    if status_arg == "Superseded":
        runner.invoke(app, ["decision", "2", "status", "Superseded"])
    result = runner.invoke(app, ["list", "--status", status_arg])
    assert result.exit_code == 0
    assert "ADR-000002" in result.output
