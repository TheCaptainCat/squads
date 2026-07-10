"""The lifecycle auto-linearization helper: turns a transition graph into one human-readable
spine string, side states parenthesized.

Algorithm under test: greedy spine (follow the first unvisited transition from initial) + BFS
side states (remaining reachable states in BFS discovery order).
"""

import pytest

from squads._workflow._models import Lifecycle, linearize_lifecycle


def _m(initial: str, transitions: dict[str, list[str]]) -> Lifecycle:
    return Lifecycle(initial=initial, transitions=transitions)


# ---------------------------------------------------------------------------
# Linear machines — no branching, no side states
# ---------------------------------------------------------------------------


def test_single_state_no_transitions() -> None:
    m = _m("Draft", {})
    assert linearize_lifecycle(m) == "Draft"


def test_two_state_linear() -> None:
    m = _m("A", {"A": ["B"]})
    assert linearize_lifecycle(m) == "A → B"


def test_three_state_linear_with_a_back_edge() -> None:
    """Draft -> Published -> Deprecated, with Deprecated -> Published a back-edge."""
    m = _m(
        "Draft",
        {
            "Draft": ["Published"],
            "Published": ["Deprecated", "Draft"],
            "Deprecated": ["Published"],
        },
    )
    assert linearize_lifecycle(m) == "Draft → Published → Deprecated"


def test_agent_lifecycle() -> None:
    m = _m("Draft", {"Draft": ["Active"], "Active": ["Archived"], "Archived": ["Active"]})
    assert linearize_lifecycle(m) == "Draft → Active → Archived"


# ---------------------------------------------------------------------------
# Machines with side states
# ---------------------------------------------------------------------------


def test_adr_lifecycle_has_two_side_states() -> None:
    m = _m(
        "Proposed",
        {
            "Proposed": ["Accepted", "Rejected"],
            "Accepted": ["Superseded", "Deprecated"],
            "Rejected": ["Proposed"],
            "Superseded": [],
            "Deprecated": [],
        },
    )
    assert linearize_lifecycle(m) == "Proposed → Accepted → Superseded (+ Rejected, Deprecated)"


def test_work_lifecycle_orders_side_states_by_priority_not_discovery() -> None:
    m = _m(
        "Draft",
        {
            "Draft": ["Ready", "InProgress", "Cancelled"],
            "Ready": ["InProgress", "Blocked", "Cancelled"],
            "InProgress": ["InReview", "Blocked", "Done", "Cancelled"],
            "InReview": ["InProgress", "Done", "Blocked", "Cancelled"],
            "Blocked": ["Ready", "InProgress", "Cancelled"],
            "Done": ["InProgress"],
            "Cancelled": ["Draft"],
        },
    )
    assert (
        linearize_lifecycle(m)
        == "Draft → Ready → InProgress → InReview → Done (+ Blocked, Cancelled)"
    )


def test_bug_lifecycle_orders_side_states_by_priority() -> None:
    m = _m(
        "Open",
        {
            "Open": ["InProgress", "WontFix", "Cancelled"],
            "InProgress": ["Fixed", "Blocked", "WontFix", "Cancelled"],
            "Fixed": ["Verified", "InProgress"],
            "Verified": ["InProgress"],
            "Blocked": ["InProgress", "WontFix", "Cancelled"],
            "WontFix": ["Open"],
            "Cancelled": ["Open"],
        },
    )
    assert (
        linearize_lifecycle(m)
        == "Open → InProgress → Fixed → Verified (+ WontFix, Blocked, Cancelled)"
    )


def test_review_lifecycle_spine_picks_approved_over_a_revisit() -> None:
    m = _m(
        "Requested",
        {
            "Requested": ["InReview", "Rejected"],
            "InReview": ["ChangesRequested", "Approved", "Rejected"],
            "ChangesRequested": ["InReview", "Approved", "Rejected"],
            "Approved": [],
            "Rejected": [],
        },
    )
    assert (
        linearize_lifecycle(m) == "Requested → InReview → ChangesRequested → Approved (+ Rejected)"
    )


# ---------------------------------------------------------------------------
# Synthetic edge cases
# ---------------------------------------------------------------------------


def test_a_branching_machine_puts_the_second_branch_in_side_states() -> None:
    m = _m("Start", {"Start": ["PathA", "PathB"], "PathA": ["End"], "PathB": ["End"], "End": []})
    assert linearize_lifecycle(m) == "Start → PathA → End (+ PathB)"


def test_a_diamond_fork_join_machine_puts_the_other_fork_in_side_states() -> None:
    m = _m("A", {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []})
    assert linearize_lifecycle(m) == "A → B → D (+ C)"


def test_a_terminal_state_off_the_spine_still_appears_as_a_side_state() -> None:
    m = _m(
        "Open",
        {"Open": ["InProgress", "Cancelled"], "InProgress": ["Done"], "Done": [], "Cancelled": []},
    )
    assert linearize_lifecycle(m) == "Open → InProgress → Done (+ Cancelled)"


def test_output_is_deterministic_across_repeated_calls() -> None:
    m = _m(
        "Draft",
        {
            "Draft": ["Ready", "Cancelled"],
            "Ready": ["InProgress"],
            "InProgress": ["Done"],
            "Done": [],
            "Cancelled": [],
        },
    )
    assert linearize_lifecycle(m) == linearize_lifecycle(m)


def test_no_parenthesized_suffix_when_every_reachable_state_is_on_the_spine() -> None:
    m = _m("A", {"A": ["B"], "B": ["C"], "C": []})
    result = linearize_lifecycle(m)
    assert "+" not in result
    assert result == "A → B → C"


@pytest.mark.parametrize(
    "lifecycle_name", ["work", "adr", "review", "bug", "guide", "agent", "subentity", "finding"]
)
def test_every_bundled_lifecycle_linearizes_to_a_non_empty_string(lifecycle_name: str) -> None:
    from squads._workflow import load_workflow_spec

    spec = load_workflow_spec()
    assert lifecycle_name in spec.lifecycles
    result = linearize_lifecycle(spec.lifecycles[lifecycle_name])
    assert result
    assert "→" in result or result.count(" ") == 0  # has an arrow, or is a single bare state
