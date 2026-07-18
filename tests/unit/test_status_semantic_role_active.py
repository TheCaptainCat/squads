"""``default_workflow.toml`` declares ``role = "active"`` on the two working states —
``InProgress`` (work-item lifecycle) and ``Active`` (roster/agent lifecycle) — orthogonal to
``terminal`` (mirrors ``Superseded``, which already carries both a role and terminal=true).
Purely additive: no other status gains or loses a role.
"""

from squads._workflow import bundled_spec


def test_in_progress_carries_the_active_role_and_stays_non_terminal() -> None:
    spec = bundled_spec()
    st = spec.statuses["InProgress"]
    assert st.role == "active"
    assert st.terminal is False


def test_roster_active_carries_the_active_role_and_stays_non_terminal() -> None:
    spec = bundled_spec()
    st = spec.statuses["Active"]
    assert st.role == "active"
    assert st.terminal is False


def test_superseded_role_is_unaffected_by_the_active_role_addition() -> None:
    spec = bundled_spec()
    st = spec.statuses["Superseded"]
    assert st.role == "superseded"
    assert st.terminal is True


def test_status_role_accessor_resolves_the_new_active_role() -> None:
    spec = bundled_spec()
    assert spec.status_role("InProgress") == "active"
    assert spec.status_role("Active") == "active"


def test_no_other_status_gained_a_role_beyond_the_two_declared_here_and_superseded() -> None:
    spec = bundled_spec()
    roled = {name for name, st in spec.statuses.items() if st.role is not None}
    assert roled == {"InProgress", "Active", "Superseded"}
