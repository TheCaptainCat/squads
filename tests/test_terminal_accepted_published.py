"""Regression and coverage tests for ACCEPTED and PUBLISHED in the TERMINAL set.

BUG-000080: inbox surfaced stale mentions from Accepted decisions and Published guides
because those statuses were missing from TERMINAL.

TASK-000081: adds ACCEPTED and PUBLISHED to the TERMINAL frozenset; this file verifies
every consumer that cares about terminal status is now correct.
"""

import pytest

from squads import _workflow as workflow
from squads._models._enums import ItemType, Status

pytestmark = pytest.mark.anyio

# --------------------------------------------------------------------------- TERMINAL membership


def test_accepted_and_published_are_terminal():
    assert Status.ACCEPTED in workflow.TERMINAL
    assert Status.PUBLISHED in workflow.TERMINAL


def test_accepted_and_published_are_not_open():
    assert not workflow.is_open(Status.ACCEPTED)
    assert not workflow.is_open(Status.PUBLISHED)


# --------------------------------------------------------------------------- inbox


async def test_inbox_excludes_mention_on_accepted_decision(svc):
    """Regression: a mention written when an ADR was Proposed must NOT appear in inbox
    after the ADR transitions to Accepted."""
    adr = (await svc.create(ItemType.DECISION, "Use CQRS pattern")).item
    # a reviewer is asked to accept the proposed ADR
    await svc.comment(adr.id, ["@reviewer please accept this ADR"], as_slug="manager")
    # the mention is visible while the ADR is still Proposed
    ids_before = {it.id for it, _ in await svc.inbox("reviewer")}
    assert adr.id in ids_before

    # accept the decision
    await svc.set_status(adr.id, Status.ACCEPTED)
    ids_after = {it.id for it, _ in await svc.inbox("reviewer")}
    assert adr.id not in ids_after


async def test_inbox_excludes_mention_on_published_guide(svc):
    """Symmetric regression for guides: a mention in a Draft guide must NOT appear in
    inbox once the guide is Published."""
    guide = (await svc.create(ItemType.GUIDE, "Onboarding guide")).item
    await svc.comment(guide.id, ["@qa please review this draft"], as_slug="manager")
    ids_before = {it.id for it, _ in await svc.inbox("qa")}
    assert guide.id in ids_before

    await svc.set_status(guide.id, Status.PUBLISHED)
    ids_after = {it.id for it, _ in await svc.inbox("qa")}
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


async def test_guide_full_cycle_published_draft_published(svc):
    """A guide can go Draft→Published→Draft→Published: terminal does not block re-opening."""
    guide = (await svc.create(ItemType.GUIDE, "Cycle guide")).item
    await svc.set_status(guide.id, Status.PUBLISHED)
    assert (await svc.get(guide.id)).status == Status.PUBLISHED
    await svc.set_status(guide.id, Status.DRAFT)
    assert (await svc.get(guide.id)).status == Status.DRAFT
    await svc.set_status(guide.id, Status.PUBLISHED)
    assert (await svc.get(guide.id)).status == Status.PUBLISHED


async def test_decision_accepted_to_superseded(svc):
    """Accepted decision can be superseded (new ADR takes over)."""
    old_adr = (await svc.create(ItemType.DECISION, "Old pattern")).item
    await svc.set_status(old_adr.id, Status.ACCEPTED)
    await svc.set_status(old_adr.id, Status.SUPERSEDED)
    assert (await svc.get(old_adr.id)).status == Status.SUPERSEDED


# --------------------------------------------------------------------------- blocked semantics


async def test_accepted_decision_unblocks_dependent(svc):
    """A task that depends-on a Proposed ADR is blocked; accepting the ADR unblocks it.
    ACCEPTED is now terminal, so is_open(ACCEPTED) is False — the blocker is gone."""
    adr = (await svc.create(ItemType.DECISION, "API contract")).item
    task = (await svc.create(ItemType.TASK, "Implement API")).item
    # task cannot proceed until ADR is settled
    await svc.add_ref(task.id, adr.id, kind="depends-on")

    pairs = await svc.blocked()
    blocked_ids = {it.id for it, _ in pairs}
    assert task.id in blocked_ids  # ADR is still Proposed (open) → task is blocked

    await svc.set_status(adr.id, Status.ACCEPTED)  # ADR accepted → now terminal → unblocks
    assert await svc.blocked() == []


async def test_published_guide_unblocks_dependent(svc):
    """Symmetric: a task depending on a Draft guide is unblocked once it's Published."""
    guide = (await svc.create(ItemType.GUIDE, "Deployment guide")).item
    task = (await svc.create(ItemType.TASK, "Deploy service")).item
    await svc.add_ref(task.id, guide.id, kind="depends-on")

    pairs = await svc.blocked()
    blocked_ids = {it.id for it, _ in pairs}
    assert task.id in blocked_ids  # guide is Draft (open)

    await svc.set_status(guide.id, Status.PUBLISHED)
    assert await svc.blocked() == []


# --------------------------------------------------------------------------- list and search


async def test_accepted_decision_hidden_in_default_list_visible_with_all(svc):
    """An Accepted decision must not appear in the open-only view (terminal) but must be
    visible in the full view and still found by search.

    The service list_items() returns all items; the CLI applies an is_open filter for the
    default view. We replicate that here using is_open directly.
    """
    adr = (await svc.create(ItemType.DECISION, "ADR: Use PostgreSQL")).item
    await svc.set_status(adr.id, Status.ACCEPTED)

    all_items = await svc.list_items()
    assert adr.id in [i.id for i in all_items]  # list_items() returns everything

    open_items = [i for i in all_items if workflow.is_open(i.status)]
    assert adr.id not in [i.id for i in open_items]  # Accepted is terminal → filtered out

    search_hits = [i.id for i, _ in await svc.search("PostgreSQL")]
    assert adr.id in search_hits  # search always looks at all items


async def test_published_guide_hidden_in_default_list_visible_with_all(svc):
    """A Published guide is not open (terminal) so it is absent from the is_open-filtered
    view but present in the full list and in search results."""
    guide = (await svc.create(ItemType.GUIDE, "Squads overview guide")).item
    await svc.set_status(guide.id, Status.PUBLISHED)

    all_items = await svc.list_items()
    assert guide.id in [i.id for i in all_items]

    open_items = [i for i in all_items if workflow.is_open(i.status)]
    assert guide.id not in [i.id for i in open_items]

    search_hits = [i.id for i, _ in await svc.search("overview")]
    assert guide.id in search_hits


# --------------------------------------------------------------------------- CLI smoke


async def test_cli_accepted_decision_hidden_then_visible(project, invoke):
    """sq list hides Accepted decisions by default; --all shows them; sq search finds them."""
    await invoke(["create", "decision", "Use Redis", "--author", "manager"])
    await invoke(["decision", "2", "status", "Accepted"])

    default = await invoke(["list", "--type", "decision"])
    assert "ADR-2" not in default.output

    with_all = await invoke(["list", "--type", "decision", "--all"])
    assert "ADR-2" in with_all.output

    found = await invoke(["search", "Redis"])
    assert "ADR-2" in found.output


async def test_cli_published_guide_hidden_then_visible(project, invoke):
    """sq list hides Published guides by default; --all shows them; sq search finds them."""
    await invoke(["create", "guide", "Ops runbook", "--author", "manager"])
    await invoke(["guide", "2", "status", "Published"])

    default = await invoke(["list", "--type", "guide"])
    assert "GUIDE-2" not in default.output

    with_all = await invoke(["list", "--type", "guide", "--all"])
    assert "GUIDE-2" in with_all.output

    found = await invoke(["search", "runbook"])
    assert "GUIDE-2" in found.output


async def test_cli_accepted_adr_unblocks_task(project, invoke):
    """sq blocked shows a depends-on task as blocked until the ADR is Accepted."""
    await invoke(["create", "decision", "API contract", "--author", "manager"])
    await invoke(["create", "task", "Implement API", "--author", "manager"])
    await invoke(["task", "3", "ref", "add", "ADR-000002", "--kind", "depends-on"])

    blocked_before = await invoke(["blocked"])
    assert "TASK-3" in blocked_before.output

    await invoke(["decision", "2", "status", "Accepted"])

    blocked_after = await invoke(["blocked"])
    assert "TASK-3" not in blocked_after.output


@pytest.mark.parametrize("status_arg", ["Accepted", "Superseded"])
async def test_cli_decision_by_status_filter(project, invoke, status_arg):
    """sq list --status <S> always returns matching items regardless of is_open."""
    await invoke(["create", "decision", "My ADR", "--author", "manager"])
    await invoke(["decision", "2", "status", "Accepted"])
    if status_arg == "Superseded":
        await invoke(["decision", "2", "status", "Superseded"])
    result = await invoke(["list", "--status", status_arg])
    assert result.exit_code == 0
    assert "ADR-2" in result.output
