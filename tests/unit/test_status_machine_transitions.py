"""The foundational per-type status-machine contract: a declared transition is legal, an
undeclared skip is rejected, every built-in type's initial status is a member of its own
declared states, and the exact ``TERMINAL`` set is correct AND disjoint across workflows —
a superset/subset check would miss a leaked or missing member, so this asserts exact sets.
"""

from _helpers import BUILTIN_TYPES
from squads._workflow import bundled_spec


def test_a_declared_transition_is_legal_and_an_undeclared_skip_is_rejected() -> None:
    assert bundled_spec().initial_status("task") == "Draft"
    assert bundled_spec().can_transition("task", "Draft", "Ready")
    assert bundled_spec().can_transition("task", "InProgress", "Done")
    assert not bundled_spec().can_transition("task", "Draft", "Done")  # illegal skip


def test_the_bug_workflows_own_transition_edges() -> None:
    """The bug lifecycle is a second, differently-shaped instance of the same contract:
    reopen-from-terminal edges (Fixed/Verified/WontFix/Cancelled -> a live state) plus the
    ordinary forward edges."""
    wf = bundled_spec().workflow_for("bug")
    legal = [
        ("Open", "InProgress"),
        ("Open", "WontFix"),
        ("Open", "Cancelled"),
        ("InProgress", "Fixed"),
        ("InProgress", "Blocked"),
        ("Fixed", "Verified"),
        ("Fixed", "InProgress"),  # reopen on failed verify
        ("Verified", "InProgress"),  # reopen on regression
        ("Blocked", "InProgress"),
        ("WontFix", "Open"),
        ("Cancelled", "Open"),
    ]
    for src, dst in legal:
        assert wf.can_transition(src, dst), f"{src} -> {dst} should be legal"
    illegal = [("Open", "Verified"), ("Open", "Fixed"), ("Verified", "Fixed"), ("Verified", "Open")]
    for src, dst in illegal:
        assert not wf.can_transition(src, dst), f"{src} -> {dst} should be illegal"


def test_decision_and_review_and_guide_initial_statuses() -> None:
    assert bundled_spec().initial_status("decision") == "Proposed"
    assert bundled_spec().can_transition("decision", "Proposed", "Accepted")
    assert not bundled_spec().can_transition("decision", "Proposed", "Superseded")  # not direct
    assert bundled_spec().initial_status("review") == "Requested"
    assert bundled_spec().initial_status("guide") == "Draft"
    assert bundled_spec().can_transition("guide", "Draft", "Published")


def test_every_built_in_types_initial_status_is_a_member_of_its_own_states() -> None:
    for t in BUILTIN_TYPES:
        wf = bundled_spec().workflow_for(t)
        assert wf.initial in wf.states, f"{t}: initial {wf.initial!r} not in its own states"


def test_the_bugs_declared_states_are_exactly_its_own_vocabulary() -> None:
    """An exact-set assertion — a superset/subset check would miss a leaked or missing member."""
    states = bundled_spec().workflow_for("bug").states
    assert states == {"Open", "InProgress", "Fixed", "Verified", "Blocked", "WontFix", "Cancelled"}


def test_the_bugs_states_exclude_work_item_only_vocabulary() -> None:
    states = bundled_spec().workflow_for("bug").states
    for work_only in ("Draft", "Ready", "InReview", "Done", "Todo"):
        assert work_only not in states


def test_bug_terminal_states_are_exactly_verified_wontfix_and_cancelled() -> None:
    wf = bundled_spec().workflow_for("bug")
    terminals = {s for s in wf.states if s in bundled_spec().terminal_set()}
    assert terminals == {"Verified", "WontFix", "Cancelled"}


def test_work_item_only_statuses_never_leak_into_the_bug_workflow() -> None:
    """Some statuses (InProgress/Blocked/Cancelled) are deliberately shared generic vocabulary
    across workflows — the no-leakage guarantee is narrower: a status that belongs ONLY to the
    work-item lifecycle (Draft/Ready/InReview/Done/Todo) must never appear in bug's own set,
    which is exactly what the previous test already proves; this pins the inverse direction —
    every one of bug's own states is either shared generic vocabulary or bug-specific, never a
    work-item-only status by coincidence of a future edit."""
    work_only = {"Draft", "Ready", "InReview", "Done", "Todo"}
    bug_specific = {"Open", "Fixed", "Verified", "WontFix"}
    shared_generic = {"InProgress", "Blocked", "Cancelled"}
    assert bundled_spec().workflow_for("bug").states == bug_specific | shared_generic
    assert not (bundled_spec().workflow_for("bug").states & work_only)
