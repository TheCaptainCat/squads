"""`sq check` reports more than one **live** `role` item carrying the `is_default`
designation — a gap the `set-default` verb's own design already identifies (the
projection resolves the designation by first roster match, and nothing validates a single
holder at item level) but that, before this, nothing reported.

Report-only, deliberately: this predicate is never folded into
`_config_integrity.check_all`, so the retirement gate (`_services/_retirement.py::enforce`)
never evaluates it — see `_services/_validators.py::_default_designation_duplicated` for why a
gate clause here would reopen the exact lock-out the withdrawn `no_default_role` clause was
withdrawn for.

Companion to `tests/service/test_default_role_designation_move.py` (`set_default_role`'s own
convergence behaviour, unchanged here) and
`tests/service/test_retirement_refuses_a_config_breaking_transition.py` (the retirement gate).
"""

import pytest

from squads._services._results import CheckIssue

pytestmark = pytest.mark.anyio


def _messages(issues: list[CheckIssue], needle: str) -> list[CheckIssue]:
    return [i for i in issues if needle in i.message]


async def test_check_flags_two_live_roles_carrying_the_default_designation(svc):
    qa = await svc.activate_role("qa")
    manager = await svc.roster_item("role", "manager")
    await svc.update(qa.id, set_extra={"is_default": "true"})  # manager still carries it too

    issues = await svc.check()

    hits = _messages(issues, "default-role designation")
    assert len(hits) == 1
    hit = hits[0]
    assert hit.level == "error"
    assert manager.id in hit.message
    assert qa.id in hit.message
    assert "set-default" in hit.message


async def test_check_stays_silent_with_exactly_one_default_holder(svc):
    issues = await svc.check()
    assert _messages(issues, "default-role designation") == []


async def test_check_stays_silent_when_the_second_holder_is_not_live(svc):
    """Only LIVE holders count: a non-live role also carrying the key is not an active
    ambiguity in the generated config (only live roster entries are ever projected), and this
    is exactly the state a reactivation must be free to leave without the report firing
    mid-transition (see the two tests below)."""
    qa = await svc.activate_role("qa")
    await svc.set_roster_status(qa.id, "Archived")
    await svc.update(qa.id, set_extra={"is_default": "true"})

    issues = await svc.check()

    assert _messages(issues, "default-role designation") == []


# ------------------------------------------------------- report-only: never a gate clause


async def test_retiring_a_role_is_not_refused_by_a_two_holder_default_designation(svc):
    qa = await svc.activate_role("qa")
    await svc.update(qa.id, set_extra={"is_default": "true"})

    outcome = await svc.set_roster_status(qa.id, "Archived")

    assert outcome.item.status == "Archived"


async def test_reactivating_a_role_is_not_refused_by_a_two_holder_default_designation(svc):
    """The lock-out this must never become: reactivating a non-live role that still carries
    `is_default` while a live role also carries it is exactly the transition delta scoping
    would refuse if this were a gate clause — introducing a "two live holders" condition that
    did not exist before this transition — and there is no remedy in that direction:
    `set_default_role` refuses a non-live target, and no interactive command clears the key
    off a non-live role. Proves the retirement/reactivation path did not inherit the
    predicate."""
    qa = await svc.activate_role("qa")
    await svc.set_roster_status(qa.id, "Archived")
    await svc.update(qa.id, set_extra={"is_default": "true"})  # non-live holder, manager live

    outcome = await svc.set_roster_status(qa.id, "Active")

    assert outcome.item.status == "Active"
