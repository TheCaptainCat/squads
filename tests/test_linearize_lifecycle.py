"""Unit tests for the lifecycle auto-linearization helper (TASK-000262).

Tests cover: linear graphs, branching graphs, graphs with side states, cyclic
machines (forward cycles), and the bundled built-in lifecycles.

Algorithm: greedy spine (follow first unvisited transition from initial) + BFS
side states (remaining reachable states in BFS discovery order).
"""

import pytest

from squads._workflow._models import Lifecycle, linearize_lifecycle

# ---------------------------------------------------------------------------
# Helper to build test machines concisely
# ---------------------------------------------------------------------------


def _m(initial: str, transitions: dict[str, list[str]]) -> Lifecycle:
    return Lifecycle(initial=initial, transitions=transitions)


# ---------------------------------------------------------------------------
# Linear machines — no branching, no side states
# ---------------------------------------------------------------------------


def test_single_state_no_transitions() -> None:
    """A machine with one state and no transitions produces just that state."""
    m = _m("Draft", {})
    assert linearize_lifecycle(m) == "Draft"


def test_two_state_linear() -> None:
    """Two-state linear chain: A → B."""
    m = _m("A", {"A": ["B"]})
    assert linearize_lifecycle(m) == "A → B"


def test_three_state_linear() -> None:
    """Three-state chain: guide lifecycle (Draft → Published → Deprecated)."""
    m = _m(
        "Draft",
        {
            "Draft": ["Published"],
            "Published": ["Deprecated", "Draft"],
            "Deprecated": ["Published"],
        },
    )
    # Spine: Draft → Published → Deprecated (Deprecated → Published is a back-edge;
    # Published is already in spine).
    # All states reachable (Draft←Deprecated←Published←Draft via cycle), all on spine.
    assert linearize_lifecycle(m) == "Draft → Published → Deprecated"


def test_agent_lifecycle() -> None:
    """Agent lifecycle: Draft → Active → Archived."""
    m = _m(
        "Draft",
        {
            "Draft": ["Active"],
            "Active": ["Archived"],
            "Archived": ["Active"],
        },
    )
    assert linearize_lifecycle(m) == "Draft → Active → Archived"


# ---------------------------------------------------------------------------
# Machines with side states
# ---------------------------------------------------------------------------


def test_adr_lifecycle() -> None:
    """ADR lifecycle: Proposed → Accepted → Superseded (+ Rejected, Deprecated)."""
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
    result = linearize_lifecycle(m)
    assert result == "Proposed → Accepted → Superseded (+ Rejected, Deprecated)"


def test_work_lifecycle() -> None:
    """Work lifecycle: Draft → Ready → InProgress → InReview → Done (+ Blocked, Cancelled)."""
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
    result = linearize_lifecycle(m)
    # Canonical ordering: Blocked before Cancelled (priority sort; see _SIDE_PRIORITY).
    assert result == "Draft → Ready → InProgress → InReview → Done (+ Blocked, Cancelled)"


def test_bug_lifecycle() -> None:
    """Bug lifecycle: Open → InProgress → Fixed → Verified (+ WontFix, Cancelled, Blocked)."""
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
    result = linearize_lifecycle(m)
    # Canonical ordering: WontFix(0) before Blocked(1) before Cancelled(2) (priority sort).
    assert result == "Open → InProgress → Fixed → Verified (+ WontFix, Blocked, Cancelled)"


def test_review_lifecycle() -> None:
    """Review lifecycle: spine picks Approved after ChangesRequested (TASK-261 re-baseline).

    TOML fix (option-b from carry-forward note):
    ChangesRequested now declares [InReview, Approved, Rejected].  InReview is already
    visited so the greedy spine picks Approved next, matching the hand-written PLAYBOOK
    string.  The previous machine had [InReview, Rejected]; adding Approved to
    ChangesRequested is semantically valid (reviewer approves after revision) and aligns
    linearize_lifecycle output with the stable lifecycle prose in playbook.toml and goldens.
    """
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
    result = linearize_lifecycle(m)
    # Spine: Requested → InReview → ChangesRequested → Approved (Approved is first unvisited
    # from ChangesRequested; InReview is already in spine).
    # Side: Rejected (reachable from multiple states but not on spine).
    assert result == "Requested → InReview → ChangesRequested → Approved (+ Rejected)"


# ---------------------------------------------------------------------------
# Custom / synthetic machines (for coverage of edge cases)
# ---------------------------------------------------------------------------


def test_simple_branching_machine() -> None:
    """A simple branching machine: spine follows first branch, others are side states."""
    m = _m(
        "Start",
        {
            "Start": ["PathA", "PathB"],
            "PathA": ["End"],
            "PathB": ["End"],
            "End": [],
        },
    )
    result = linearize_lifecycle(m)
    # Spine: Start → PathA → End (End is first unvisited from PathA)
    # Side: PathB (reachable from Start but not on spine)
    assert result == "Start → PathA → End (+ PathB)"


def test_diamond_machine() -> None:
    """Diamond (fork-join) machine: spine through one path, other fork in side states."""
    m = _m(
        "A",
        {
            "A": ["B", "C"],
            "B": ["D"],
            "C": ["D"],
            "D": [],
        },
    )
    result = linearize_lifecycle(m)
    # Spine: A → B → D (first transitions); C is side
    assert result == "A → B → D (+ C)"


def test_terminal_only_side_state() -> None:
    """Machine where some terminal states are reachable but not on the spine."""
    m = _m(
        "Open",
        {
            "Open": ["InProgress", "Cancelled"],
            "InProgress": ["Done"],
            "Done": [],
            "Cancelled": [],
        },
    )
    result = linearize_lifecycle(m)
    # Spine: Open → InProgress → Done; side: Cancelled
    assert result == "Open → InProgress → Done (+ Cancelled)"


def test_determinism_consistent_output() -> None:
    """Calling linearize_lifecycle twice on the same machine returns identical strings."""
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
    r1 = linearize_lifecycle(m)
    r2 = linearize_lifecycle(m)
    assert r1 == r2


def test_all_states_on_spine_no_side_states() -> None:
    """When all reachable states end up on the spine, no '(+ ...)' suffix is appended."""
    m = _m("A", {"A": ["B"], "B": ["C"], "C": []})
    result = linearize_lifecycle(m)
    assert "+" not in result
    assert result == "A → B → C"


# ---------------------------------------------------------------------------
# Bundled spec — smoke test that linearize_lifecycle returns non-empty strings
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "lifecycle_name",
    ["work", "adr", "review", "bug", "guide", "agent", "subtask", "story", "finding"],
)
def test_bundled_lifecycles_produce_non_empty_strings(lifecycle_name: str) -> None:
    """linearize_lifecycle produces a non-empty string for every bundled lifecycle."""
    from squads._workflow import load_workflow_spec

    spec = load_workflow_spec()
    assert lifecycle_name in spec.lifecycles, f"lifecycle {lifecycle_name!r} not in bundled spec"
    result = linearize_lifecycle(spec.lifecycles[lifecycle_name])
    assert result, f"empty string for lifecycle {lifecycle_name!r}"
    assert " → " in result or "→" in result  # has at least one arrow (or single state)
